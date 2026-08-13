"""Tests for Research Benchmark Layer - Sprint 3.9D-1

Validates composite scoring, ranking, determinism, immutability, and boundaries.
"""

import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.reporting.models import ResearchReport
from ml_service.research.benchmark import (
    BenchmarkResult,
    DefaultResearchBenchmark,
    calculate_absolute_score,
)


def test_benchmark_result_immutability():
    """Verify that BenchmarkResult attributes are frozen and immutable."""
    result = BenchmarkResult(
        benchmark_id="bench_01",
        compared_experiments=("exp_1", "exp_2"),
        ranking=("exp_2", "exp_1"),
        winner="exp_2",
        scores=(("exp_1", 0.5), ("exp_2", 0.8))
    )

    with pytest.raises(FrozenInstanceError):
        result.winner = "exp_1"

    with pytest.raises(FrozenInstanceError):
        result.benchmark_id = "new_id"


def test_scoring_correctness():
    """Verify scoring computes weighted values correctly based on the formula."""
    # Excellent report: Sharpe=3.0, Sortino=3.0, PF=inf, WinRate=1.0, MaxDrawdown=0.0
    # Expected scores:
    # Sharpe (30%) -> 3/3 = 1.0 -> 0.3
    # Sortino (20%) -> 3/3 = 1.0 -> 0.2
    # PF (20%) -> inf = 1.0 -> 0.2
    # WinRate (15%) -> 1.0 -> 0.15
    # DD Recovery (15%) -> 1.0 - 0.0 = 1.0 -> 0.15
    # Total composite = 0.3 + 0.2 + 0.2 + 0.15 + 0.15 = 1.0
    excellent_report = ResearchReport(
        experiment_id="excel",
        total_signals=10,
        win_rate=1.0,
        average_return=0.05,
        total_return=0.5,
        max_drawdown=0.0,
        sharpe_ratio=3.0,
        sortino_ratio=3.0,
        profit_factor=float('inf')
    )

    score = calculate_absolute_score(excellent_report)
    assert score == pytest.approx(1.0)

    # Poor report: Sharpe=0.0, Sortino=0.0, PF=1.0 (or less), WinRate=0.0, MaxDrawdown=-100.0 (100% DD)
    # Expected score: all zero -> 0.0
    poor_report = ResearchReport(
        experiment_id="poor",
        total_signals=10,
        win_rate=0.0,
        average_return=-0.05,
        total_return=-0.5,
        max_drawdown=-100.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        profit_factor=0.5
    )

    score_poor = calculate_absolute_score(poor_report)
    assert score_poor == pytest.approx(0.0)


def test_ranking_correctness_and_ties():
    """Verify that rankings are correctly sorted descending by score and ties solved alphabetically."""
    reports = [
        # Scored at ~0.5
        ResearchReport(
            experiment_id="exp_b",
            total_signals=10,
            win_rate=0.5,
            average_return=0.01,
            total_return=0.1,
            max_drawdown=0.1,
            sharpe_ratio=1.5,
            sortino_ratio=1.5,
            profit_factor=1.5
        ),
        # Scored identical to exp_b to check alphabetical tie-breaker
        ResearchReport(
            experiment_id="exp_a",
            total_signals=10,
            win_rate=0.5,
            average_return=0.01,
            total_return=0.1,
            max_drawdown=0.1,
            sharpe_ratio=1.5,
            sortino_ratio=1.5,
            profit_factor=1.5
        ),
        # High performer
        ResearchReport(
            experiment_id="exp_high",
            total_signals=10,
            win_rate=0.8,
            average_return=0.03,
            total_return=0.3,
            max_drawdown=0.02,
            sharpe_ratio=2.5,
            sortino_ratio=2.5,
            profit_factor=3.0
        ),
    ]

    benchmarker = DefaultResearchBenchmark(benchmark_id="test_bench")
    result = benchmarker.compare(reports)

    # exp_high should be 1st
    # exp_a and exp_b have identical score, so sorted alphabetically -> exp_a before exp_b
    assert result.winner == "exp_high"
    assert result.ranking == ("exp_high", "exp_a", "exp_b")
    assert result.compared_experiments == ("exp_b", "exp_a", "exp_high")


def test_empty_reports_error():
    """Verify benchmarker raises ValueError on empty list."""
    benchmarker = DefaultResearchBenchmark()
    with pytest.raises(ValueError, match="Cannot benchmark empty reports list"):
        benchmarker.compare([])


def test_dependency_isolation():
    """Ensure benchmark package does not couple with database or execution environments."""
    forbidden_modules = [
        "sqlite3",
        "sqlalchemy",
        "psycopg2",
        "ml_service.trading",
        "ml_service.portfolio",
    ]
    
    files_to_check = [
        "ml_service/research/benchmark/models.py",
        "ml_service/research/benchmark/interfaces.py",
        "ml_service/research/benchmark/scoring.py",
        "ml_service/research/benchmark/benchmark.py",
    ]
    
    for filepath in files_to_check:
        with open(filepath, "r") as f:
            content = f.read()
            for forbidden in forbidden_modules:
                assert forbidden not in content, f"Forbidden import of {forbidden} found in {filepath}"
