"""Feature Integration Tests - Sprint 3.9B-2B

Tests for feature context integration into strategy runtime.
Validates the complete flow: MarketSnapshot -> FeatureBuilder -> FeatureSnapshot.
"""

import pytest
from datetime import datetime, timezone
from dataclasses import dataclass

from ml_service.research.strategy.features import (
    FeatureContextService,
    DefaultFeatureBuilder,
)
from ml_service.simulation.models import MarketSnapshot


@dataclass(frozen=True)
class MarketSnapshot:
    """Test market snapshot."""
    timestamp: datetime
    symbol: str
    mid_price: float
    bid: float = None
    ask: float = None


def test_market_snapshot_updates_feature_context():
    """Verify MarketSnapshot enters FeatureBuilder and updates context."""
    builder = DefaultFeatureBuilder(window_size=10)
    service = FeatureContextService(builder)

    symbol = "BTCUSDT"
    service.initialize_context(symbol)

    snapshot1 = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        symbol=symbol,
        mid_price=50000.0,
        bid=49999.0,
        ask=50001.0,
    )

    context = service.update_context(symbol, snapshot1)

    assert len(context.window) == 1
    assert context.window[0].symbol == symbol
    assert context.window[0].mid_price == 50000.0
    assert context.symbol == symbol


def test_feature_snapshot_generated_from_context():
    """Verify FeatureSnapshot is built from updated context."""
    builder = DefaultFeatureBuilder(window_size=10)
    service = FeatureContextService(builder)

    symbol = "ETHUSDT"
    service.initialize_context(symbol)

    snapshot1 = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        symbol=symbol,
        mid_price=3000.0,
    )

    service.update_context(symbol, snapshot1)
    feature_snapshot = service.build_snapshot(symbol)

    assert feature_snapshot is not None
    assert feature_snapshot.schema_version == "1.0.0"
    assert feature_snapshot.timestamp.startswith("2024-01-01")


def test_multiple_market_steps_are_deterministic():
    """Verify same snapshots produce same FeatureSnapshot (determinism)."""
    builder1 = DefaultFeatureBuilder(window_size=10)
    service1 = FeatureContextService(builder1)

    builder2 = DefaultFeatureBuilder(window_size=10)
    service2 = FeatureContextService(builder2)

    symbol = "BTCUSDT"

    snapshots = [
        MarketSnapshot(
            timestamp=datetime(2024, 1, 1, i, 0, 0, tzinfo=timezone.utc),
            symbol=symbol,
            mid_price=50000.0 + i * 100,
        )
        for i in range(5)
    ]

    service1.initialize_context(symbol)
    service2.initialize_context(symbol)

    for snapshot in snapshots:
        service1.update_context(symbol, snapshot)
        service2.update_context(symbol, snapshot)

    result1 = service1.build_snapshot(symbol)
    result2 = service2.build_snapshot(symbol)

    assert result1.timestamp == result2.timestamp
    assert result1.schema_version == result2.schema_version
    assert result1.features == result2.features


def test_no_future_data_leakage_during_updates():
    """Verify updates enforce chronological ordering and reject future data."""
    builder = DefaultFeatureBuilder(window_size=10)
    service = FeatureContextService(builder)

    symbol = "BTCUSDT"
    service.initialize_context(symbol)

    snapshot1 = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        symbol=symbol,
        mid_price=50000.0,
    )

    snapshot2 = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        symbol=symbol,
        mid_price=51000.0,
    )

    service.update_context(symbol, snapshot1)

    with pytest.raises(ValueError, match="before last window timestamp"):
        service.update_context(symbol, snapshot2)


def test_strategy_receives_feature_snapshot():
    """Verify strategy can access FeatureSnapshot after context update."""
    builder = DefaultFeatureBuilder(window_size=10)
    service = FeatureContextService(builder)

    symbol = "BTCUSDT"
    service.initialize_context(symbol)

    snapshot = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        symbol=symbol,
        mid_price=50000.0,
    )

    service.update_context(symbol, snapshot)
    feature_snapshot = service.build_snapshot(symbol)

    assert feature_snapshot is not None
    assert hasattr(feature_snapshot, 'timestamp')
    assert hasattr(feature_snapshot, 'features')
    assert hasattr(feature_snapshot, 'schema_version')


def test_original_context_not_mutated():
    """Verify context updates create new objects, don't mutate originals."""
    builder = DefaultFeatureBuilder(window_size=10)
    service = FeatureContextService(builder)

    symbol = "BTCUSDT"
    context1 = service.initialize_context(symbol)

    assert len(context1.window) == 0

    snapshot = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        symbol=symbol,
        mid_price=50000.0,
    )

    context2 = service.update_context(symbol, snapshot)

    assert len(context1.window) == 0
    assert len(context2.window) == 1

    assert context1 is not context2
