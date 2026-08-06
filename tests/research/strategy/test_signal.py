"""Tests for Signal Generation Layer - Sprint 3.9C-1

Validates threshold behavior, immutability, determinism, and boundaries.
"""

import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.strategy.models import (
    StrategyState,
    FeatureSnapshot,
    Signal,
    SignalAction,
)
from ml_service.research.strategy.inference.models import Prediction
from ml_service.research.strategy.signal.generator import DefaultSignalGenerator


def test_default_signal_generator_validation():
    """Verify threshold boundary validation during initialization."""
    with pytest.raises(ValueError):
        DefaultSignalGenerator(entry_threshold=0.5, exit_threshold=0.6)

    with pytest.raises(ValueError):
        DefaultSignalGenerator(entry_threshold=1.2)


def test_deterministic_signal_generation():
    """Verify that identical inputs produce identical signal outputs."""
    generator = DefaultSignalGenerator(entry_threshold=0.6, exit_threshold=0.5)
    
    prediction = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.75,
    )
    state = StrategyState(strategy_id="test", timestamp="2024-01-01T00:00:00Z")
    features = FeatureSnapshot(timestamp="2024-01-01T00:00:00Z")

    signal1 = generator.generate(prediction, features, state)
    signal2 = generator.generate(prediction, features, state)

    assert signal1 == signal2
    assert signal1.action == SignalAction.LONG
    assert signal1.confidence == 0.75


def test_signal_output_immutability():
    """Verify generated Signal is frozen/immutable."""
    generator = DefaultSignalGenerator(entry_threshold=0.6, exit_threshold=0.5)
    prediction = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="DOWN",
        probability=0.85,
    )
    state = StrategyState(strategy_id="test", timestamp="2024-01-01T00:00:00Z")
    
    signal = generator.generate(prediction, None, state)
    assert signal.action == SignalAction.SHORT

    with pytest.raises(FrozenInstanceError):
        signal.action = SignalAction.FLAT

    with pytest.raises(FrozenInstanceError):
        signal.confidence = 0.99


def test_threshold_behavior_long():
    """Verify LONG triggers only above entry threshold."""
    generator = DefaultSignalGenerator(entry_threshold=0.7, exit_threshold=0.5)
    state = StrategyState(strategy_id="test", timestamp="2024-01-01T00:00:00Z")

    # Probability below exit threshold -> FLAT
    p_flat = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.45,
    )
    signal_flat = generator.generate(p_flat, None, state)
    assert signal_flat.action == SignalAction.FLAT

    # Probability in deadband (between exit and entry) -> None
    p_none = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.6,
    )
    signal_none = generator.generate(p_none, None, state)
    assert signal_none is None

    # Probability above entry -> LONG
    p_long = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.75,
    )
    signal_long = generator.generate(p_long, None, state)
    assert signal_long.action == SignalAction.LONG


def test_threshold_behavior_short():
    """Verify SHORT triggers only above entry threshold."""
    generator = DefaultSignalGenerator(entry_threshold=0.7, exit_threshold=0.5)
    state = StrategyState(strategy_id="test", timestamp="2024-01-01T00:00:00Z")

    # Probability above entry -> SHORT
    p_short = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="SHORT",
        probability=0.72,
    )
    signal_short = generator.generate(p_short, None, state)
    assert signal_short.action == SignalAction.SHORT


def test_isolation_no_execution_imports():
    """Ensure signal generator doesn't import database or execution simulator components."""
    import ast
    
    files_to_check = [
        "ml_service/research/strategy/signal/generator.py",
        "ml_service/research/strategy/signal/interfaces.py",
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
