"""Test immutability and serialization of strategy domain models."""

import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.strategy.models import (
    StrategyState,
    FeatureSnapshot,
    Signal,
    SignalAction,
    StrategyResult,
)
from ml_service.research.strategy.inference.models import Prediction


def test_strategy_state_immutable():
    """Verify StrategyState is immutable."""
    state = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
        parameters=(("param1", 1.0), ("param2", "value")),
        internal_state=(("counter", 5),),
    )

    with pytest.raises(FrozenInstanceError):
        state.strategy_id = "modified"

    with pytest.raises(FrozenInstanceError):
        state.timestamp = "2024-01-02T00:00:00Z"

    with pytest.raises(FrozenInstanceError):
        state.parameters = (("new_param", 2.0),)


def test_feature_snapshot_immutable():
    """Verify FeatureSnapshot is immutable."""
    snapshot = FeatureSnapshot(
        timestamp="2024-01-01T00:00:00Z",
        features=(("feature1", 1.5), ("feature2", 2.5)),
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.timestamp = "2024-01-02T00:00:00Z"

    with pytest.raises(FrozenInstanceError):
        snapshot.features = (("new_feature", 3.0),)


def test_prediction_immutable():
    """Verify Prediction is immutable."""
    prediction = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="v1.0",
        probability=0.75,
        direction="UP",
    )

    with pytest.raises(FrozenInstanceError):
        prediction.timestamp = "2024-01-02T00:00:00Z"

    with pytest.raises(FrozenInstanceError):
        prediction.probability = 0.85

    with pytest.raises(FrozenInstanceError):
        prediction.direction = "DOWN"


def test_strategy_models_no_longer_owns_prediction():
    """Verify strategy.models does not define or own Prediction."""
    import ml_service.research.strategy.models as strategy_models
    assert not hasattr(strategy_models, "Prediction")


def test_signal_immutable():
    """Verify Signal is immutable."""
    signal = Signal(
        timestamp="2024-01-01T00:00:00Z",
        action=SignalAction.LONG,
        confidence=0.85,
        metadata=(("reason", "momentum"),),
    )

    with pytest.raises(FrozenInstanceError):
        signal.timestamp = "2024-01-02T00:00:00Z"

    with pytest.raises(FrozenInstanceError):
        signal.action = SignalAction.SHORT

    with pytest.raises(FrozenInstanceError):
        signal.confidence = 0.95


def test_strategy_result_immutable():
    """Verify StrategyResult is immutable."""
    state = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
    )
    signal = Signal(
        timestamp="2024-01-01T00:00:00Z",
        action=SignalAction.LONG,
        confidence=0.85,
    )
    result = StrategyResult(new_state=state, signal=signal)

    with pytest.raises(FrozenInstanceError):
        result.new_state = state

    with pytest.raises(FrozenInstanceError):
        result.signal = None


def test_strategy_state_deterministic_serialization():
    """Verify StrategyState serialization is deterministic."""
    state1 = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
        parameters=(("b", 2), ("a", 1)),
        internal_state=(("y", 20), ("x", 10)),
    )
    state2 = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
        parameters=(("a", 1), ("b", 2)),
        internal_state=(("x", 10), ("y", 20)),
    )

    assert state1.serialize() == state2.serialize()


def test_signal_action_enum():
    """Verify SignalAction enum values."""
    assert SignalAction.LONG.value == "LONG"
    assert SignalAction.SHORT.value == "SHORT"
    assert SignalAction.FLAT.value == "FLAT"


def test_strategy_state_to_dict():
    """Verify StrategyState to_dict produces sorted output."""
    state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
        parameters=(("c", 3), ("a", 1), ("b", 2)),
    )
    result = state.to_dict()

    assert result["parameters"] == [["a", 1], ["b", 2], ["c", 3]]


def test_signal_to_dict():
    """Verify Signal to_dict produces sorted metadata."""
    signal = Signal(
        timestamp="2024-01-01T00:00:00Z",
        action=SignalAction.LONG,
        confidence=0.85,
        metadata=(("z", 26), ("a", 1), ("m", 13)),
    )
    result = signal.to_dict()

    assert result["metadata"] == [["a", 1], ["m", 13], ["z", 26]]
    assert result["action"] == "LONG"
