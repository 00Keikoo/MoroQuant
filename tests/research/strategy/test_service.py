"""Test StrategyService orchestration."""

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
from ml_service.research.strategy.service import StrategyService
from ml_service.research.strategy.inference.models import Prediction


class MockStrategy(Strategy):
    """Mock strategy for testing service."""

    def initialize(self, state: StrategyState) -> StrategyState:
        return replace(state, internal_state=(("initialized", True),))

    def process(
        self,
        market_snapshot: MarketSnapshot,
        state: StrategyState,
        feature_snapshot: FeatureSnapshot = None,
        prediction: Prediction = None,
    ) -> StrategyResult:
        new_state = replace(
            state,
            internal_state=state.internal_state + (("processed", True),),
        )
        signal = Signal(
            timestamp=state.timestamp,
            action=SignalAction.LONG,
            confidence=0.75,
        )
        return StrategyResult(new_state=new_state, signal=signal)


def test_strategy_service_initialization():
    """Verify StrategyService initializes strategy correctly."""
    strategy = MockStrategy()
    service = StrategyService(strategy)

    initial_state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
    )

    initialized_state = service.initialize_strategy(initial_state)

    assert ("initialized", True) in initialized_state.internal_state
    assert initialized_state.strategy_id == initial_state.strategy_id


def test_strategy_service_process_market():
    """Verify StrategyService processes market snapshots."""
    strategy = MockStrategy()
    service = StrategyService(strategy)

    state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("initialized", True),),
    )

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    result = service.process_market_snapshot(market, state)

    assert isinstance(result, StrategyResult)
    assert ("processed", True) in result.new_state.internal_state
    assert result.signal is not None


def test_strategy_service_get_latest_signal():
    """Verify StrategyService extracts signals correctly."""
    strategy = MockStrategy()
    service = StrategyService(strategy)

    state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
    )

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    result = service.process_market_snapshot(market, state)

    signal = service.get_latest_signal(result)

    assert signal is not None
    assert signal.action == SignalAction.LONG
    assert signal.confidence == 0.75


def test_strategy_service_no_signal():
    """Verify StrategyService handles no signal case."""

    class NoSignalStrategy(Strategy):
        def initialize(self, state: StrategyState) -> StrategyState:
            return state

        def process(
            self,
            market_snapshot: MarketSnapshot,
            state: StrategyState,
            feature_snapshot: FeatureSnapshot = None,
            prediction: Prediction = None,
        ) -> StrategyResult:
            return StrategyResult(new_state=state, signal=None)

    strategy = NoSignalStrategy()
    service = StrategyService(strategy)

    state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
    )

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    result = service.process_market_snapshot(market, state)

    signal = service.get_latest_signal(result)
    assert signal is None


def test_strategy_service_immutability():
    """Verify StrategyService maintains immutability contract."""
    strategy = MockStrategy()
    service = StrategyService(strategy)

    original_state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
        internal_state=(("counter", 1),),
    )

    original_internal_state = original_state.internal_state

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )
    result = service.process_market_snapshot(market, original_state)

    assert original_state.internal_state == original_internal_state
    assert result.new_state is not original_state


def test_strategy_service_full_pipeline_orchestration():
    """Verify that StrategyService coordinates the full pipeline.

    Flow: MarketSnapshot -> FeatureContext -> FeatureSnapshot -> MLInferenceAdapter -> Strategy.process
    """
    from unittest.mock import Mock
    from ml_service.research.strategy.features.feature_context_service import FeatureContextService
    from ml_service.research.strategy.inference.adapter import MLInferenceAdapter
    from ml_service.research.strategy.inference.models import InferenceResult, ModelMetadata

    # 1. Setup mocks
    strategy = MockStrategy()
    feature_service = Mock(spec=FeatureContextService)
    inference_adapter = Mock(spec=MLInferenceAdapter)

    # Mock FeatureSnapshot output from builder/service
    feature_snap = FeatureSnapshot(
        timestamp="2024-01-01T00:00:00Z",
        features=(("rsi_14", 45.0),),
    )
    feature_service.has_context.return_value = True
    feature_service.build_snapshot.return_value = feature_snap

    # Mock Prediction output from adapter
    prediction = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.88,
    )
    metadata = ModelMetadata(
        model_id="BTCUSD",
        model_version_id="model_v1",
        framework="xgboost",
        feature_schema=("rsi_14",),
        fingerprint="fingerprint_xyz",
    )
    inference_result = InferenceResult(
        prediction=prediction,
        metadata=metadata,
        executed_at="2026-08-06T00:00:00Z",
        latency_ms=1.5,
    )
    inference_adapter.predict.return_value = inference_result

    # 2. Initialize orchestrator with full dependencies
    service = StrategyService(
        strategy=strategy,
        feature_service=feature_service,
        inference_adapter=inference_adapter,
        model_version_id="model_v1",
    )

    state = StrategyState(
        strategy_id="test",
        timestamp="2024-01-01T00:00:00Z",
    )

    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )

    # Spy on strategy.process call by wrapping it
    original_process = strategy.process
    calls = []
    def spy_process(market_snapshot, state, feature_snapshot=None, prediction=None):
        calls.append((feature_snapshot, prediction))
        return original_process(market_snapshot, state, feature_snapshot, prediction)

    strategy.process = spy_process

    # 3. Execute
    result = service.process_market_snapshot(market, state)

    # 4. Assertions
    # Verify feature context service was called
    feature_service.has_context.assert_called_once_with("BTCUSD")
    feature_service.update_context.assert_called_once_with("BTCUSD", market)
    feature_service.build_snapshot.assert_called_once_with("BTCUSD")

    # Verify inference adapter was called with generated feature snapshot
    inference_adapter.predict.assert_called_once_with("model_v1", feature_snap)

    # Verify strategy received correct feature snapshot and prediction
    assert len(calls) == 1
    passed_feat, passed_pred = calls[0]
    assert passed_feat == feature_snap
    assert passed_pred == prediction

    assert isinstance(result, StrategyResult)
    assert result.signal is not None


def test_strategy_service_signal_pipeline_integration():
    """Verify that SignalGenerator integration coordinates prediction to signal pipeline."""
    from unittest.mock import Mock
    from ml_service.research.strategy.signal.interfaces import SignalGenerator

    # 1. Setup strategy, mocks, and generator
    strategy = MockStrategy()
    signal_generator = Mock(spec=SignalGenerator)

    # Injected prediction
    prediction = Prediction(
        timestamp="2024-01-01T00:00:00Z",
        model_version_id="model_v1",
        direction="UP",
        probability=0.88,
    )
    
    # Mock generated signal
    expected_signal = Signal(
        timestamp="2024-01-01T00:00:00Z",
        action=SignalAction.LONG,
        confidence=0.88,
        metadata=(("test", True),),
    )
    signal_generator.generate.return_value = expected_signal

    # 2. Inject SignalGenerator into service
    service = StrategyService(
        strategy=strategy,
        signal_generator=signal_generator,
    )

    state = StrategyState(strategy_id="test", timestamp="2024-01-01T00:00:00Z")
    market = MarketSnapshot(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
        symbol="BTCUSD",
        mid_price=100.0,
    )

    # 3. Execute
    result = service.process_market_snapshot(market, state, prediction=prediction)

    # 4. Assertions
    # Verify SignalGenerator.generate was called with correct parameters
    signal_generator.generate.assert_called_once_with(prediction, None, state)

    # Verify that the generated signal was merged into final StrategyResult
    assert result.signal == expected_signal
    assert result.new_state.strategy_id == "test"



