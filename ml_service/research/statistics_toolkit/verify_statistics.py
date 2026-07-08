"""Verification tests for statistical toolkit."""

import numpy as np
from ml_service.research.statistics_toolkit import StatisticsService


def verify_distribution_analysis():
    """Verify distribution statistics computation."""
    print("\n=== Distribution Analysis ===")

    service = StatisticsService()

    np.random.seed(42)
    returns = list(np.random.normal(0.001, 0.02, 100))

    report = service.analyze("test_dist", returns, trade_count=50)

    dist = report.distribution
    print(f"Mean: {dist.mean:.6f}")
    print(f"Median: {dist.median:.6f}")
    print(f"Std Dev: {dist.std:.6f}")
    print(f"Variance: {dist.variance:.6f}")
    print(f"Skewness: {dist.skew:.6f}")
    print(f"Kurtosis: {dist.kurtosis:.6f}")

    assert -0.01 < dist.mean < 0.01
    assert dist.variance > 0
    assert dist.std > 0
    print("✓ Distribution analysis verified")


def verify_return_statistics():
    """Verify return statistics computation."""
    print("\n=== Return Statistics ===")

    service = StatisticsService()

    returns = [0.01, 0.02, -0.01, 0.015, -0.005, 0.03, -0.02, 0.01]

    report = service.analyze("test_returns", returns, trade_count=8, rolling_window=3)

    ret = report.returns
    print(f"Cumulative Return: {ret.cumulative_return:.6f}")
    print(f"Average Return: {ret.average_return:.6f}")
    print(f"Volatility: {ret.volatility:.6f}")
    print(f"Rolling Volatility Points: {len(ret.rolling_volatility) if ret.rolling_volatility else 0}")

    assert ret.cumulative_return != 0
    assert ret.volatility > 0
    assert ret.rolling_volatility is not None
    assert len(ret.rolling_volatility) == 6
    print("✓ Return statistics verified")


def verify_risk_statistics():
    """Verify risk metrics computation."""
    print("\n=== Risk Statistics ===")

    service = StatisticsService()

    np.random.seed(42)
    returns = list(np.random.normal(0.001, 0.02, 100))

    report = service.analyze("test_risk", returns, trade_count=50)

    risk = report.risk
    print(f"Volatility: {risk.volatility:.6f}")
    print(f"VaR (95%): {risk.var_95:.6f}")
    print(f"CVaR (95%): {risk.cvar_95:.6f}")
    print(f"Max Loss: {risk.max_loss:.6f}")
    print(f"Downside Deviation: {risk.downside_deviation:.6f}")

    assert risk.volatility > 0
    assert risk.var_95 < 0
    assert risk.cvar_95 < risk.var_95
    assert risk.max_loss < 0
    assert risk.downside_deviation > 0
    print("✓ Risk statistics verified")


def verify_sample_quality():
    """Verify sample quality analysis."""
    print("\n=== Sample Quality Analysis ===")

    service = StatisticsService()

    # Small sample
    small_returns = [0.01, -0.02, 0.015]
    report_small = service.analyze("test_small", small_returns, trade_count=3)

    quality_small = report_small.quality
    print(f"\nSmall Sample:")
    print(f"  Sample Size: {quality_small.sample_size}")
    print(f"  Trade Count: {quality_small.trade_count}")
    print(f"  Confidence Level: {quality_small.confidence_level:.4f}")
    print(f"  Warnings: {len(quality_small.warnings)}")
    for w in quality_small.warnings:
        print(f"    - {w}")

    assert quality_small.sample_size == 3
    assert len(quality_small.warnings) > 0

    # Large sample
    np.random.seed(42)
    large_returns = list(np.random.normal(0.002, 0.01, 200))
    report_large = service.analyze("test_large", large_returns, trade_count=150)

    quality_large = report_large.quality
    print(f"\nLarge Sample:")
    print(f"  Sample Size: {quality_large.sample_size}")
    print(f"  Trade Count: {quality_large.trade_count}")
    print(f"  Confidence Level: {quality_large.confidence_level:.4f}")
    print(f"  Warnings: {len(quality_large.warnings)}")

    assert quality_large.sample_size == 200
    assert quality_large.confidence_level > 0.5
    print("✓ Sample quality analysis verified")


def verify_deterministic_output():
    """Verify that analysis is deterministic."""
    print("\n=== Deterministic Output ===")

    service = StatisticsService()

    returns = [0.01, -0.02, 0.015, -0.005, 0.03]

    report1 = service.analyze("test_det", returns, trade_count=5)
    report2 = service.analyze("test_det", returns, trade_count=5)

    assert report1.distribution.mean == report2.distribution.mean
    assert report1.risk.var_95 == report2.risk.var_95
    assert report1.quality.confidence_level == report2.quality.confidence_level

    print("✓ Deterministic output verified")


def verify_edge_cases():
    """Verify edge case handling."""
    print("\n=== Edge Cases ===")

    service = StatisticsService()

    # Single return
    single_return = [0.01]
    report_single = service.analyze("test_single", single_return, trade_count=1)
    assert report_single.distribution.mean == 0.01
    assert report_single.quality.sample_size == 1
    print("✓ Single return handled")

    # Zero volatility
    constant_returns = [0.01] * 10
    report_constant = service.analyze("test_constant", constant_returns, trade_count=10)
    assert abs(report_constant.distribution.std) < 1e-10
    assert abs(report_constant.risk.volatility) < 1e-10
    print("✓ Zero volatility handled")

    # All negative returns
    negative_returns = [-0.01, -0.02, -0.015, -0.03]
    report_negative = service.analyze("test_negative", negative_returns, trade_count=4)
    assert report_negative.distribution.mean < 0
    assert report_negative.returns.cumulative_return < 0
    print("✓ All negative returns handled")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Statistical Toolkit Verification")
    print("=" * 60)

    try:
        verify_distribution_analysis()
        verify_return_statistics()
        verify_risk_statistics()
        verify_sample_quality()
        verify_deterministic_output()
        verify_edge_cases()

        print("\n" + "=" * 60)
        print("✓ All verifications passed")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        raise


if __name__ == "__main__":
    main()
