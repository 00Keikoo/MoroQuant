"""Tests for FeatureContext immutability and ordering - Sprint 3.9B-2A"""

import pytest
from datetime import datetime, timedelta
from dataclasses import FrozenInstanceError
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.simulation.models import MarketSnapshot


class TestFeatureContextImmutable:
    """Test 1: Verify FeatureContext immutability."""

    def test_feature_context_immutable(self):
        """Verify mutation is rejected."""
        context = FeatureContext(
            symbol="BTC-USD",
            timestamp="2024-01-01T00:00:00Z",
            window=tuple()
        )

        with pytest.raises(FrozenInstanceError):
            context.symbol = "ETH-USD"

        with pytest.raises(FrozenInstanceError):
            context.timestamp = "2024-01-02T00:00:00Z"

        with pytest.raises(FrozenInstanceError):
            context.window = tuple()


class TestFeatureContextTimestampOrdering:
    """Test 2: Verify chronological timestamp ordering."""

    def test_feature_context_timestamp_ordering(self):
        """Verify window maintains chronological order."""
        base_time = datetime(2024, 1, 1, 0, 0, 0)

        snapshot1 = MarketSnapshot(
            timestamp=base_time,
            symbol="BTC-USD",
            mid_price=40000.0
        )

        snapshot2 = MarketSnapshot(
            timestamp=base_time + timedelta(minutes=1),
            symbol="BTC-USD",
            mid_price=40100.0
        )

        context = FeatureContext(
            symbol="BTC-USD",
            timestamp="2024-01-01T00:02:00Z",
            window=(snapshot1, snapshot2)
        )

        assert context.window[0].timestamp < context.window[1].timestamp

    def test_reject_reversed_ordering(self):
        """Verify reversed chronological order is rejected."""
        base_time = datetime(2024, 1, 1, 0, 0, 0)

        snapshot1 = MarketSnapshot(
            timestamp=base_time + timedelta(minutes=1),
            symbol="BTC-USD",
            mid_price=40100.0
        )

        snapshot2 = MarketSnapshot(
            timestamp=base_time,
            symbol="BTC-USD",
            mid_price=40000.0
        )

        with pytest.raises(ValueError, match="not chronologically ordered"):
            FeatureContext(
                symbol="BTC-USD",
                timestamp="2024-01-01T00:02:00Z",
                window=(snapshot1, snapshot2)
            )


class TestFeatureContextNoFutureData:
    """Test 4: Verify no future data allowed."""

    def test_feature_builder_no_future_data(self):
        """Verify future timestamp is rejected."""
        context_time = datetime(2024, 1, 1, 0, 0, 0)
        future_time = context_time + timedelta(minutes=5)

        future_snapshot = MarketSnapshot(
            timestamp=future_time,
            symbol="BTC-USD",
            mid_price=40000.0
        )

        with pytest.raises(ValueError, match="Future data detected"):
            FeatureContext(
                symbol="BTC-USD",
                timestamp="2024-01-01T00:00:00Z",
                window=(future_snapshot,)
            )

    def test_accept_past_data(self):
        """Verify past data is accepted."""
        context_time = datetime(2024, 1, 1, 0, 5, 0)
        past_time = context_time - timedelta(minutes=5)

        past_snapshot = MarketSnapshot(
            timestamp=past_time,
            symbol="BTC-USD",
            mid_price=40000.0
        )

        context = FeatureContext(
            symbol="BTC-USD",
            timestamp="2024-01-01T00:05:00Z",
            window=(past_snapshot,)
        )

        assert len(context.window) == 1
        assert context.window[0].timestamp <= context_time
