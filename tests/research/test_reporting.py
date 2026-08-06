"""Tests for Research Reporting Engine - Sprint 3.9C-6

Validates metrics correctness, immutability, deterministic serialization, and dependency boundaries.
"""

import pytest
import json
from dataclasses import FrozenInstanceError
from ml_service.research.evaluation.models import EvaluationResult
from ml_service.research.reporting import ResearchReport, DefaultResearchAnalytics


def test_research_report_immutability():
    """Verify that ResearchReport attributes are frozen and cannot be modified."""
    report = ResearchReport(
        experiment_id="exp_01",
        total_signals=10,
        win_rate=0.6,
        average_return=0.015,
        total_return=0.15,
        max_drawdown=0.05,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        profit_factor=2.5,
        metrics=(("custom_metric", 42.0),)
    )

    with pytest.raises(FrozenInstanceError):
        report.win_rate = 0.8

    with pytest.raises(FrozenInstanceError):
        report.experiment_id = "new_exp"


def test_research_report_deterministic_serialization():
    """Verify that serialization is deterministic and stable."""
    metrics = (
        ("beta", 0.95),
        ("alpha", 0.02),
        ("gamma", 0.11),
    )
    report = ResearchReport(
        experiment_id="exp_02",
        total_signals=100,
        win_rate=0.55,
        average_return=0.002,
        total_return=0.20,
        max_drawdown=0.12,
        sharpe_ratio=1.1,
        sortino_ratio=1.3,
        profit_factor=1.45,
        metrics=metrics
    )

    dict_repr = report.to_dict()
    # Check that keys are correctly populated
    assert dict_repr["experiment_id"] == "exp_02"
    
    # Check that metrics in dict are sorted alphabetically by key
    assert dict_repr["metrics"] == [["alpha", 0.02], ["beta", 0.95], ["gamma", 0.11]]

    # Ensure JSON output is deterministic and sorted
    json_str_1 = report.to_json()
    json_str_2 = report.to_json()
    assert json_str_1 == json_str_2

    # Verify that reloading the JSON maintains metrics list structure
    loaded = json.loads(json_str_1)
    assert loaded["metrics"] == [["alpha", 0.02], ["beta", 0.95], ["gamma", 0.11]]


def test_metrics_correctness_basic():
    """Test metrics calculation with simple deterministic signals."""
    # 5 evaluations: 3 positive, 2 negative returns
    # timestamps out of order to verify chronological sorting for drawdown
    results = [
        EvaluationResult(
            signal_timestamp="2026-08-01T12:00:00Z",
            action="LONG",
            predicted_direction="UP",
            actual_direction="UP",
            is_correct=True,
            forward_return=0.02,
            is_hit=True
        ),
        EvaluationResult(
            signal_timestamp="2026-08-01T12:02:00Z",
            action="LONG",
            predicted_direction="UP",
            actual_direction="DOWN",
            is_correct=False,
            forward_return=-0.01,
            is_hit=False
        ),
        EvaluationResult(
            signal_timestamp="2026-08-01T12:01:00Z",
            action="LONG",
            predicted_direction="UP",
            actual_direction="UP",
            is_correct=True,
            forward_return=0.03,
            is_hit=True
        ),
        EvaluationResult(
            signal_timestamp="2026-08-01T12:03:00Z",
            action="SHORT",
            predicted_direction="DOWN",
            actual_direction="DOWN",
            is_correct=True,
            forward_return=0.01,
            is_hit=True
        ),
        EvaluationResult(
            signal_timestamp="2026-08-01T12:04:00Z",
            action="SHORT",
            predicted_direction="DOWN",
            actual_direction="UP",
            is_correct=False,
            forward_return=-0.02,
            is_hit=False
        ),
    ]

    analytics = DefaultResearchAnalytics()
    report = analytics.evaluate(results, "exp_basic")

    assert report.experiment_id == "exp_basic"
    assert report.total_signals == 5
    assert report.win_rate == pytest.approx(0.6)  # 3 correct out of 5
    assert report.average_return == pytest.approx(0.006)  # (0.02 + 0.03 - 0.01 + 0.01 - 0.02) / 5 = 0.03 / 5 = 0.006
    assert report.total_return == pytest.approx(0.03)  # Sum of returns = 0.03
    assert report.profit_factor == pytest.approx(2.0)  # Wins sum: 0.06, Losses sum: 0.03. PF = 2.0

    # Drawdown verification:
    # Sorted:
    # 1. 2026-08-01T12:00:00Z -> ret = 0.02 -> Eq = 1.02, Peak = 1.02
    # 2. 2026-08-01T12:01:00Z -> ret = 0.03 -> Eq = 1.02 * 1.03 = 1.0506, Peak = 1.0506
    # 3. 2026-08-01T12:02:00Z -> ret = -0.01 -> Eq = 1.0506 * 0.99 = 1.040094, Peak = 1.0506. DD = (1.0506 - 1.040094)/1.0506 = 0.01 (1%)
    # 4. 2026-08-01T12:03:00Z -> ret = 0.01 -> Eq = 1.040094 * 1.01 = 1.05049494, Peak = 1.0506
    # 5. 2026-08-01T12:04:00Z -> ret = -0.02 -> Eq = 1.05049494 * 0.98 = 1.029485, Peak = 1.0506. DD = (1.0506 - 1.029485)/1.0506 = 0.0201 (2.01%)
    # Multiplicative max drawdown should be approx 0.0201 (2.01%)
    assert report.max_drawdown == pytest.approx(0.0201, abs=1e-4)


def test_empty_results():
    """Verify that analytics handles empty results lists gracefully."""
    analytics = DefaultResearchAnalytics()
    report = analytics.evaluate([], "exp_empty")

    assert report.experiment_id == "exp_empty"
    assert report.total_signals == 0
    assert report.win_rate == 0.0
    assert report.average_return == 0.0
    assert report.total_return == 0.0
    assert report.max_drawdown == 0.0
    assert report.sharpe_ratio == 0.0
    assert report.sortino_ratio == 0.0
    assert report.profit_factor == 0.0
    assert report.metrics == ()


def test_dependency_isolation():
    """Ensure the reporting package does not import database, network, or execution-coupled layers."""
    import sys
    
    # Check that typical database or execution module names are not in the module's dependencies
    forbidden_modules = [
        "sqlite3",
        "sqlalchemy",
        "psycopg2",
        "ml_service.trading",
        "ml_service.portfolio",
    ]
    
    # Read files to check for imports
    files_to_check = [
        "ml_service/research/reporting/models.py",
        "ml_service/research/reporting/interfaces.py",
        "ml_service/research/reporting/analytics.py",
    ]
    
    for filepath in files_to_check:
        with open(filepath, "r") as f:
            content = f.read()
            for forbidden in forbidden_modules:
                assert forbidden not in content, f"Forbidden import of {forbidden} found in {filepath}"
