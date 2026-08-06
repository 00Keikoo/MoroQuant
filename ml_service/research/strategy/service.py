"""Strategy Service - Sprint 3.9B-1 / 3.9B-2B

Manages strategy lifecycle following ADR-024.
Pure orchestration - no portfolio/order execution logic.

Sprint 3.9B-2B: Integrated FeatureContext layer into strategy flow.
"""

from dataclasses import replace
from typing import Optional
from ml_service.research.strategy.models import (
    StrategyState,
    StrategyResult,
    Signal,
    FeatureSnapshot,
)
from ml_service.research.strategy.interfaces import Strategy, MarketSnapshot
from ml_service.research.strategy.features import FeatureContextService


from ml_service.research.strategy.inference.models import Prediction
from ml_service.research.strategy.inference.adapter import MLInferenceAdapter
from ml_service.research.strategy.signal.interfaces import SignalGenerator


class StrategyService:
    """Orchestrates strategy execution following ADR-024.

    Responsibilities:
    - Manage strategy lifecycle
    - Call strategy interface
    - Integrate feature context layer (Sprint 3.9B-2B)
    - Integrate ML inference adapter layer (Sprint 3.9B-5C)
    - Integrate Signal Generator layer (Sprint 3.9C-2)
    - Produce immutable outputs

    MUST NOT:
    - Calculate portfolio
    - Execute orders
    - Access database
    - Mutate state
    """

    def __init__(
        self,
        strategy: Strategy,
        feature_service: Optional[FeatureContextService] = None,
        inference_adapter: Optional[MLInferenceAdapter] = None,
        model_version_id: Optional[str] = None,
        signal_generator: Optional[SignalGenerator] = None,
    ):
        """Initialize service with strategy implementation and core services.

        Args:
            strategy: Strategy implementation to manage
            feature_service: Optional feature context service for feature layer integration
            inference_adapter: Optional ML inference adapter for executing predictions
            model_version_id: Optional semantic model identifier to run predictions with
            signal_generator: Optional signal generator for mapping predictions to signals
        """
        self._strategy = strategy
        self._feature_service = feature_service
        self._inference_adapter = inference_adapter
        self._model_version_id = model_version_id
        self._signal_generator = signal_generator

    def initialize_strategy(self, initial_state: StrategyState) -> StrategyState:
        """Initialize strategy state.

        Args:
            initial_state: Initial strategy state

        Returns:
            Initialized state (potentially modified by strategy)

        Rules:
            - Pure function
            - No side effects
            - Returns new state
        """
        return self._strategy.initialize(initial_state)

    def process_market_snapshot(
        self,
        market_snapshot: MarketSnapshot,
        current_state: StrategyState,
        feature_snapshot: Optional[FeatureSnapshot] = None,
        prediction: Optional[Prediction] = None,
    ) -> StrategyResult:
        """Process market data and produce strategy decision.

        Flow (Sprint 3.9C-2 integrated pipeline):
        1. MarketSnapshot arrives
        2. If feature service configured:
           - Update FeatureContext with snapshot
           - Build FeatureSnapshot from context (if not provided)
        3. If ML inference adapter and model_version_id configured:
           - Call MLInferenceAdapter to run model prediction (if prediction not provided)
        4. If SignalGenerator dependency is configured (and prediction exists):
           - Call SignalGenerator to generate the Signal
        5. Call strategy.process() with market snapshot, feature snapshot, and prediction
        6. If Signal was generated, merge it into final StrategyResult
        7. Return StrategyResult

        Args:
            market_snapshot: Current market data
            current_state: Current strategy state
            feature_snapshot: Optional pre-calculated feature snapshot
            prediction: Optional ML model prediction

        Returns:
            StrategyResult with new state and optional signal

        Rules:
            - Pure function
            - No side effects
            - Deterministic
            - No order execution
            - No portfolio calculation
        """
        if self._feature_service:
            symbol = market_snapshot.symbol

            if not self._feature_service.has_context(symbol):
                self._feature_service.initialize_context(symbol)

            self._feature_service.update_context(symbol, market_snapshot)
            if feature_snapshot is None:
                feature_snapshot = self._feature_service.build_snapshot(symbol)

        if self._inference_adapter and self._model_version_id and feature_snapshot and prediction is None:
            inference_result = self._inference_adapter.predict(
                self._model_version_id,
                feature_snapshot
            )
            prediction = inference_result.prediction

        signal = None
        if self._signal_generator and prediction:
            signal = self._signal_generator.generate(
                prediction,
                feature_snapshot,
                current_state
            )

        result = self._strategy.process(
            market_snapshot,
            current_state,
            feature_snapshot=feature_snapshot,
            prediction=prediction,
        )

        if signal is not None:
            result = StrategyResult(new_state=result.new_state, signal=signal)

        return result

    def get_latest_signal(self, result: StrategyResult) -> Optional[Signal]:
        """Extract signal from strategy result.

        Args:
            result: Strategy execution result

        Returns:
            Signal if present, None otherwise

        Rules:
            - Pure getter
            - No side effects
        """
        return result.signal

    def get_feature_snapshot(self, symbol: str) -> Optional[FeatureSnapshot]:
        """Get current feature snapshot for symbol.

        Args:
            symbol: Trading symbol identifier

        Returns:
            FeatureSnapshot if feature service configured and context exists, None otherwise

        Rules:
            - Pure getter
            - No side effects
        """
        if not self._feature_service:
            return None

        if not self._feature_service.has_context(symbol):
            return None

        return self._feature_service.build_snapshot(symbol)
