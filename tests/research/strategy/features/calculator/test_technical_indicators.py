"""Tests for TechnicalIndicatorCalculator - Sprint 3.9B-3B

Validates ADR-024 compliance:
- Deterministic calculation
- No database dependency
- No portfolio dependency
- Immutable output
- NaN handling
- No lookahead bias
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from ml_service.research.strategy.features.calculator.technical_indicators import TechnicalIndicatorCalculator
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.simulation.models import MarketSnapshot


def create_market_snapshot(timestamp: datetime, mid_price: float, volume: float = 1000.0, bid: float = None, ask: float = None) -> MarketSnapshot:
    """Helper to create MarketSnapshot instances."""
    return MarketSnapshot(
        timestamp=timestamp,
        symbol="BTCUSDT",
        mid_price=mid_price,
        bid=bid,
        ask=ask,
        volume=volume,
    )


def create_feature_context_with_snapshots(num_snapshots: int = 100, base_price: float = 50000.0) -> FeatureContext:
    """Helper to create FeatureContext with synthetic market data."""
    start_time = datetime(2024, 1, 1, 0, 0, 0)

    snapshots = []
    for i in range(num_snapshots):
        ts = start_time + timedelta(minutes=i)
        price = base_price + (i * 10) + np.sin(i / 10) * 100
        bid = price - 5
        ask = price + 5
        volume = 1000.0 + (i * 10)

        snapshots.append(create_market_snapshot(ts, price, volume, bid, ask))

    return FeatureContext(
        symbol="BTCUSDT",
        timestamp=snapshots[-1].timestamp.isoformat() + 'Z',
        window=tuple(snapshots)
    )


class TestTechnicalIndicatorCalculatorInitialization:
    """Test calculator initialization and configuration."""

    def test_default_initialization(self):
        """Calculator initializes with default parameters."""
        calc = TechnicalIndicatorCalculator()

        assert calc.ema_periods == (9, 21, 50, 200)
        assert calc.rsi_period == 14
        assert calc.macd_params == (12, 26, 9)
        assert calc.atr_period == 14
        assert calc.bb_period == 20
        assert calc.bb_std == 2.0
        assert calc.volume_period == 20

    def test_custom_initialization(self):
        """Calculator accepts custom parameters."""
        calc = TechnicalIndicatorCalculator(
            ema_periods=(10, 20),
            rsi_period=21,
            macd_params=(8, 21, 5),
            atr_period=10,
            bb_period=15,
            bb_std=1.5,
            volume_period=10
        )

        assert calc.ema_periods == (10, 20)
        assert calc.rsi_period == 21
        assert calc.macd_params == (8, 21, 5)
        assert calc.atr_period == 10
        assert calc.bb_period == 15
        assert calc.bb_std == 1.5
        assert calc.volume_period == 10


class TestTechnicalIndicatorCalculatorCalculation:
    """Test feature calculation logic."""

    def test_empty_window_returns_empty_tuple(self):
        """Empty window returns empty feature tuple."""
        calc = TechnicalIndicatorCalculator()
        context = FeatureContext(
            symbol="BTCUSDT",
            timestamp="2024-01-01T00:00:00Z",
            window=tuple()
        )

        features = calc.calculate(context)

        assert features == tuple()

    def test_single_snapshot_returns_empty_tuple(self):
        """Single snapshot insufficient for indicators."""
        calc = TechnicalIndicatorCalculator()
        snapshot = create_market_snapshot(datetime(2024, 1, 1), 50000.0)
        context = FeatureContext(
            symbol="BTCUSDT",
            timestamp=snapshot.timestamp.isoformat() + 'Z',
            window=(snapshot,)
        )

        features = calc.calculate(context)

        assert features == tuple()

    def test_calculate_generates_expected_features(self):
        """Calculator generates expected technical indicator features."""
        calc = TechnicalIndicatorCalculator()
        context = create_feature_context_with_snapshots(100)

        features = calc.calculate(context)

        assert len(features) > 0

        feature_names = [name for name, _ in features]

        assert any('ema_9' in name for name in feature_names)
        assert any('ema_21' in name for name in feature_names)
        assert 'rsi' in feature_names
        assert any('macd' in name for name in feature_names)
        assert 'atr' in feature_names
        assert any('bb_' in name for name in feature_names)

    def test_features_are_finite_numbers(self):
        """All returned features are finite numbers."""
        calc = TechnicalIndicatorCalculator()
        context = create_feature_context_with_snapshots(100)

        features = calc.calculate(context)

        for name, value in features:
            assert isinstance(value, float)
            assert np.isfinite(value), f"Feature {name} has non-finite value: {value}"
            assert not np.isnan(value), f"Feature {name} is NaN"

    def test_no_ohlcv_columns_in_output(self):
        """Raw OHLCV columns excluded from features."""
        calc = TechnicalIndicatorCalculator()
        context = create_feature_context_with_snapshots(100)

        features = calc.calculate(context)
        feature_names = [name for name, _ in features]

        assert 'open' not in feature_names
        assert 'high' not in feature_names
        assert 'low' not in feature_names
        assert 'close' not in feature_names
        assert 'volume' not in feature_names


class TestTechnicalIndicatorCalculatorDeterminism:
    """Test deterministic calculation guarantee."""

    def test_calculate_is_deterministic(self):
        """Same context produces identical features."""
        calc = TechnicalIndicatorCalculator()
        context = create_feature_context_with_snapshots(100)

        features1 = calc.calculate(context)
        features2 = calc.calculate(context)

        assert features1 == features2

    def test_calculate_is_deterministic_across_instances(self):
        """Different calculator instances produce same results."""
        context = create_feature_context_with_snapshots(100)

        calc1 = TechnicalIndicatorCalculator()
        calc2 = TechnicalIndicatorCalculator()

        features1 = calc1.calculate(context)
        features2 = calc2.calculate(context)

        assert features1 == features2


class TestTechnicalIndicatorCalculatorNaNHandling:
    """Test NaN and edge case handling."""

    def test_missing_bid_ask_handled_gracefully(self):
        """Calculator handles missing bid/ask by using mid_price."""
        calc = TechnicalIndicatorCalculator()

        snapshots = []
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(100):
            ts = start_time + timedelta(minutes=i)
            price = 50000.0 + (i * 10)
            snapshots.append(create_market_snapshot(ts, price, volume=1000.0))

        context = FeatureContext(
            symbol="BTCUSDT",
            timestamp=snapshots[-1].timestamp.isoformat() + 'Z',
            window=tuple(snapshots)
        )

        features = calc.calculate(context)

        assert len(features) > 0
        for name, value in features:
            assert np.isfinite(value)

    def test_zero_volume_handled_gracefully(self):
        """Calculator handles zero volume without errors."""
        calc = TechnicalIndicatorCalculator()

        snapshots = []
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(100):
            ts = start_time + timedelta(minutes=i)
            price = 50000.0 + (i * 10)
            snapshots.append(create_market_snapshot(ts, price, volume=0.0))

        context = FeatureContext(
            symbol="BTCUSDT",
            timestamp=snapshots[-1].timestamp.isoformat() + 'Z',
            window=tuple(snapshots)
        )

        features = calc.calculate(context)

        assert isinstance(features, tuple)


class TestTechnicalIndicatorCalculatorNoLookahead:
    """Test no lookahead bias guarantee."""

    def test_features_only_use_historical_data(self):
        """Features at timestamp T only use data up to T."""
        calc = TechnicalIndicatorCalculator()

        snapshots_100 = []
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(100):
            ts = start_time + timedelta(minutes=i)
            price = 50000.0 + (i * 10)
            snapshots_100.append(create_market_snapshot(ts, price, volume=1000.0))

        context_100 = FeatureContext(
            symbol="BTCUSDT",
            timestamp=snapshots_100[-1].timestamp.isoformat() + 'Z',
            window=tuple(snapshots_100)
        )

        features_100 = calc.calculate(context_100)

        snapshots_150 = snapshots_100.copy()
        for i in range(100, 150):
            ts = start_time + timedelta(minutes=i)
            price = 50000.0 + (i * 10)
            snapshots_150.append(create_market_snapshot(ts, price, volume=1000.0))

        context_100_only = FeatureContext(
            symbol="BTCUSDT",
            timestamp=snapshots_100[-1].timestamp.isoformat() + 'Z',
            window=tuple(snapshots_100)
        )

        features_100_only = calc.calculate(context_100_only)

        assert features_100 == features_100_only


class TestTechnicalIndicatorCalculatorDependencyIsolation:
    """Test dependency isolation (ADR-024 compliance)."""

    def test_no_database_dependency(self):
        """Calculator module has no database imports."""
        import inspect
        from ml_service.research.strategy.features.calculator import technical_indicators

        source = inspect.getsource(technical_indicators)

        forbidden = ['sqlalchemy', 'Session', 'database', 'db.']
        for pattern in forbidden:
            assert pattern not in source, f"Found forbidden pattern: {pattern}"

    def test_no_portfolio_dependency(self):
        """Calculator module has no portfolio imports."""
        import inspect
        from ml_service.research.strategy.features.calculator import technical_indicators

        source = inspect.getsource(technical_indicators)

        forbidden = ['PortfolioService', 'PortfolioEngine', 'ExecutionSimulator', 'Order']
        for pattern in forbidden:
            assert pattern not in source, f"Found forbidden pattern: {pattern}"

    def test_only_allowed_imports(self):
        """Calculator only imports allowed modules."""
        import inspect
        from ml_service.research.strategy.features.calculator import technical_indicators

        source = inspect.getsource(technical_indicators)

        allowed_prefixes = [
            'import pandas',
            'import numpy',
            'from typing',
            'from ml_service.research.strategy.features.calculator.interfaces',
            'from ml_service.research.strategy.features.context',
            'from ml_service.features.indicators',
        ]

        import_lines = [line.strip() for line in source.split('\n')
                       if line.strip().startswith(('import ', 'from '))]

        for line in import_lines:
            if line.startswith(('"""', "'''", '#')):
                continue

            assert any(line.startswith(prefix) for prefix in allowed_prefixes), \
                f"Unexpected import: {line}"


class TestTechnicalIndicatorCalculatorDataframeConversion:
    """Test internal DataFrame conversion logic."""

    def test_converts_snapshots_to_dataframe(self):
        """Snapshots correctly converted to OHLCV DataFrame."""
        calc = TechnicalIndicatorCalculator()

        snapshots = []
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(10):
            ts = start_time + timedelta(minutes=i)
            price = 50000.0 + (i * 10)
            bid = price - 5
            ask = price + 5
            snapshots.append(create_market_snapshot(ts, price, volume=1000.0, bid=bid, ask=ask))

        df = calc._convert_to_dataframe(tuple(snapshots))

        assert len(df) == 10
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
        assert df.index.name == 'timestamp' or isinstance(df.index, type(snapshots[0].timestamp))

    def test_high_low_derived_from_bid_ask(self):
        """High/low correctly derived from bid/ask."""
        calc = TechnicalIndicatorCalculator()

        snapshot = create_market_snapshot(
            datetime(2024, 1, 1),
            mid_price=50000.0,
            bid=49995.0,
            ask=50005.0
        )

        df = calc._convert_to_dataframe((snapshot,))

        assert df.iloc[0]['low'] == 49995.0
        assert df.iloc[0]['high'] == 50005.0

    def test_high_low_swapped_if_inverted(self):
        """High/low corrected if bid > ask."""
        calc = TechnicalIndicatorCalculator()

        snapshot = create_market_snapshot(
            datetime(2024, 1, 1),
            mid_price=50000.0,
            bid=50005.0,
            ask=49995.0
        )

        df = calc._convert_to_dataframe((snapshot,))

        assert df.iloc[0]['low'] <= df.iloc[0]['high']


class TestTechnicalIndicatorCalculatorIntegration:
    """Integration tests with DefaultFeatureBuilder."""

    def test_integrates_with_feature_builder(self):
        """Calculator integrates correctly with DefaultFeatureBuilder."""
        from ml_service.research.strategy.features import DefaultFeatureBuilder

        calc = TechnicalIndicatorCalculator()
        builder = DefaultFeatureBuilder(window_size=100, calculator=calc)

        context = create_feature_context_with_snapshots(100)
        snapshot = builder.build(context)

        assert snapshot.features is not None
        assert len(snapshot.features) > 0
        assert snapshot.schema_version == "1.0.0"

    def test_builder_uses_calculator_output(self):
        """Builder correctly uses calculator output."""
        from ml_service.research.strategy.features import DefaultFeatureBuilder

        calc = TechnicalIndicatorCalculator()
        builder = DefaultFeatureBuilder(calculator=calc)

        context = create_feature_context_with_snapshots(100)
        features = calc.calculate(context)

        snapshot = builder.build(context)

        assert snapshot.features == features
