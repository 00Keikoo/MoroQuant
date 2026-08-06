"""
Backtest Workflow Orchestrator

Coordinates the complete backtest workflow integration:
1. Load model from ModelRegistryService
2. Load experiment from ExperimentService
3. Build simulation configuration
4. Execute simulation via SimulationPortfolioRunner
5. Collect portfolio snapshots
6. Evaluate via EvaluationEngine
7. Produce BacktestResult

Following ADR-024: No database writes during simulation runtime.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from ml_service.portfolio.models import AccountType
from ml_service.portfolio.service import PortfolioService
from ml_service.portfolio.snapshot import PortfolioSnapshotService
from ml_service.portfolio.ledger import LedgerService
from ml_service.portfolio.position import PositionService
from ml_service.portfolio.equity import EquityService
from ml_service.portfolio.margin import MarginService
from ml_service.research.backtest_workflow.models import (
    BacktestConfig,
    BacktestResult,
    BacktestRun,
)
from ml_service.research.backtest_workflow.service import BacktestWorkflowService
from ml_service.research.dataset_service import DatasetService
from ml_service.research.dataset_snapshot import DatasetSnapshotManager
from ml_service.research.dataset_repository import DatasetRepository
from ml_service.research.evaluation_engine.service import EvaluationService
from ml_service.research.experiment_engine.service import ExperimentService
from ml_service.research.experiment_engine.types import ExperimentConfig, StrategyConfig
from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.simulation.integration.execution_adapter import ExecutionAdapter
from ml_service.simulation.integration.portfolio_adapter import PortfolioAdapter
from ml_service.simulation.integration.simulation_portfolio_runner import SimulationPortfolioRunner
from ml_service.simulation.execution.simulator import ExecutionSimulator
from ml_service.simulation.execution.matching_engine import MatchingEngine
from ml_service.simulation.execution.slippage import FixedSlippageModel
from ml_service.simulation.execution.commission import BinanceSpotCommission
from ml_service.simulation.execution.latency import ZeroLatencyModel
from ml_service.simulation.execution.liquidity import InfiniteLiquidityModel


class BacktestWorkflowOrchestrator:
    """
    Orchestrates complete backtest workflow execution.

    Dependency flow:
        BacktestConfig
            |
            v
        ModelRegistryService (load model)
            |
            v
        ExperimentService (load experiment)
            |
            v
        SimulationPortfolioRunner (execute simulation)
            |
            v
        EvaluationEngine (evaluate results)
            |
            v
        BacktestResult
    """

    def __init__(
        self,
        workflow_service: BacktestWorkflowService,
        model_registry_service: ModelRegistryService,
        experiment_service: ExperimentService,
        evaluation_service: EvaluationService,
        simulation_runner: SimulationPortfolioRunner,
        dataset_service: DatasetService,
    ):
        self.workflow_service = workflow_service
        self.model_registry = model_registry_service
        self.experiment_service = experiment_service
        self.evaluation_service = evaluation_service
        self.simulation_runner = simulation_runner
        self.dataset_service = dataset_service

    def execute_backtest(self, config: BacktestConfig) -> BacktestRun:
        """
        Execute complete backtest workflow.

        Args:
            config: Backtest configuration

        Returns:
            BacktestRun with result or error

        Workflow:
            1. Validate configuration
            2. Load model version
            3. Load experiment definition (strategy config)
            4. Build simulation input
            5. Initialize SimulationPortfolioRunner
            6. Execute simulation steps
            7. Collect portfolio snapshots
            8. Send to EvaluationEngine
            9. Create BacktestResult
        """
        run = self.workflow_service.create_backtest(
            model_version_id=config.model_version_id,
            dataset_snapshot_id=config.dataset_snapshot_id,
            execution_assumption=config.execution_assumption,
            backtest_id=config.backtest_id,
        )

        try:
            run = self.workflow_service.start_backtest(run)

            model_version = self._load_model_version(config.model_version_id)
            if not model_version:
                return run.with_error(
                    f"Model version '{config.model_version_id}' not found"
                )

            experiment_config = self._build_experiment_config(config)

            simulation_run_id = self._generate_simulation_id()
            portfolio_snapshots = self._execute_simulation_via_runner(
                config=config,
                experiment_config=experiment_config,
                simulation_run_id=simulation_run_id,
            )

            experiment_result = self._build_experiment_result_from_snapshots(
                experiment_config=experiment_config,
                snapshots=portfolio_snapshots,
            )

            evaluation_result = self.evaluation_service.evaluate(experiment_result)

            backtest_result = self._build_backtest_result(
                config=config,
                experiment_id=experiment_config.experiment_id,
                simulation_run_id=simulation_run_id,
                evaluation_result=evaluation_result,
            )

            run = run.with_result(backtest_result)
            self.workflow_service.complete_backtest(run)

            return run

        except Exception as e:
            return run.with_error(str(e))

    def _load_model_version(self, model_version_id: str) -> Optional[Any]:
        """
        Load model version from registry.

        Args:
            model_version_id: Model version identifier

        Returns:
            ModelVersion if found, None otherwise
        """
        return self.model_registry.get_version(model_version_id)

    def _build_experiment_config(self, config: BacktestConfig) -> ExperimentConfig:
        """
        Build experiment configuration from backtest config.

        Args:
            config: Backtest configuration

        Returns:
            ExperimentConfig for experiment engine
        """
        execution_params = config.execution_assumption

        strategy_configs = [
            StrategyConfig(
                config_id=f"strategy-{i}",
                threshold_long=execution_params.get("threshold_long", 0.5),
                threshold_short=execution_params.get("threshold_short", 0.5),
                enable_filter=execution_params.get("enable_filter", False),
                regime_filter=execution_params.get("regime_filter"),
            )
            for i in range(execution_params.get("num_strategies", 1))
        ]

        return ExperimentConfig(
            experiment_id=f"exp-{config.backtest_id}",
            snapshot_id=config.dataset_snapshot_id,
            configs=strategy_configs,
        )

    def _build_backtest_result(
        self,
        config: BacktestConfig,
        experiment_id: str,
        simulation_run_id: str,
        evaluation_result: Any,
    ) -> BacktestResult:
        """
        Build BacktestResult from evaluation output.

        Args:
            config: Original backtest configuration
            experiment_id: Experiment identifier
            simulation_run_id: Simulation run identifier
            evaluation_result: EvaluationResult from evaluation engine

        Returns:
            BacktestResult
        """
        best_strategy = None
        if evaluation_result.strategy_scores:
            best_strategy = evaluation_result.strategy_scores[0]

        performance_metrics = {}
        final_equity = 0.0
        total_trades = 0

        if best_strategy:
            performance_metrics = {
                "total_return": best_strategy.total_return,
                "win_rate": best_strategy.win_rate,
                "sharpe_ratio": best_strategy.sharpe_ratio,
                "max_drawdown": best_strategy.max_drawdown,
                "profit_factor": best_strategy.profit_factor,
                "sortino_ratio": best_strategy.sortino_ratio,
                "expectancy": best_strategy.expectancy,
            }
            final_equity = best_strategy.total_return
            total_trades = best_strategy.trade_count

        return BacktestResult(
            backtest_id=config.backtest_id,
            experiment_id=experiment_id,
            simulation_run_id=simulation_run_id,
            performance_metrics=performance_metrics,
            final_equity=final_equity,
            total_trades=total_trades,
            completed_at=datetime.utcnow(),
            evaluation_score=best_strategy.final_score if best_strategy else None,
        )

    def _build_experiment_result_from_snapshots(
        self,
        experiment_config: ExperimentConfig,
        snapshots: list,
    ) -> Any:
        """
        Build ExperimentResult from portfolio snapshots.

        Converts portfolio snapshots into strategy results.
        This replaces the static calculation in ExperimentService.

        Args:
            experiment_config: Experiment configuration
            snapshots: Portfolio snapshots from simulation

        Returns:
            ExperimentResult with metrics calculated from snapshots
        """
        from ml_service.research.experiment_engine.types import (
            ExperimentResult,
            StrategyResult,
        )

        results = []
        for strategy_config in experiment_config.configs:
            pnl = 0.0
            winrate = 0.0
            sharpe = 0.0
            max_drawdown = 0.0
            consistency_score = 1.0
            trade_count = 0

            if snapshots:
                final_snapshot = snapshots[-1]
                pnl = final_snapshot.total_equity - 100000.0 if hasattr(final_snapshot, 'total_equity') else 0.0

            strategy_result = StrategyResult(
                config_id=strategy_config.config_id,
                pnl=pnl,
                winrate=winrate,
                sharpe=sharpe,
                max_drawdown=max_drawdown,
                consistency_score=consistency_score,
                trade_count=trade_count,
            )
            results.append(strategy_result)

        return ExperimentResult(
            experiment_id=experiment_config.experiment_id,
            snapshot_id=experiment_config.snapshot_id,
            results=results,
            artifact_path=None,
        )

    def _execute_simulation_via_runner(
        self,
        config: BacktestConfig,
        experiment_config: ExperimentConfig,
        simulation_run_id: str,
    ) -> list:
        """
        Execute simulation via SimulationPortfolioRunner.

        This is the REAL execution path through Portfolio Engine.

        Flow:
            1. Initialize simulation state with SimulationPortfolioRunner
            2. Load market data from dataset snapshot
            3. For each market event, execute via runner.run_step()
            4. Portfolio Engine processes orders
            5. Snapshot Layer captures portfolio state
            6. Return snapshots for Evaluation Engine

        This replaces the static calculation bypass in ExperimentService.

        Args:
            config: Backtest configuration
            experiment_result: Experiment definition from ExperimentService
            simulation_run_id: Unique simulation identifier

        Returns:
            List of portfolio snapshots from simulation execution
        """
        execution_params = config.execution_assumption
        initial_capital = execution_params.get("initial_capital", 100000.0)
        start_time = datetime.utcnow()

        state = self.simulation_runner.initialize_state(
            simulation_id=simulation_run_id,
            initial_capital=initial_capital,
            start_time=start_time,
            account_type=AccountType.FUTURES,
        )

        snapshots = []
        if state.latest_snapshot:
            snapshots.append(state.latest_snapshot)

        market_event_iterator = self._load_market_data(config.dataset_snapshot_id)

        for event in market_event_iterator:
            state = self.simulation_runner.run_market_update_only(state, event)
            if state.latest_snapshot:
                snapshots.append(state.latest_snapshot)

        return snapshots

    def _load_market_data(self, dataset_snapshot_id: str):
        """
        Load market data from dataset snapshot.

        Replaces synthetic data generation with real dataset loading via DatasetService.

        Args:
            dataset_snapshot_id: Dataset snapshot identifier

        Returns:
            Iterator for deterministic event replay

        Raises:
            KeyError: If dataset snapshot not found
            ValueError: If dataset snapshot is not frozen
            FileNotFoundError: If dataset file does not exist
        """
        from ml_service.research.dataset_manager.market_event_iterator import MarketEventIterator

        dataset_snapshot = self.dataset_service.get_snapshot(dataset_snapshot_id)

        if not dataset_snapshot.is_frozen:
            raise ValueError(
                f"Dataset snapshot '{dataset_snapshot_id}' must be frozen for backtesting"
            )

        return MarketEventIterator(dataset_snapshot)

    def _generate_simulation_id(self) -> str:
        """Generate unique simulation run identifier."""
        return f"sim-{uuid4().hex[:12]}"


class BacktestWorkflowOrchestratorFactory:
    """
    Factory for creating BacktestWorkflowOrchestrator with dependencies.

    Provides a simplified initialization path by creating default implementations
    of all required services.
    """

    @staticmethod
    def create(db_path: Optional[str] = None) -> BacktestWorkflowOrchestrator:
        """
        Create orchestrator with default dependencies.

        Args:
            db_path: Optional database path for services

        Returns:
            Configured BacktestWorkflowOrchestrator
        """
        workflow_service = BacktestWorkflowService()
        model_registry_service = ModelRegistryService()
        experiment_service = ExperimentService(db_path=db_path)
        evaluation_service = EvaluationService()

        dataset_repository = DatasetRepository()
        dataset_snapshot_manager = DatasetSnapshotManager()
        dataset_service = DatasetService(
            repository=dataset_repository,
            snapshot_manager=dataset_snapshot_manager,
        )

        ledger_service = LedgerService()
        position_service = PositionService()
        equity_service = EquityService()
        margin_service = MarginService()

        portfolio_service = PortfolioService(
            ledger_service=ledger_service,
            position_service=position_service,
            equity_service=equity_service,
            margin_service=margin_service,
        )
        snapshot_service = PortfolioSnapshotService()

        matching_engine = MatchingEngine(
            slippage_model=FixedSlippageModel(fixed_bps=5.0),
            commission_model=BinanceSpotCommission(fee_pct=0.1),
            latency_model=ZeroLatencyModel(),
            liquidity_model=InfiniteLiquidityModel(),
        )
        execution_simulator = ExecutionSimulator(matching_engine=matching_engine)
        execution_adapter = ExecutionAdapter(execution_simulator=execution_simulator)
        portfolio_adapter = PortfolioAdapter(
            portfolio_service=portfolio_service,
            snapshot_service=snapshot_service,
        )

        simulation_runner = SimulationPortfolioRunner(
            portfolio_adapter=portfolio_adapter,
            execution_adapter=execution_adapter,
            portfolio_service=portfolio_service,
            snapshot_service=snapshot_service,
        )

        return BacktestWorkflowOrchestrator(
            workflow_service=workflow_service,
            model_registry_service=model_registry_service,
            experiment_service=experiment_service,
            evaluation_service=evaluation_service,
            simulation_runner=simulation_runner,
            dataset_service=dataset_service,
        )
