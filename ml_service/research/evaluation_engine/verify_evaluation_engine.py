"""Verification script for Evaluation Engine."""

from ml_service.research.experiment_engine.types import StrategyResult, ExperimentResult
from ml_service.research.evaluation_engine import (
    compute_strategy_score,
    evaluate_experiment,
    EvaluationService,
)


def create_mock_experiment_result() -> ExperimentResult:
    """Create mock experiment result for testing."""
    strategies = [
        StrategyResult(
            config_id="strategy_conservative",
            pnl=1500.0,
            winrate=0.65,
            sharpe=1.8,
            max_drawdown=-200.0,
            consistency_score=0.85,
            trade_count=50
        ),
        StrategyResult(
            config_id="strategy_aggressive",
            pnl=3000.0,
            winrate=0.45,
            sharpe=1.2,
            max_drawdown=-800.0,
            consistency_score=0.60,
            trade_count=80
        ),
        StrategyResult(
            config_id="strategy_balanced",
            pnl=2200.0,
            winrate=0.58,
            sharpe=2.1,
            max_drawdown=-350.0,
            consistency_score=0.78,
            trade_count=65
        ),
        StrategyResult(
            config_id="strategy_poor",
            pnl=-500.0,
            winrate=0.35,
            sharpe=-0.5,
            max_drawdown=-1200.0,
            consistency_score=0.40,
            trade_count=40
        ),
    ]

    return ExperimentResult(
        experiment_id="exp_verification_001",
        snapshot_id="snap_001",
        results=strategies
    )


def verify_strategy_score():
    """Verify individual strategy scoring."""
    print("\n=== Verifying Strategy Score Computation ===")

    strategy = StrategyResult(
        config_id="test_strategy",
        pnl=2000.0,
        winrate=0.60,
        sharpe=1.5,
        max_drawdown=-300.0,
        consistency_score=0.75,
        trade_count=50
    )

    score = compute_strategy_score(strategy)

    print(f"Config ID: {score.config_id}")
    print(f"Total Return: {score.total_return:.2f}")
    print(f"Win Rate: {score.win_rate:.2%}")
    print(f"Sharpe Ratio: {score.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {score.max_drawdown:.2f}")
    print(f"Trade Count: {score.trade_count}")
    print(f"Profit Factor: {score.profit_factor:.2f}")
    print(f"Sortino Ratio: {score.sortino_ratio:.2f}")
    print(f"Expectancy: {score.expectancy:.2f}")
    print(f"Final Score: {score.final_score:.4f}")

    assert score.config_id == "test_strategy"
    assert score.total_return == 2000.0
    assert score.win_rate == 0.60
    assert score.trade_count == 50
    assert score.expectancy == 40.0
    assert score.profit_factor > 1.0
    assert score.sortino_ratio > 0

    print("✓ Strategy score computation verified")


def verify_experiment_evaluation():
    """Verify full experiment evaluation and ranking."""
    print("\n=== Verifying Experiment Evaluation ===")

    experiment = create_mock_experiment_result()
    evaluation = evaluate_experiment(experiment)

    print(f"Experiment ID: {evaluation.experiment_id}")
    print(f"Number of strategies evaluated: {len(evaluation.strategy_scores)}")
    print(f"\nRanking (best to worst):")
    for i, config_id in enumerate(evaluation.ranking, 1):
        score = next(s for s in evaluation.strategy_scores if s.config_id == config_id)
        print(f"  {i}. {config_id}: score={score.final_score:.4f}, "
              f"return={score.total_return:.2f}, sharpe={score.sharpe_ratio:.2f}")

    print(f"\nBest Strategy: {evaluation.best_strategy_id}")
    print(f"Worst Strategy: {evaluation.worst_strategy_id}")
    print(f"Overall Risk Score: {evaluation.overall_risk_score:.4f}")

    assert evaluation.experiment_id == "exp_verification_001"
    assert len(evaluation.strategy_scores) == 4
    assert len(evaluation.ranking) == 4
    assert evaluation.best_strategy_id == evaluation.ranking[0]
    assert evaluation.worst_strategy_id == evaluation.ranking[-1]
    assert evaluation.worst_strategy_id == "strategy_poor"
    assert 0.0 <= evaluation.overall_risk_score <= 1.0

    best_score = next(s for s in evaluation.strategy_scores
                     if s.config_id == evaluation.best_strategy_id)
    worst_score = next(s for s in evaluation.strategy_scores
                      if s.config_id == evaluation.worst_strategy_id)
    assert best_score.final_score > worst_score.final_score

    print("✓ Experiment evaluation verified")


def verify_service_layer():
    """Verify service layer functionality."""
    print("\n=== Verifying Service Layer ===")

    service = EvaluationService()
    experiment = create_mock_experiment_result()
    evaluation = service.evaluate(experiment)

    top_strategy = service.get_top_strategy(evaluation)
    print(f"Top strategy: {top_strategy}")

    for config_id in evaluation.ranking:
        score = service.get_strategy_score(evaluation, config_id)
        print(f"  {config_id}: {score:.4f}")

    assert top_strategy == evaluation.best_strategy_id
    assert service.get_strategy_score(evaluation, top_strategy) > 0
    assert service.get_strategy_score(evaluation, "nonexistent") == 0.0

    print("✓ Service layer verified")


def verify_edge_cases():
    """Verify edge cases and boundary conditions."""
    print("\n=== Verifying Edge Cases ===")

    empty_experiment = ExperimentResult(
        experiment_id="exp_empty",
        snapshot_id="snap_empty",
        results=[]
    )

    empty_eval = evaluate_experiment(empty_experiment)
    assert len(empty_eval.strategy_scores) == 0
    assert len(empty_eval.ranking) == 0
    assert empty_eval.best_strategy_id == ""
    assert empty_eval.worst_strategy_id == ""
    print("✓ Empty experiment handled correctly")

    zero_trades = StrategyResult(
        config_id="zero_trades",
        pnl=0.0,
        winrate=0.0,
        sharpe=0.0,
        max_drawdown=0.0,
        consistency_score=0.0,
        trade_count=0
    )
    score = compute_strategy_score(zero_trades)
    assert score.expectancy == 0.0
    assert score.profit_factor >= 0.1
    print("✓ Zero trades handled correctly")

    perfect_strategy = StrategyResult(
        config_id="perfect",
        pnl=10000.0,
        winrate=1.0,
        sharpe=3.0,
        max_drawdown=-10.0,
        consistency_score=1.0,
        trade_count=100
    )
    perfect_score = compute_strategy_score(perfect_strategy)
    assert perfect_score.win_rate == 1.0
    assert perfect_score.final_score > 0.5
    print("✓ Perfect strategy handled correctly")

    print("✓ Edge cases verified")


def verify_determinism():
    """Verify evaluation is deterministic."""
    print("\n=== Verifying Determinism ===")

    experiment = create_mock_experiment_result()

    eval1 = evaluate_experiment(experiment)
    eval2 = evaluate_experiment(experiment)

    assert eval1.ranking == eval2.ranking
    assert eval1.best_strategy_id == eval2.best_strategy_id
    assert eval1.overall_risk_score == eval2.overall_risk_score

    for s1, s2 in zip(eval1.strategy_scores, eval2.strategy_scores):
        assert s1.final_score == s2.final_score

    print("✓ Evaluation is deterministic")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("EVALUATION ENGINE VERIFICATION")
    print("=" * 60)

    try:
        verify_strategy_score()
        verify_experiment_evaluation()
        verify_service_layer()
        verify_edge_cases()
        verify_determinism()

        print("\n" + "=" * 60)
        print("✓ ALL VERIFICATION TESTS PASSED")
        print("=" * 60)
        print("\nEvaluation Engine is ready for production use.")

    except AssertionError as e:
        print(f"\n✗ VERIFICATION FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
