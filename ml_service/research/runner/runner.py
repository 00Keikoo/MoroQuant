from abc import ABC, abstractmethod
from typing import Dict, Any
from ml_service.research.models import DatasetSnapshot
from ml_service.research.runner.models import ResearchRunResult

class Runner(ABC):
    """
    Interface for the quantitative research runner.
    Enforces ADR-024 principles: immutable, deterministic, isolated, no database writes.
    """
    @abstractmethod
    def run(self, dataset_snapshot: DatasetSnapshot, config: Dict[str, Any]) -> ResearchRunResult:
        """
        Execute end-to-end research orchestration pipeline.
        """
        pass


class ResearchRunner(Runner):
    """
    Orchestrates the quantitative research execution pipeline:
    DatasetSnapshot -> Replay -> FeatureContext -> FeatureSnapshot -> Inference -> SignalGeneration -> Evaluation -> ExperimentTracking
    """
    def __init__(
        self,
        feature_service,
        inference_adapter,
        signal_generator,
        tracker,
    ) -> None:
        self.feature_service = feature_service
        self.inference_adapter = inference_adapter
        self.signal_generator = signal_generator
        self.tracker = tracker

    def run(self, dataset_snapshot: DatasetSnapshot, config: Dict[str, Any]) -> ResearchRunResult:
        # Validate input DatasetSnapshot
        if not dataset_snapshot.is_frozen:
            raise ValueError("DatasetSnapshot must be frozen to execute pipeline")

        run_id = config.get("run_id", "run-default")
        experiment_id = config.get("experiment_id", "exp-default")
        model_version_id = config.get("model_version_id", "model-default")
        strategy_id = config.get("strategy_id", "strategy-default")
        threshold_long = config.get("threshold_long", 0.5)
        threshold_short = config.get("threshold_short", 0.5)

        # 1. Replay
        snapshot = config.get("snapshot")
        if not snapshot:
            raise ValueError("Config must provide a 'snapshot' object for Replay step")

        from ml_service.research.replay_engine.replay import run_replay
        replay_result = run_replay(snapshot, threshold_long=threshold_long, threshold_short=threshold_short)

        # 2. FeatureContext & 3. FeatureSnapshot
        from datetime import datetime
        from ml_service.simulation.models import MarketSnapshot

        symbol = snapshot.signals[0].get("symbol", "BTCUSDT") if snapshot.signals else "BTCUSDT"
        dt = datetime.fromisoformat(snapshot.timestamp.replace("Z", "+00:00"))

        market_snapshot = MarketSnapshot(
            timestamp=dt,
            symbol=symbol,
            mid_price=config.get("mid_price", 100.0),
        )

        self.feature_service.initialize_context(symbol)
        self.feature_service.update_context(symbol, market_snapshot)
        feature_snapshot = self.feature_service.build_snapshot(symbol)

        # 4. Inference
        inference_result = self.inference_adapter.predict(model_version_id, feature_snapshot)

        # 5. SignalGeneration
        from ml_service.research.strategy.models import StrategyState
        state = StrategyState(strategy_id=strategy_id, timestamp=snapshot.timestamp)
        signal = self.signal_generator.generate(inference_result.prediction, feature_snapshot, state)
        signals = (signal,) if signal else ()

        # 6. Evaluation
        from ml_service.research.experiment_engine.types import StrategyResult as ExpStrategyResult, ExperimentResult as ExpExperimentResult
        from ml_service.research.evaluation_engine.engine import evaluate_experiment

        pnl = sum(d.get("position_size", 0.0) * d.get("prob_long", 0.0) for d in replay_result.decisions)
        winrate = replay_result.signal_reproduction_rate
        trade_count = len([d for d in replay_result.decisions if d.get("executed")])

        strat_result = ExpStrategyResult(
            config_id=strategy_id,
            pnl=pnl,
            winrate=winrate,
            sharpe=winrate * 3.0,
            max_drawdown=-0.05,
            consistency_score=replay_result.consistency_score,
            trade_count=trade_count,
        )
        exp_result = ExpExperimentResult(
            experiment_id=experiment_id,
            snapshot_id=snapshot.snapshot_id,
            results=[strat_result],
        )
        evaluation_result = evaluate_experiment(exp_result)

        # 7. ExperimentTracking
        eval_summary = (
            ("best_strategy_id", evaluation_result.best_strategy_id),
            ("overall_risk_score", evaluation_result.overall_risk_score),
            ("signal_reproduction_rate", replay_result.signal_reproduction_rate),
        )

        from ml_service.research.experiment.models import ExperimentRun
        experiment_run = ExperimentRun(
            experiment_id=experiment_id,
            model_version_id=model_version_id,
            dataset_snapshot_id=dataset_snapshot.dataset_version_id,
            strategy_id=strategy_id,
            feature_schema_version=feature_snapshot.schema_version,
            evaluation_summary=eval_summary,
        )
        self.tracker.log_run(experiment_run)

        return ResearchRunResult(
            run_id=run_id,
            dataset_snapshot_id=dataset_snapshot.dataset_version_id,
            replay_result=replay_result,
            feature_snapshot=feature_snapshot,
            inference_result=inference_result,
            signals=signals,
            evaluation_result=evaluation_result,
            experiment_run=experiment_run,
        )
