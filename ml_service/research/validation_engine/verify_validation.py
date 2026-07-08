"""Verification script for validation engine."""

from datetime import datetime, timedelta
from typing import List

from .types import SplitMetrics
from .service import ValidationEngine
from .splitter import create_time_series_split
from .walk_forward import create_walk_forward_windows
from .overfit import calculate_overfit_score
from .stability import calculate_stability_from_metrics


def generate_test_timestamps(days: int = 365) -> List[str]:
    """Generate test timestamps."""
    start = datetime(2024, 1, 1)
    timestamps = []
    for i in range(days):
        ts = start + timedelta(days=i)
        timestamps.append(ts.isoformat())
    return timestamps


def mock_evaluate_fn(start: str, end: str) -> SplitMetrics:
    """Mock evaluation function for testing."""
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    days = (end_dt - start_dt).days

    return SplitMetrics(
        sharpe_ratio=1.5,
        total_return=0.15,
        win_rate=0.55,
        max_drawdown=-0.08,
        trade_count=days * 2,
        sortino_ratio=1.8,
        profit_factor=1.6
    )


def mock_evaluate_fn_overfit(start: str, end: str) -> SplitMetrics:
    """Mock evaluation with overfitting pattern."""
    if 'train' in start or start < '2024-07-01':
        return SplitMetrics(
            sharpe_ratio=2.5,
            total_return=0.35,
            win_rate=0.75,
            max_drawdown=-0.05,
            trade_count=100,
            sortino_ratio=3.0,
            profit_factor=2.5
        )
    else:
        return SplitMetrics(
            sharpe_ratio=0.8,
            total_return=0.05,
            win_rate=0.48,
            max_drawdown=-0.15,
            trade_count=50,
            sortino_ratio=0.9,
            profit_factor=1.1
        )


def verify_time_series_split():
    """Verify time series split."""
    print("\n=== Verifying Time Series Split ===")

    timestamps = generate_test_timestamps(365)
    split = create_time_series_split(timestamps, 0.6, 0.2, 0.2)

    print(f"Train: {split.train_start} to {split.train_end}")
    print(f"Validation: {split.validation_start} to {split.validation_end}")
    print(f"Test: {split.test_start} to {split.test_end}")

    assert split.train_start < split.train_end
    assert split.train_end < split.validation_start
    assert split.validation_end < split.test_start
    print("✓ Chronological ordering preserved")


def verify_walk_forward():
    """Verify walk forward windows."""
    print("\n=== Verifying Walk Forward ===")

    timestamps = generate_test_timestamps(365)
    windows = create_walk_forward_windows(timestamps, 90, 30, 30)

    print(f"Generated {len(windows)} windows")
    for i, window in enumerate(windows[:3]):
        print(f"Window {i}: train {window.train_start[:10]} to {window.train_end[:10]}, "
              f"test {window.test_start[:10]} to {window.test_end[:10]}")

    assert len(windows) > 0
    print("✓ Walk forward windows created")


def verify_overfit_detection():
    """Verify overfitting detection."""
    print("\n=== Verifying Overfitting Detection ===")

    train_metrics = SplitMetrics(
        sharpe_ratio=2.5,
        total_return=0.35,
        win_rate=0.75,
        max_drawdown=-0.05,
        trade_count=100,
        sortino_ratio=3.0,
        profit_factor=2.5
    )

    validation_metrics = SplitMetrics(
        sharpe_ratio=0.8,
        total_return=0.05,
        win_rate=0.48,
        max_drawdown=-0.15,
        trade_count=50,
        sortino_ratio=0.9,
        profit_factor=1.1
    )

    result = calculate_overfit_score(train_metrics, validation_metrics, 0.3)

    print(f"Train sharpe: {result.train_sharpe:.2f}")
    print(f"Validation sharpe: {result.validation_sharpe:.2f}")
    print(f"Sharpe decay: {result.sharpe_decay:.3f}")
    print(f"Overfit score: {result.overfit_score:.3f}")
    print(f"Is overfit: {result.is_overfit}")

    assert result.overfit_score > 0.3
    assert result.is_overfit
    print("✓ Overfitting detected correctly")


def verify_stability_analysis():
    """Verify stability analysis."""
    print("\n=== Verifying Stability Analysis ===")

    metrics_list = [
        SplitMetrics(1.5, 0.15, 0.55, -0.08, 50, 1.8, 1.6),
        SplitMetrics(1.6, 0.16, 0.56, -0.07, 52, 1.9, 1.7),
        SplitMetrics(1.4, 0.14, 0.54, -0.09, 48, 1.7, 1.5),
        SplitMetrics(1.5, 0.15, 0.55, -0.08, 51, 1.8, 1.6),
    ]

    result = calculate_stability_from_metrics(metrics_list, 0.5)

    print(f"Sharpe std: {result.sharpe_std:.3f}")
    print(f"Consistency ratio: {result.consistency_ratio:.3f}")
    print(f"Stability score: {result.stability_score:.3f}")
    print(f"Is stable: {result.is_stable}")

    assert result.stability_score > 0.5
    assert result.is_stable
    print("✓ Stability analysis computed correctly")


def verify_validation_engine():
    """Verify complete validation engine."""
    print("\n=== Verifying Validation Engine ===")

    engine = ValidationEngine(overfit_threshold=0.3, stability_threshold=0.5)
    timestamps = generate_test_timestamps(365)

    print("\nTest 1: No overfitting case")
    report = engine.validate_experiment(
        experiment_id="test_exp_1",
        timestamps=timestamps,
        evaluate_fn=mock_evaluate_fn
    )

    print(f"Train sharpe: {report.train_metrics.sharpe_ratio:.2f}")
    print(f"Validation sharpe: {report.validation_metrics.sharpe_ratio:.2f}")
    print(f"Overfit score: {report.overfit_score:.3f}")
    print(f"Verdict: {report.final_verdict}")
    assert report.final_verdict.startswith("PASS")
    print("✓ No overfitting case passed")

    print("\nTest 2: Overfitting case")
    timestamps_overfit = generate_test_timestamps(365)
    for i, ts in enumerate(timestamps_overfit):
        dt = datetime.fromisoformat(ts)
        if i < 219:
            timestamps_overfit[i] = dt.isoformat().replace('2024', '2024-train')

    report2 = engine.validate_experiment(
        experiment_id="test_exp_2",
        timestamps=timestamps,
        evaluate_fn=mock_evaluate_fn_overfit
    )

    print(f"Train sharpe: {report2.train_metrics.sharpe_ratio:.2f}")
    print(f"Validation sharpe: {report2.validation_metrics.sharpe_ratio:.2f}")
    print(f"Overfit score: {report2.overfit_score:.3f}")
    print(f"Verdict: {report2.final_verdict}")
    print(f"Warnings: {report2.warnings}")
    assert report2.final_verdict.startswith("FAIL") or report2.final_verdict.startswith("WARN")
    print("✓ Overfitting case detected")


def verify_walk_forward_validation():
    """Verify walk forward validation."""
    print("\n=== Verifying Walk Forward Validation ===")

    engine = ValidationEngine(overfit_threshold=0.3, stability_threshold=0.5)
    timestamps = generate_test_timestamps(365)

    report = engine.validate_with_walk_forward(
        experiment_id="test_exp_wf",
        timestamps=timestamps,
        evaluate_fn=mock_evaluate_fn,
        train_window_days=90,
        test_window_days=30,
        step_days=30
    )

    print(f"Walk forward windows: {len(report.walk_forward_windows) if report.walk_forward_windows else 0}")
    print(f"Stability score: {report.stability_score:.3f}")
    print(f"Overfit score: {report.overfit_score:.3f}")
    print(f"Verdict: {report.final_verdict}")

    assert report.walk_forward_windows is not None
    assert len(report.walk_forward_windows) > 0
    print("✓ Walk forward validation completed")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("RESEARCH VALIDATION ENGINE VERIFICATION")
    print("=" * 60)

    try:
        verify_time_series_split()
        verify_walk_forward()
        verify_overfit_detection()
        verify_stability_analysis()
        verify_validation_engine()
        verify_walk_forward_validation()

        print("\n" + "=" * 60)
        print("ALL VERIFICATION TESTS PASSED ✓")
        print("=" * 60)
        print("\nValidation Engine ready for use:")
        print("- Time series split with chronological ordering")
        print("- Walk-forward validation with rolling windows")
        print("- Overfitting detection via train/validation decay")
        print("- Stability analysis across periods")
        print("- Complete ValidationReport generation")

    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        raise


if __name__ == "__main__":
    main()
