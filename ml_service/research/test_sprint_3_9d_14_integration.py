"""End-to-end integration test for Sprint 3.9D-14.

Validates the complete research pipeline:
Dataset/Snapshot → Replay → Experiment → Evaluation → ResearchReport → Benchmark → Promotion → RegistryProposal

Verifies:
- trade.id != trade.signal_id (Phase 1 fix)
- Actual metric calculations from real trade data (Phase 2 fix)
- Production Evaluation→ResearchReport adapter is used
- Production DefaultResearchBenchmark is used
- Production Benchmark→Promotion adapter is used
- PromotionEngine is exercised
- Canonical RegistryProposal is produced
- Normal experiment path uses actual profit factor, not heuristic
"""

import sys
import os

# Add parent directory to path for direct imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.experiment_engine.engine import apply_strategy_config
from ml_service.research.experiment_engine.types import StrategyConfig, ExperimentResult, StrategyResult
from ml_service.research.evaluation_engine.engine import evaluate_experiment, compute_strategy_score
from ml_service.research.evaluation_engine.types import EvaluationResult

# Import production adapters and classes
from ml_service.research.reporting.adapter import evaluation_to_report
from ml_service.research.benchmark.benchmark import DefaultResearchBenchmark
from ml_service.research.promotion_engine.benchmark_adapter import benchmark_to_audit_report
from ml_service.research.promotion_engine.engine import PromotionEngine
from ml_service.research.promotion_engine.models import RegistryProposal, PromotionStatus
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState


def test_end_to_end_pipeline_integration():
    """Test complete pipeline with realistic fixture using production classes."""

    # Fixture: Snapshot with trade.id != trade.signal_id
    snapshot = Snapshot(
        snapshot_id="integration-snapshot-1",
        timestamp="2024-08-13T12:00:00Z",
        trades=[
            # Deliberately different id vs signal_id (Phase 1 regression test)
            {"id": "trade-001", "signal_id": "signal-001", "symbol": "AAPL", "pnl": 250.0},
            {"id": "trade-002", "signal_id": "signal-002", "symbol": "GOOGL", "pnl": -100.0},
            {"id": "trade-003", "signal_id": "signal-003", "symbol": "MSFT", "pnl": 150.0},
            {"id": "trade-004", "signal_id": "signal-004", "symbol": "TSLA", "pnl": -75.0},
            {"id": "trade-005", "signal_id": "signal-005", "symbol": "AMZN", "pnl": 200.0},
        ],
        signals=[]
    )

    # Fixture: ReplayResult with decisions matching signal_ids
    replay_result = ReplayResult(
        snapshot_id="integration-snapshot-1",
        decisions=[
            {
                "signal_id": "signal-001",
                "symbol": "AAPL",
                "prob_long": 0.75,
                "prob_short": 0.1,
                "prob_neutral": 0.15,
                "executed": True
            },
            {
                "signal_id": "signal-002",
                "symbol": "GOOGL",
                "prob_long": 0.2,
                "prob_short": 0.7,
                "prob_neutral": 0.1,
                "executed": True
            },
            {
                "signal_id": "signal-003",
                "symbol": "MSFT",
                "prob_long": 0.8,
                "prob_short": 0.1,
                "prob_neutral": 0.1,
                "executed": True
            },
            {
                "signal_id": "signal-004",
                "symbol": "TSLA",
                "prob_long": 0.1,
                "prob_short": 0.75,
                "prob_neutral": 0.15,
                "executed": True
            },
            {
                "signal_id": "signal-005",
                "symbol": "AMZN",
                "prob_long": 0.85,
                "prob_short": 0.05,
                "prob_neutral": 0.1,
                "executed": True
            },
        ],
        signal_reproduction_rate=1.0,
        execution_alignment_rate=1.0,
        divergence_count=0,
        notes=[],
        consistency_score=0.95,
        divergence_score=0.05
    )

    # 1. Experiment: Apply strategy config
    config = StrategyConfig(
        config_id="integration-config-1",
        threshold_long=0.65,
        threshold_short=0.65,
        enable_filter=False
    )

    strategy_result = apply_strategy_config(replay_result, snapshot, config)

    # Verify Phase 1: Trade mapping works correctly (id != signal_id)
    assert strategy_result.pnl == 425.0, f"Expected total PnL=425.0, got {strategy_result.pnl}"
    assert strategy_result.trade_count == 5, f"Expected 5 trades, got {strategy_result.trade_count}"
    assert strategy_result.winrate == 0.6, f"Expected winrate=0.6 (3/5), got {strategy_result.winrate}"

    # Verify Phase 2: Metrics calculated from actual data
    assert strategy_result.sharpe != 0.0, "Sharpe should be calculated from actual returns"
    assert strategy_result.max_drawdown < 0.0, "Max drawdown should be negative with actual losses"
    assert strategy_result.profit_factor is not None, "Profit factor should be calculated"
    assert strategy_result.profit_factor > 1.0, "Profit factor should be > 1 with net positive PnL"

    # 2. Evaluation: Compute enriched metrics
    experiment_result = ExperimentResult(
        experiment_id="integration-exp-1",
        snapshot_id="integration-snapshot-1",
        results=[strategy_result]
    )

    evaluation = evaluate_experiment(experiment_result)

    assert evaluation.experiment_id == "integration-exp-1"
    assert len(evaluation.strategy_scores) == 1
    assert evaluation.best_strategy_id == "integration-config-1"

    best_score = evaluation.strategy_scores[0]
    assert best_score.total_return == 425.0
    assert best_score.win_rate == 0.6
    assert best_score.sharpe_ratio != 0.0
    assert best_score.profit_factor > 1.0
    assert best_score.expectancy == 85.0  # 425.0 / 5 trades

    # 3. Phase 3: Evaluation → ResearchReport adapter using production evaluation_to_report
    research_report = evaluation_to_report(evaluation)

    assert research_report.experiment_id == "integration-exp-1"
    assert research_report.total_signals == 5
    assert research_report.win_rate == 0.6
    assert research_report.total_return == 425.0
    assert research_report.average_return == 85.0
    assert research_report.sharpe_ratio != 0.0
    assert research_report.profit_factor > 1.0
    assert research_report.max_drawdown < 0.0

    # 4. Benchmark: Compare reports using production DefaultResearchBenchmark
    benchmark_runner = DefaultResearchBenchmark(benchmark_id="integration-benchmark-1")
    benchmark_result = benchmark_runner.compare([research_report])

    assert benchmark_result.benchmark_id == "integration-benchmark-1"
    assert benchmark_result.winner == "integration-exp-1"
    assert len(benchmark_result.ranking) == 1
    assert len(benchmark_result.scores) == 1

    # 5. Phase 4: Benchmark → Promotion integration using production benchmark_to_audit_report
    audit_report = benchmark_to_audit_report(benchmark_result)

    assert audit_report["benchmark_id"] == "integration-benchmark-1"
    assert audit_report["benchmark_winner"] == "integration-exp-1"
    assert audit_report["cohort_size"] == 1
    assert "benchmark_score" in audit_report
    assert "validation_score" in audit_report

    # 6. Promotion: Generate RegistryProposal using production models and PromotionEngine
    model_identity = ModelIdentity(
        artifact_path="integration-model-v1",
        symbol="AAPL",
        timeframe="1d",
        model_type="xgb",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="a" * 64,
        trained_at="2026-08-13T12:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="candidate"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path="integration-model-v1",
        symbol="AAPL",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Model validated",
        timestamp="2026-08-13T12:00:00Z"
    )

    promotion_engine = PromotionEngine()
    registry_proposal = promotion_engine.evaluate(
        model_identity=model_identity,
        lifecycle_record=lifecycle_record,
        audit_report=audit_report
    )

    # Verify Phase 4: RegistryProposal is canonical promotion_engine model
    assert registry_proposal.model_id == "integration-model-v1"
    assert registry_proposal.symbol == "AAPL"
    assert registry_proposal.asset_class == "CRYPTO"
    assert registry_proposal.current_state == "VALIDATED"
    assert registry_proposal.score is not None
    assert registry_proposal.status is not None


def test_evaluation_uses_actual_profit_factor_and_not_heuristic():
    """Verify that when actual profit_factor is present in StrategyResult, the evaluation path preserves it."""
    # Case A: Actual profit factor is provided
    result_with_pf = StrategyResult(
        config_id="config-pf",
        pnl=100.0,
        winrate=0.6,
        sharpe=1.5,
        max_drawdown=-10.0,
        consistency_score=0.9,
        trade_count=10,
        profit_factor=2.75
    )
    score_with_pf = compute_strategy_score(result_with_pf)
    assert score_with_pf.profit_factor == 2.75, f"Expected profit_factor=2.75, got {score_with_pf.profit_factor}"

    # Case B: Profit factor is None (fallback to heuristic estimation)
    result_without_pf = StrategyResult(
        config_id="config-no-pf",
        pnl=100.0,
        winrate=0.6,
        sharpe=1.5,
        max_drawdown=-10.0,
        consistency_score=0.9,
        trade_count=10,
        profit_factor=None
    )
    score_without_pf = compute_strategy_score(result_without_pf)
    assert score_without_pf.profit_factor != 2.75, "Should fall back to estimate when profit_factor is None"
    assert score_without_pf.profit_factor is not None


if __name__ == "__main__":
    test_end_to_end_pipeline_integration()
    test_evaluation_uses_actual_profit_factor_and_not_heuristic()
