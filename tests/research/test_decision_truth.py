"""Tests for Decision Truth Layer."""

import pytest
from ml_service.research.decision_truth import DecisionEngine, DecisionContext, DecisionResult


class TestDecisionEngine:
    """Test deterministic decision engine."""

    def test_long_decision_above_threshold(self):
        """Test LONG decision when prob_long > prob_short and above threshold."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig1",
            symbol="BTCUSDT",
            probability_long=0.7,
            probability_short=0.3,
            probability_neutral=0.0
        )
        result = engine.decide(context)

        assert result.action == "LONG"
        assert result.confidence == 0.7
        assert result.threshold_used == 0.5
        assert "LONG_PROBABILITY_EXCEEDS_THRESHOLD" in result.reason_code

    def test_short_decision_above_threshold(self):
        """Test SHORT decision when prob_short > prob_long and above threshold."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig2",
            symbol="ETHUSDT",
            probability_long=0.2,
            probability_short=0.8,
            probability_neutral=0.0
        )
        result = engine.decide(context)

        assert result.action == "SHORT"
        assert result.confidence == 0.8
        assert result.threshold_used == 0.5
        assert "SHORT_PROBABILITY_EXCEEDS_THRESHOLD" in result.reason_code

    def test_hold_decision_below_threshold(self):
        """Test HOLD decision when both probabilities below threshold."""
        engine = DecisionEngine(threshold_long=0.6, threshold_short=0.6)
        context = DecisionContext(
            signal_id="sig3",
            symbol="BTCUSDT",
            probability_long=0.5,
            probability_short=0.4,
            probability_neutral=0.1
        )
        result = engine.decide(context)

        assert result.action == "HOLD"
        assert result.confidence == 0.5
        assert "BOTH_PROBABILITIES_BELOW_THRESHOLD" in result.reason_code

    def test_hold_decision_equal_probabilities(self):
        """Test HOLD decision when probabilities are equal."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig4",
            symbol="BTCUSDT",
            probability_long=0.6,
            probability_short=0.6,
            probability_neutral=0.0
        )
        result = engine.decide(context)

        assert result.action == "HOLD"
        assert "PROBABILITIES_EQUAL" in result.reason_code

    def test_deterministic_behavior(self):
        """Test that same input always produces same output."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig5",
            symbol="BTCUSDT",
            probability_long=0.7,
            probability_short=0.3,
            probability_neutral=0.0
        )

        result1 = engine.decide(context)
        result2 = engine.decide(context)
        result3 = engine.decide(context)

        assert result1.action == result2.action == result3.action
        assert result1.confidence == result2.confidence == result3.confidence
        assert result1.threshold_used == result2.threshold_used == result3.threshold_used
        assert result1.reason_code == result2.reason_code == result3.reason_code

    def test_asymmetric_thresholds_long(self):
        """Test asymmetric thresholds favor LONG."""
        engine = DecisionEngine(threshold_long=0.4, threshold_short=0.7)
        context = DecisionContext(
            signal_id="sig6",
            symbol="BTCUSDT",
            probability_long=0.5,
            probability_short=0.5,
            probability_neutral=0.0
        )
        result = engine.decide(context)

        assert result.action == "HOLD"

    def test_asymmetric_thresholds_short(self):
        """Test asymmetric thresholds with SHORT signal."""
        engine = DecisionEngine(threshold_long=0.7, threshold_short=0.4)
        context = DecisionContext(
            signal_id="sig7",
            symbol="BTCUSDT",
            probability_long=0.3,
            probability_short=0.6,
            probability_neutral=0.1
        )
        result = engine.decide(context)

        assert result.action == "SHORT"
        assert result.confidence == 0.6
        assert result.threshold_used == 0.4

    def test_invalid_threshold_long(self):
        """Test that invalid threshold_long raises ValueError."""
        with pytest.raises(ValueError, match="threshold_long must be between"):
            DecisionEngine(threshold_long=1.5, threshold_short=0.5)

    def test_invalid_threshold_short(self):
        """Test that invalid threshold_short raises ValueError."""
        with pytest.raises(ValueError, match="threshold_short must be between"):
            DecisionEngine(threshold_long=0.5, threshold_short=-0.1)

    def test_edge_case_zero_probabilities(self):
        """Test edge case with zero probabilities."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig8",
            symbol="BTCUSDT",
            probability_long=0.0,
            probability_short=0.0,
            probability_neutral=1.0
        )
        result = engine.decide(context)

        assert result.action == "HOLD"

    def test_edge_case_boundary_threshold(self):
        """Test exact threshold boundary."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig9",
            symbol="BTCUSDT",
            probability_long=0.5,
            probability_short=0.3,
            probability_neutral=0.2
        )
        result = engine.decide(context)

        assert result.action == "HOLD"

    def test_optional_regime_and_features(self):
        """Test that optional fields work correctly."""
        engine = DecisionEngine(threshold_long=0.5, threshold_short=0.5)
        context = DecisionContext(
            signal_id="sig10",
            symbol="BTCUSDT",
            probability_long=0.7,
            probability_short=0.3,
            probability_neutral=0.0,
            regime="TRENDING",
            features={"volatility": 0.02, "volume": 1000}
        )
        result = engine.decide(context)

        assert result.action == "LONG"
        assert context.regime == "TRENDING"
        assert context.features is not None
