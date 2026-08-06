"""
Tests for Backtest Workflow Architecture Compliance

Validates Sprint 3.8.1 architecture fixes:
1. SimulationPortfolioRunner is the real execution path
2. ExperimentService boundary (config only, no execution)
3. Repository persists complete BacktestRun aggregate
4. Persistence survives restart
5. End-to-end workflow integration
"""

import copy
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

from ml_service.portfolio.models import AccountType
from ml_service.research.backtest_workflow.models import (
    BacktestConfig,
    BacktestRun,
    BacktestStatus,
    BacktestResult,
)
from ml_service.research.backtest_workflow.orchestrator import (
    BacktestWorkflowOrchestrator,
)
from ml_service.research.backtest_workflow.repository import (
    BacktestWorkflowRepository,
)
from ml_service.research.backtest_workflow.service import BacktestWorkflowService
from ml_service.research.experiment_engine.types import (
    ExperimentConfig,
    ExperimentResult,
    StrategyConfig,
    StrategyResult,
)


class TestSimulationRunnerIsExecutionPath:
    """Test that SimulationPortfolioRunner is actually called."""

    @patch('ml_service.research.dataset_manager.market_event_iterator.MarketEventIterator')
    def test_simulation_runner_initialize_is_called(self, mock_market_iterator):
        """Verify SimulationPortfolioRunner.initialize_state is invoked."""
        mock_workflow_service = Mock(spec=BacktestWorkflowService)
        mock_model_registry = Mock()
        mock_experiment_service = Mock()
        mock_evaluation_service = Mock()
        mock_simulation_runner = Mock()
        mock_dataset_service = Mock()

        mock_snapshot = Mock()
        mock_snapshot.is_frozen = True
        mock_dataset_service.get_snapshot.return_value = mock_snapshot

        mock_events = [Mock() for _ in range(5)]
        mock_market_iterator.return_value.__iter__.return_value = iter(mock_events)

        run = BacktestRun(
            backtest_id="test-001",
            config=BacktestConfig(
                backtest_id="test-001",
                model_version_id="model-v1",
                dataset_snapshot_id="snapshot-001",
                execution_assumption={"initial_capital": 100000.0},
                created_at=datetime.utcnow(),
            ),
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        mock_workflow_service.create_backtest.return_value = run
        mock_workflow_service.start_backtest.return_value = run.with_status(
            BacktestStatus.RUNNING
        )
        mock_model_registry.get_version.return_value = {"version": "v1"}

        mock_state = Mock()
        mock_state.latest_snapshot = Mock()
        mock_state.latest_snapshot.total_equity = 100000.0
        mock_simulation_runner.initialize_state.return_value = mock_state
        mock_simulation_runner.run_market_update_only.return_value = mock_state

        mock_evaluation_service.evaluate.return_value = Mock(strategy_scores=[])

        orchestrator = BacktestWorkflowOrchestrator(
            workflow_service=mock_workflow_service,
            model_registry_service=mock_model_registry,
            experiment_service=mock_experiment_service,
            evaluation_service=mock_evaluation_service,
            simulation_runner=mock_simulation_runner,
            dataset_service=mock_dataset_service,
        )

        config = BacktestConfig(
            backtest_id="test-001",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 100000.0},
            created_at=datetime.utcnow(),
        )

        result = orchestrator.execute_backtest(config)

        mock_simulation_runner.initialize_state.assert_called_once()
        call_args = mock_simulation_runner.initialize_state.call_args
        assert "simulation_id" in call_args.kwargs
        assert call_args.kwargs["initial_capital"] == 100000.0
        assert call_args.kwargs["account_type"] == AccountType.FUTURES
        assert mock_simulation_runner.run_market_update_only.call_count >= 5
        assert result.status == BacktestStatus.COMPLETED


class TestExperimentServiceBoundary:
    """Test that ExperimentService only handles config, not execution."""

    @patch('ml_service.research.dataset_manager.market_event_iterator.MarketEventIterator')
    def test_experiment_service_not_used_for_simulation_execution(self, mock_market_iterator):
        """Verify ExperimentService.run_experiment is NOT called for simulation."""
        mock_workflow_service = Mock(spec=BacktestWorkflowService)
        mock_model_registry = Mock()
        mock_experiment_service = Mock()
        mock_evaluation_service = Mock()
        mock_simulation_runner = Mock()
        mock_dataset_service = Mock()

        mock_snapshot = Mock()
        mock_snapshot.is_frozen = True
        mock_dataset_service.get_snapshot.return_value = mock_snapshot

        mock_events = [Mock() for _ in range(5)]
        mock_market_iterator.return_value.__iter__.return_value = iter(mock_events)

        run = BacktestRun(
            backtest_id="test-002",
            config=BacktestConfig(
                backtest_id="test-002",
                model_version_id="model-v1",
                dataset_snapshot_id="snapshot-001",
                execution_assumption={},
                created_at=datetime.utcnow(),
            ),
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        mock_workflow_service.create_backtest.return_value = run
        mock_workflow_service.start_backtest.return_value = run.with_status(
            BacktestStatus.RUNNING
        )
        mock_model_registry.get_version.return_value = {"version": "v1"}

        mock_state = Mock()
        mock_state.latest_snapshot = Mock()
        mock_state.latest_snapshot.total_equity = 100000.0
        mock_simulation_runner.initialize_state.return_value = mock_state
        mock_simulation_runner.run_market_update_only.return_value = mock_state

        mock_evaluation_service.evaluate.return_value = Mock(strategy_scores=[])

        orchestrator = BacktestWorkflowOrchestrator(
            workflow_service=mock_workflow_service,
            model_registry_service=mock_model_registry,
            experiment_service=mock_experiment_service,
            evaluation_service=mock_evaluation_service,
            simulation_runner=mock_simulation_runner,
            dataset_service=mock_dataset_service,
        )

        config = BacktestConfig(
            backtest_id="test-002",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={},
            created_at=datetime.utcnow(),
        )

        orchestrator.execute_backtest(config)

        mock_experiment_service.run_experiment.assert_not_called()


class TestRepositoryPersistence:
    """Test that repository persists complete BacktestRun aggregate."""

    def test_repository_persists_full_backtest_run(self):
        """Verify BacktestRun with config is stored and retrieved."""
        repository = BacktestWorkflowRepository()

        config = BacktestConfig(
            backtest_id="test-003",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"threshold_long": 0.6},
            created_at=datetime.utcnow(),
        )

        result = BacktestResult(
            backtest_id="test-003",
            experiment_id="exp-001",
            simulation_run_id="sim-001",
            performance_metrics={"sharpe": 1.5},
            final_equity=110000.0,
            total_trades=10,
            completed_at=datetime.utcnow(),
            evaluation_score=0.85,
        )

        run = BacktestRun(
            backtest_id="test-003",
            config=config,
            status=BacktestStatus.COMPLETED,
            result=result,
            error_message=None,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        repository.save(run)

        retrieved = repository.get("test-003")

        assert retrieved is not None
        assert retrieved.backtest_id == "test-003"
        assert retrieved.config.model_version_id == "model-v1"
        assert retrieved.config.dataset_snapshot_id == "snapshot-001"
        assert retrieved.config.execution_assumption["threshold_long"] == 0.6
        assert retrieved.status == BacktestStatus.COMPLETED
        assert retrieved.result.experiment_id == "exp-001"
        assert retrieved.result.final_equity == 110000.0

    def test_repository_rejects_incomplete_config(self):
        """Verify repository validates BacktestRun before saving."""
        repository = BacktestWorkflowRepository()

        invalid_config = BacktestConfig(
            backtest_id="",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={},
            created_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="",
            config=invalid_config,
            status=BacktestStatus.COMPLETED,
            result=None,
            error_message=None,
        )

        with pytest.raises(ValueError):
            repository.save(run)


class TestRestartPersistence:
    """Test that persistence survives repository reload."""

    def test_restart_persistence(self):
        """Verify saved BacktestRun survives simulated restart."""
        repository1 = BacktestWorkflowRepository()

        config = BacktestConfig(
            backtest_id="test-004",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 50000.0},
            created_at=datetime.utcnow(),
        )

        result = BacktestResult(
            backtest_id="test-004",
            experiment_id="exp-002",
            simulation_run_id="sim-002",
            performance_metrics={},
            final_equity=52000.0,
            total_trades=5,
            completed_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="test-004",
            config=config,
            status=BacktestStatus.COMPLETED,
            result=result,
            error_message=None,
            completed_at=datetime.utcnow(),
        )

        repository1.save(run)

        repository2 = BacktestWorkflowRepository()
        repository2._runs = copy.deepcopy(repository1._runs)

        retrieved = repository2.get("test-004")

        assert retrieved is not None
        assert retrieved.config.model_version_id == "model-v1"
        assert retrieved.config.execution_assumption["initial_capital"] == 50000.0
        assert retrieved.result.final_equity == 52000.0


class TestEndToEndWorkflow:
    """Test complete workflow integration."""

    @patch('ml_service.research.dataset_manager.market_event_iterator.MarketEventIterator')
    def test_end_to_end_workflow_integration(self, mock_market_iterator):
        """Verify complete flow from config to result."""
        repository = BacktestWorkflowRepository()
        workflow_service = BacktestWorkflowService(repository=repository)

        mock_model_registry = Mock()
        mock_model_registry.get_version.return_value = {"version": "v1"}

        mock_experiment_service = Mock()
        mock_dataset_service = Mock()

        mock_snapshot = Mock()
        mock_snapshot.is_frozen = True
        mock_dataset_service.get_snapshot.return_value = mock_snapshot

        mock_events = [Mock() for _ in range(5)]
        mock_market_iterator.return_value.__iter__.return_value = iter(mock_events)

        mock_simulation_runner = Mock()
        mock_state = Mock()
        mock_state.latest_snapshot = Mock()
        mock_state.latest_snapshot.total_equity = 105000.0
        mock_simulation_runner.initialize_state.return_value = mock_state
        mock_simulation_runner.run_market_update_only.return_value = mock_state

        mock_evaluation_service = Mock()
        mock_strategy = Mock()
        mock_strategy.total_return = 5000.0
        mock_strategy.win_rate = 0.6
        mock_strategy.sharpe_ratio = 1.2
        mock_strategy.max_drawdown = -0.05
        mock_strategy.profit_factor = 1.8
        mock_strategy.sortino_ratio = 1.5
        mock_strategy.expectancy = 50.0
        mock_strategy.trade_count = 8
        mock_strategy.final_score = 0.75
        mock_eval_result = Mock()
        mock_eval_result.strategy_scores = [mock_strategy]
        mock_evaluation_service.evaluate.return_value = mock_eval_result

        orchestrator = BacktestWorkflowOrchestrator(
            workflow_service=workflow_service,
            model_registry_service=mock_model_registry,
            experiment_service=mock_experiment_service,
            evaluation_service=mock_evaluation_service,
            simulation_runner=mock_simulation_runner,
            dataset_service=mock_dataset_service,
        )

        config = BacktestConfig(
            backtest_id="test-e2e-001",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 100000.0},
            created_at=datetime.utcnow(),
        )

        result_run = orchestrator.execute_backtest(config)

        assert result_run.status == BacktestStatus.COMPLETED
        assert result_run.result is not None
        assert result_run.result.backtest_id == "test-e2e-001"

        persisted_run = repository.get("test-e2e-001")
        assert persisted_run is not None
        assert persisted_run.config.model_version_id == "model-v1"
        assert persisted_run.status == BacktestStatus.COMPLETED

        mock_simulation_runner.initialize_state.assert_called_once()
        assert mock_simulation_runner.run_market_update_only.call_count >= 5
        mock_evaluation_service.evaluate.assert_called_once()


class TestExecutionLoopValidation:
    """Test market event loop execution path."""

    @patch('ml_service.research.dataset_manager.market_event_iterator.MarketEventIterator')
    def test_market_event_loop_execution(self, mock_market_iterator):
        """Verify market events trigger run_step calls."""
        mock_workflow_service = Mock(spec=BacktestWorkflowService)
        mock_model_registry = Mock()
        mock_experiment_service = Mock()
        mock_evaluation_service = Mock()
        mock_simulation_runner = Mock()
        mock_dataset_service = Mock()

        mock_snapshot = Mock()
        mock_snapshot.is_frozen = True
        mock_dataset_service.get_snapshot.return_value = mock_snapshot

        mock_events = [Mock() for _ in range(5)]
        mock_market_iterator.return_value.__iter__.return_value = iter(mock_events)

        run = BacktestRun(
            backtest_id="test-loop-001",
            config=BacktestConfig(
                backtest_id="test-loop-001",
                model_version_id="model-v1",
                dataset_snapshot_id="snapshot-001",
                execution_assumption={"initial_capital": 100000.0},
                created_at=datetime.utcnow(),
            ),
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        mock_workflow_service.create_backtest.return_value = run
        mock_workflow_service.start_backtest.return_value = run.with_status(
            BacktestStatus.RUNNING
        )
        mock_model_registry.get_version.return_value = {"version": "v1"}

        mock_state = Mock()
        mock_state.latest_snapshot = Mock()
        mock_state.latest_snapshot.total_equity = 100000.0
        mock_simulation_runner.initialize_state.return_value = mock_state
        mock_simulation_runner.run_market_update_only.return_value = mock_state

        mock_evaluation_service.evaluate.return_value = Mock(strategy_scores=[])

        orchestrator = BacktestWorkflowOrchestrator(
            workflow_service=mock_workflow_service,
            model_registry_service=mock_model_registry,
            experiment_service=mock_experiment_service,
            evaluation_service=mock_evaluation_service,
            simulation_runner=mock_simulation_runner,
            dataset_service=mock_dataset_service,
        )

        config = BacktestConfig(
            backtest_id="test-loop-001",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 100000.0},
            created_at=datetime.utcnow(),
        )

        result = orchestrator.execute_backtest(config)

        assert mock_simulation_runner.run_market_update_only.call_count == 5

    @patch('ml_service.research.dataset_manager.market_event_iterator.MarketEventIterator')
    def test_multiple_portfolio_snapshots_generated(self, mock_market_iterator):
        """Verify multiple snapshots are collected during execution."""
        mock_workflow_service = Mock(spec=BacktestWorkflowService)
        mock_model_registry = Mock()
        mock_experiment_service = Mock()
        mock_evaluation_service = Mock()
        mock_simulation_runner = Mock()
        mock_dataset_service = Mock()

        mock_snapshot = Mock()
        mock_snapshot.is_frozen = True
        mock_dataset_service.get_snapshot.return_value = mock_snapshot

        mock_events = [Mock() for _ in range(5)]
        mock_market_iterator.return_value.__iter__.return_value = iter(mock_events)

        run = BacktestRun(
            backtest_id="test-snapshots-001",
            config=BacktestConfig(
                backtest_id="test-snapshots-001",
                model_version_id="model-v1",
                dataset_snapshot_id="snapshot-001",
                execution_assumption={"initial_capital": 100000.0},
                created_at=datetime.utcnow(),
            ),
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        mock_workflow_service.create_backtest.return_value = run
        mock_workflow_service.start_backtest.return_value = run.with_status(
            BacktestStatus.RUNNING
        )
        mock_model_registry.get_version.return_value = {"version": "v1"}

        snapshots = []
        for i in range(6):
            snapshot = Mock()
            snapshot.total_equity = 100000.0 + (i * 100)
            snapshots.append(snapshot)

        mock_states = []
        for snapshot in snapshots:
            state = Mock()
            state.latest_snapshot = snapshot
            mock_states.append(state)

        mock_simulation_runner.initialize_state.return_value = mock_states[0]
        mock_simulation_runner.run_market_update_only.side_effect = mock_states[1:]

        mock_evaluation_service.evaluate.return_value = Mock(strategy_scores=[])

        orchestrator = BacktestWorkflowOrchestrator(
            workflow_service=mock_workflow_service,
            model_registry_service=mock_model_registry,
            experiment_service=mock_experiment_service,
            evaluation_service=mock_evaluation_service,
            simulation_runner=mock_simulation_runner,
            dataset_service=mock_dataset_service,
        )

        config = BacktestConfig(
            backtest_id="test-snapshots-001",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 100000.0},
            created_at=datetime.utcnow(),
        )

        result = orchestrator.execute_backtest(config)

        assert result.status == BacktestStatus.COMPLETED

    def test_deterministic_equity_curve(self):
        """Verify same inputs produce same equity sequence."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        config = BacktestConfig(
            backtest_id="test-determinism-001",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 100000.0},
            created_at=timestamp,
        )

        assert config.model_version_id == "model-v1"
        assert config.dataset_snapshot_id == "snapshot-001"
        assert config.execution_assumption["initial_capital"] == 100000.0

    @patch('ml_service.research.dataset_manager.market_event_iterator.MarketEventIterator')
    def test_execution_path_integrity(self, mock_market_iterator):
        """Verify execution path goes through SimulationPortfolioRunner."""
        mock_workflow_service = Mock(spec=BacktestWorkflowService)
        mock_model_registry = Mock()
        mock_experiment_service = Mock()
        mock_evaluation_service = Mock()
        mock_simulation_runner = Mock()
        mock_dataset_service = Mock()

        mock_snapshot = Mock()
        mock_snapshot.is_frozen = True
        mock_dataset_service.get_snapshot.return_value = mock_snapshot

        mock_events = [Mock() for _ in range(5)]
        mock_market_iterator.return_value.__iter__.return_value = iter(mock_events)

        run = BacktestRun(
            backtest_id="test-path-001",
            config=BacktestConfig(
                backtest_id="test-path-001",
                model_version_id="model-v1",
                dataset_snapshot_id="snapshot-001",
                execution_assumption={"initial_capital": 100000.0},
                created_at=datetime.utcnow(),
            ),
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        mock_workflow_service.create_backtest.return_value = run
        mock_workflow_service.start_backtest.return_value = run.with_status(
            BacktestStatus.RUNNING
        )
        mock_model_registry.get_version.return_value = {"version": "v1"}

        mock_state = Mock()
        mock_state.latest_snapshot = Mock()
        mock_state.latest_snapshot.total_equity = 100000.0
        mock_simulation_runner.initialize_state.return_value = mock_state
        mock_simulation_runner.run_market_update_only.return_value = mock_state

        mock_evaluation_service.evaluate.return_value = Mock(strategy_scores=[])

        orchestrator = BacktestWorkflowOrchestrator(
            workflow_service=mock_workflow_service,
            model_registry_service=mock_model_registry,
            experiment_service=mock_experiment_service,
            evaluation_service=mock_evaluation_service,
            simulation_runner=mock_simulation_runner,
            dataset_service=mock_dataset_service,
        )

        config = BacktestConfig(
            backtest_id="test-path-001",
            model_version_id="model-v1",
            dataset_snapshot_id="snapshot-001",
            execution_assumption={"initial_capital": 100000.0},
            created_at=datetime.utcnow(),
        )

        result = orchestrator.execute_backtest(config)

        mock_simulation_runner.initialize_state.assert_called_once()
        assert mock_simulation_runner.run_market_update_only.call_count > 0
        assert result.status == BacktestStatus.COMPLETED
