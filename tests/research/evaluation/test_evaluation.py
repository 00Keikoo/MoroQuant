"""Tests for Research Evaluation Layer - Sprint 3.9C-3

Validates evaluation metrics calculations, immutability, determinism, and boundaries.
"""

from datetime import datetime
import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.strategy.models import Signal, SignalAction
from ml_service.research.strategy.inference.models import Prediction
from ml_service.simulation.models import MarketSnapshot
from ml_service.research.evaluation.models import EvaluationResult
from ml_service.research.evaluation.evaluator import DefaultSignalEvaluator


def test_deterministic_evaluation():
    """Verify that identical inputs produce identical evaluation result scorecards."""
    evaluator = DefaultSignalEvaluator()
    
    signal = Signal(timestamp="2024-01-01T00:00:00Z", action=SignalAction.LONG, confidence=0.88)
    prediction = Prediction(timestamp="2024-01-01T00:00:00Z", model_version_id="model_v1", direction="UP", probability=0.88)
    
    future_snapshots = [
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:00:00"), symbol="BTCUSD", mid_price=100.0),
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:01:00"), symbol="BTCUSD", mid_price=102.5),
    ]

    result1 = evaluator.evaluate(signal, prediction, future_snapshots)
    result2 = evaluator.evaluate(signal, prediction, future_snapshots)

    assert result1 == result2
    assert result1.forward_return == pytest.approx(0.025)
    assert result1.is_correct is True
    assert result1.is_hit is True


def test_evaluation_result_immutability():
    """Verify generated EvaluationResult scorecard is frozen."""
    evaluator = DefaultSignalEvaluator()
    
    signal = Signal(timestamp="2024-01-01T00:00:00Z", action=SignalAction.LONG, confidence=0.88)
    prediction = Prediction(timestamp="2024-01-01T00:00:00Z", model_version_id="model_v1", direction="UP", probability=0.88)
    
    future_snapshots = [
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:00:00"), symbol="BTCUSD", mid_price=100.0),
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:01:00"), symbol="BTCUSD", mid_price=102.5),
    ]

    result = evaluator.evaluate(signal, prediction, future_snapshots)

    with pytest.raises(FrozenInstanceError):
        result.is_correct = False

    with pytest.raises(FrozenInstanceError):
        result.forward_return = 0.5


def test_hit_miss_short_correct():
    """Verify correct SHORT prediction results in a hit."""
    evaluator = DefaultSignalEvaluator()
    
    signal = Signal(timestamp="2024-01-01T00:00:00Z", action=SignalAction.SHORT, confidence=0.88)
    prediction = Prediction(timestamp="2024-01-01T00:00:00Z", model_version_id="model_v1", direction="DOWN", probability=0.88)
    
    future_snapshots = [
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:00:00"), symbol="BTCUSD", mid_price=100.0),
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:01:00"), symbol="BTCUSD", mid_price=95.0),
    ]

    result = evaluator.evaluate(signal, prediction, future_snapshots)
    assert result.is_correct is True
    assert result.forward_return == pytest.approx(0.05)
    assert result.is_hit is True


def test_hit_miss_wrong():
    """Verify incorrect prediction results in a miss."""
    evaluator = DefaultSignalEvaluator()
    
    signal = Signal(timestamp="2024-01-01T00:00:00Z", action=SignalAction.LONG, confidence=0.88)
    prediction = Prediction(timestamp="2024-01-01T00:00:00Z", model_version_id="model_v1", direction="UP", probability=0.88)
    
    future_snapshots = [
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:00:00"), symbol="BTCUSD", mid_price=100.0),
        MarketSnapshot(timestamp=datetime.fromisoformat("2024-01-01T00:01:00"), symbol="BTCUSD", mid_price=95.0),
    ]

    result = evaluator.evaluate(signal, prediction, future_snapshots)
    assert result.is_correct is False
    assert result.forward_return == pytest.approx(-0.05)
    assert result.is_hit is False


def test_isolation_no_execution_dependency():
    """Ensure evaluator does not import database or execution simulator components."""
    import ast
    
    files_to_check = [
        "ml_service/research/evaluation/evaluator.py",
        "ml_service/research/evaluation/interfaces.py",
        "ml_service/research/evaluation/models.py",
    ]
    
    forbidden = [
        "ml_service.simulation.execution",
        "ml_service.simulation.portfolio",
        "sqlite3",
    ]
    
    for filepath in files_to_check:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for f_mod in forbidden:
                        assert f_mod not in alias.name, f"Forbidden import {alias.name} in {filepath}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for f_mod in forbidden:
                        assert f_mod not in node.module, f"Forbidden import from {node.module} in {filepath}"
