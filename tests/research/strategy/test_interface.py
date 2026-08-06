"""Test Strategy interface contract and deterministic behavior."""

from datetime import datetime
import pytest
from dataclasses import replace
from ml_service.research.strategy.models import (
    StrategyState,
    StrategyResult,
    Signal,
    SignalAction,
    FeatureSnapshot,
)
from ml_service.research.strategy.interfaces import Strategy, MarketSnapshot
from ml_service.research.strategy.inference.models import Prediction


class DummyStrategy(Strategy):
    """Test implementation of Strategy interface."""

    def initialize(self, state: StrategyState) -> StrategyState:
        return replace(
            state,
            internal_state=(("initialized", True),),
        )

    def process(
        self,
        market_snapshot: MarketSnapshot,
        state: StrategyState,
        feature_snapshot: FeatureSnapshot = None,
        prediction: Prediction = None,
    ) -> StrategyResult:
        counter_value = 0
        for key, value in state.internal_state:
            if key == "counter":
                counter_value = value
                break

        new_counter = counter_value + 1

        updated_internal_state = tuple(
            (k, v) if k != "counter" else (k, new_counter)
            for k, v in state.internal_state
        )
        if not any(k == "counter" for k, v in state.internal_state):
            updated_internal_state = state.internal_state + (("counter", new_counter),)

        new_state = replace(state, internal_state=updated_internal_state)

        signal = None
        # Use prediction/feature snapshot if provided to influence signal logic
        confidence = 0.8
        if prediction is not None:
            confidence = prediction.probability

        if new_counter % 2 == 0:
            signal = Signal(
                timestamp=state.timestamp,
                action=SignalAction.LONG if (prediction is None or prediction.direction == "UP") else SignalAction.SHORT,
                confidence=confidence,
            )

        return StrategyResult(new_state=new_state, signal=signal)


def test_strategy_interface_contract():
    """Verify Strategy interface contract."""
    strategy = DummyStrategy()

    initial_state = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
    )

    initialized_state = strategy.initialize(initial_state)

    assert initialized_state.strategy_id == initial_state.strategy_id
    assert initialized_state.timestamp == initial_state.timestamp
    assert ("initialized", True) in initialized_state.internal_state

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    result = strategy.process(market, initialized_state)

    assert isinstance(result, StrategyResult)
    assert isinstance(result.new_state, StrategyState)
    assert result.new_state.strategy_id == initialized_state.strategy_id


def test_strategy_deterministic_output():
    """Verify strategy produces deterministic output for same input."""
    strategy = DummyStrategy()

    state = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("counter", 5),),
    )

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )

    result1 = strategy.process(market, state)
    result2 = strategy.process(market, state)

    assert result1.new_state.serialize() == result2.new_state.serialize()

    if result1.signal and result2.signal:
        assert result1.signal.action == result2.signal.action
        assert result1.signal.confidence == result2.signal.confidence
        assert result1.signal.timestamp == result2.signal.timestamp


def test_strategy_state_transitions_pure():
    """Verify strategy doesn't mutate input state."""
    strategy = DummyStrategy()

    original_state = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("counter", 1),),
    )

    original_counter = None
    for key, value in original_state.internal_state:
        if key == "counter":
            original_counter = value
            break

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    result = strategy.process(market, original_state)

    current_counter = None
    for key, value in original_state.internal_state:
        if key == "counter":
            current_counter = value
            break

    assert current_counter == original_counter
    assert original_state is not result.new_state


def test_strategy_signal_generation():
    """Verify strategy signal generation logic."""
    strategy = DummyStrategy()

    state_odd = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("counter", 1),),
    )

    state_even = StrategyState(
        strategy_id="test-strategy",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("counter", 2),),
    )

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )

    result_odd = strategy.process(market, state_odd)
    assert result_odd.signal is not None

    result_even = strategy.process(market, state_even)
    assert result_even.signal is None


def test_strategy_receives_feature_snapshot():
    """Verify strategy receives and can use FeatureSnapshot."""
    strategy = DummyStrategy()
    state = StrategyState(strategy_id="test", timestamp="2024-01-01T00:00:00Z")
    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    feature_snap = FeatureSnapshot(
        timestamp="2024-01-01T00:00:00Z",
        features=(("rsi_14", 45.0),),
    )
    
    result = strategy.process(market, state, feature_snapshot=feature_snap)
    assert result is not None


def test_strategy_receives_prediction():
    """Verify strategy receives and can use Prediction."""
    strategy = DummyStrategy()
    state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("counter", 1),),
    )
    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    prediction = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.92,
    )

    result = strategy.process(market, state, prediction=prediction)
    assert result.signal is not None
    assert result.signal.confidence == 0.92

