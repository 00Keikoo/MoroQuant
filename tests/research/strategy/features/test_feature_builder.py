"""Tests for FeatureBuilder purity and determinism - Sprint 3.9B-2A"""

import pytest
from datetime import datetime, timedelta
from ml_service.research.strategy.features.builder import DefaultFeatureBuilder
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.simulation.models import MarketSnapshot


class TestFeatureBuilderUpdateIsPure:
    """Test 3: Verify update() is a pure function."""

    def test_feature_builder_update_is_pure(self):
        """Verify old context unchanged after update."""
        builder = DefaultFeatureBuilder(window_size=10)

        original_context = builder.initialize(symbol="BTC-USD")

        snapshot = MarketSnapshot(
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            symbol="BTC-USD",
            mid_price=40000.0
        )

        new_context = builder.update(original_context, snapshot)

        assert len(original_context.window) == 0
        assert len(new_context.window) == 1
        assert original_context is not new_context

    def test_multiple_updates_preserve_originals(self):
        """Verify each update preserves previous contexts."""
        builder = DefaultFeatureBuilder(window_size=10)

        context1 = builder.initialize(symbol="BTC-USD")

        snapshot1 = MarketSnapshot(
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            symbol="BTC-USD",
            mid_price=40000.0
        )
        context2 = builder.update(context1, snapshot1)

        snapshot2 = MarketSnapshot(
            timestamp=datetime(2024, 1, 1, 0, 1, 0),
            symbol="BTC-USD",
            mid_price=40100.0
        )
        context3 = builder.update(context2, snapshot2)

        assert len(context1.window) == 0
        assert len(context2.window) == 1
        assert len(context3.window) == 2


class TestFeatureSnapshotSchemaVersion:
    """Test 5: Verify schema version determinism."""

    def test_feature_snapshot_schema_version(self):
        """Verify schema version is deterministic."""
        builder = DefaultFeatureBuilder()

        context = FeatureContext(
            symbol="BTC-USD",
            timestamp="2024-01-01T00:00:00Z",
            window=tuple()
        )

        snapshot1 = builder.build(context)
        snapshot2 = builder.build(context)

        assert snapshot1.schema_version == "1.0.0"
        assert snapshot2.schema_version == "1.0.0"
        assert snapshot1.schema_version == snapshot2.schema_version


class TestFeatureBuilderDeterministicOutput:
    """Test 6: Verify deterministic output."""

    def test_feature_builder_deterministic_output(self):
        """Verify same inputs produce same outputs."""
        builder1 = DefaultFeatureBuilder(window_size=10)
        builder2 = DefaultFeatureBuilder(window_size=10)

        base_time = datetime(2024, 1, 1, 0, 0, 0)
        snapshots = [
            MarketSnapshot(
                timestamp=base_time + timedelta(minutes=i),
                symbol="BTC-USD",
                mid_price=40000.0 + i * 10
            )
            for i in range(5)
        ]

        context1 = builder1.initialize("BTC-USD")
        context2 = builder2.initialize("BTC-USD")

        for snapshot in snapshots:
            context1 = builder1.update(context1, snapshot)
            context2 = builder2.update(context2, snapshot)

        snapshot1 = builder1.build(context1)
        snapshot2 = builder2.build(context2)

        assert snapshot1.schema_version == snapshot2.schema_version
        assert snapshot1.features == snapshot2.features
        assert len(context1.window) == len(context2.window)
        assert context1.symbol == context2.symbol

    def test_window_size_limit_enforced(self):
        """Verify rolling window maintains size limit."""
        builder = DefaultFeatureBuilder(window_size=3)

        context = builder.initialize("BTC-USD")

        base_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(5):
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(minutes=i),
                symbol="BTC-USD",
                mid_price=40000.0 + i * 10
            )
            context = builder.update(context, snapshot)

        assert len(context.window) == 3

        assert context.window[0].mid_price == 40020.0
        assert context.window[1].mid_price == 40030.0
        assert context.window[2].mid_price == 40040.0
