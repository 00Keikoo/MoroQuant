"""Verification script for statistical comparison engine."""

import numpy as np
from ml_service.research.comparison_engine.service import ComparisonEngine
from ml_service.research.comparison_engine.comparison import calculate_confidence_interval


def verify_comparison_engine():
    """Verify statistical comparison engine functionality."""

    print("=" * 60)
    print("Statistical Comparison Engine Verification")
    print("=" * 60)

    np.random.seed(42)

    returns_a = [0.02, 0.03, -0.01, 0.04, 0.01, 0.02, -0.005, 0.03]
    returns_b = [0.015, 0.02, -0.015, 0.03, 0.008, 0.015, -0.01, 0.025]

    sharpe_a = 1.5
    sharpe_b = 1.3
    max_dd_a = -0.08
    max_dd_b = -0.10
    win_rate_a = 0.75
    win_rate_b = 0.70

    print("\n1. Testing Metrics Comparison")
    print("-" * 60)
    print(f"Experiment A: Total Return={sum(returns_a):.4f}, Sharpe={sharpe_a:.2f}")
    print(f"Experiment B: Total Return={sum(returns_b):.4f}, Sharpe={sharpe_b:.2f}")

    engine = ComparisonEngine()

    report = engine.compare_experiments(
        experiment_a_id="exp_a",
        experiment_b_id="exp_b",
        returns_a=returns_a,
        returns_b=returns_b,
        sharpe_a=sharpe_a,
        sharpe_b=sharpe_b,
        max_dd_a=max_dd_a,
        max_dd_b=max_dd_b,
        win_rate_a=win_rate_a,
        win_rate_b=win_rate_b,
        alpha=0.05,
        bootstrap_iterations=10000,
        random_seed=42
    )

    print(f"\nReturn Difference: {report.metrics_difference.return_diff:.4f}")
    print(f"Sharpe Difference: {report.metrics_difference.sharpe_diff:.2f}")
    print(f"Drawdown Difference: {report.metrics_difference.drawdown_diff:.2f}")
    print(f"Win Rate Difference: {report.metrics_difference.win_rate_diff:.2f}")

    print("\n2. Testing Hypothesis Tests")
    print("-" * 60)
    print(f"T-test p-value: {report.hypothesis_test.t_test_pvalue:.4f}")
    print(f"T-test significant: {report.hypothesis_test.t_test_significant}")
    print(f"Mann-Whitney p-value: {report.hypothesis_test.mann_whitney_pvalue:.4f}")
    print(f"Mann-Whitney significant: {report.hypothesis_test.mann_whitney_significant}")

    print("\n3. Testing Bootstrap Analysis")
    print("-" * 60)
    print(f"Confidence Interval: [{report.bootstrap_result.confidence_interval_lower:.4f}, {report.bootstrap_result.confidence_interval_upper:.4f}]")
    print(f"Probability A beats B: {report.bootstrap_result.probability_a_beats_b:.4f}")
    print(f"Bootstrap iterations: {report.bootstrap_result.n_iterations}")

    print("\n4. Testing Confidence Interval (separate function)")
    print("-" * 60)
    ci_lower, ci_upper = calculate_confidence_interval(returns_a, confidence_level=0.95)
    print(f"95% CI for Experiment A: [{ci_lower:.4f}, {ci_upper:.4f}]")

    print("\n5. Final Verdict")
    print("-" * 60)
    print(f"Verdict: {report.verdict}")

    print("\n6. Testing Determinism")
    print("-" * 60)
    report2 = engine.compare_experiments(
        experiment_a_id="exp_a",
        experiment_b_id="exp_b",
        returns_a=returns_a,
        returns_b=returns_b,
        sharpe_a=sharpe_a,
        sharpe_b=sharpe_b,
        max_dd_a=max_dd_a,
        max_dd_b=max_dd_b,
        win_rate_a=win_rate_a,
        win_rate_b=win_rate_b,
        random_seed=42
    )

    deterministic = (
        report.bootstrap_result.probability_a_beats_b == report2.bootstrap_result.probability_a_beats_b
        and report.bootstrap_result.confidence_interval_lower == report2.bootstrap_result.confidence_interval_lower
    )
    print(f"Deterministic with same seed: {deterministic}")

    print("\n7. Testing Clear Winner Scenario")
    print("-" * 60)
    returns_winner = [0.05, 0.06, 0.04, 0.07, 0.05, 0.06, 0.04, 0.08]
    returns_loser = [0.01, 0.005, -0.02, 0.015, -0.01, 0.008, -0.015, 0.012]

    report_clear = engine.compare_experiments(
        experiment_a_id="exp_winner",
        experiment_b_id="exp_loser",
        returns_a=returns_winner,
        returns_b=returns_loser,
        sharpe_a=2.5,
        sharpe_b=0.8,
        max_dd_a=-0.03,
        max_dd_b=-0.15,
        win_rate_a=0.90,
        win_rate_b=0.50,
        random_seed=42
    )

    print(f"Probability A beats B: {report_clear.bootstrap_result.probability_a_beats_b:.4f}")
    print(f"T-test significant: {report_clear.hypothesis_test.t_test_significant}")
    print(f"Verdict: {report_clear.verdict}")

    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)

    all_checks = [
        report.metrics_difference.return_diff > 0,
        report.bootstrap_result.n_iterations == 10000,
        deterministic,
        report_clear.bootstrap_result.probability_a_beats_b > 0.95,
        report_clear.hypothesis_test.t_test_significant
    ]

    if all(all_checks):
        print("✓ All verification checks passed")
        return True
    else:
        print("✗ Some verification checks failed")
        return False


if __name__ == "__main__":
    verify_comparison_engine()
