"""Feature Calculator Interface Tests - Sprint 3.9B-3A

Tests for FeatureCalculator abstraction following ADR-024.
Validates interface contract, determinism, and dependency isolation.
"""

import pytest
from abc import ABC
from datetime import datetime, timezone
from ml_service.research.strategy.features.calculator import FeatureCalculator, NoOpFeatureCalculator
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.research.strategy.features.builder import DefaultFeatureBuilder
from ml_service.simulation.models import MarketSnapshot


def test_feature_calculator_interface_contract():
    """FeatureCalculator must be abstract base class with calculate method."""
    assert issubclass(FeatureCalculator, ABC)
    assert hasattr(FeatureCalculator, 'calculate')
    assert callable(getattr(FeatureCalculator, 'calculate'))

    with pytest.raises(TypeError):
        FeatureCalculator()


def test_noop_calculator_returns_empty_features():
    """NoOpFeatureCalculator returns empty tuple regardless of context."""
    calculator = NoOpFeatureCalculator()

    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:00:00Z",
        window=tuple()
    )

    result = calculator.calculate(context)

    assert result == tuple()
    assert isinstance(result, tuple)
    assert len(result) == 0


def test_noop_calculator_with_populated_window():
    """NoOpFeatureCalculator ignores window data and returns empty tuple."""
    calculator = NoOpFeatureCalculator()

    ts = datetime(2024, 1, 15, 10, 0, 0)
    snapshots = tuple([
        MarketSnapshot(
            symbol="AAPL",
            timestamp=ts,
            mid_price=150.5
        )
    ])

    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:00:00Z",
        window=snapshots
    )

    result = calculator.calculate(context)

    assert result == tuple()


def test_builder_uses_injected_calculator():
    """DefaultFeatureBuilder delegates calculation to injected calculator."""

    class MockCalculator(FeatureCalculator):
        def calculate(self, context: FeatureContext):
            return (("test_feature", 42.0),)

    calculator = MockCalculator()
    builder = DefaultFeatureBuilder(calculator=calculator)

    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:00:00Z",
        window=tuple()
    )

    snapshot = builder.build(context)

    assert snapshot.features == (("test_feature", 42.0),)
    assert snapshot.timestamp == context.timestamp


def test_builder_defaults_to_noop_calculator():
    """DefaultFeatureBuilder uses NoOpFeatureCalculator when none provided."""
    builder = DefaultFeatureBuilder()

    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:00:00Z",
        window=tuple()
    )

    snapshot = builder.build(context)

    assert snapshot.features == tuple()


def test_calculator_output_is_deterministic():
    """Calculator produces same output for same input."""

    class DeterministicCalculator(FeatureCalculator):
        def calculate(self, context: FeatureContext):
            if not context.window:
                return tuple()
            last_price = context.window[-1].mid_price
            return (("last_price", last_price),)

    calculator = DeterministicCalculator()

    ts = datetime(2024, 1, 15, 10, 0, 0)
    snapshot = MarketSnapshot(
        symbol="AAPL",
        timestamp=ts,
        mid_price=150.5
    )

    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:00:00Z",
        window=(snapshot,)
    )

    result1 = calculator.calculate(context)
    result2 = calculator.calculate(context)
    result3 = calculator.calculate(context)

    assert result1 == result2 == result3
    assert result1 == (("last_price", 150.5),)


def test_no_database_dependency():
    """Calculator module has no database imports."""
    import ml_service.research.strategy.features.calculator as calc_module
    import inspect

    source = inspect.getsource(calc_module)

    forbidden_imports = [
        'sqlalchemy',
        'database',
        'db_manager',
        'DatabaseManager',
        'Session',
        'engine'
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source, f"Calculator should not import {forbidden}"


def test_no_portfolio_dependency():
    """Calculator module has no portfolio or execution imports."""
    import ml_service.research.strategy.features.calculator.interfaces as calc_interfaces
    import ml_service.research.strategy.features.calculator.noop as calc_noop
    import inspect

    interfaces_source = inspect.getsource(calc_interfaces)
    noop_source = inspect.getsource(calc_noop)

    forbidden_imports = [
        'PortfolioService',
        'portfolio_engine',
        'ExecutionSimulator',
        'execution',
        'order',
        'position'
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in interfaces_source, f"Calculator interfaces should not reference {forbidden}"
        assert forbidden not in noop_source, f"NoOp calculator should not reference {forbidden}"


def test_calculator_returns_correct_type():
    """Calculator must return Tuple[Tuple[str, float], ...]."""

    class TypedCalculator(FeatureCalculator):
        def calculate(self, context: FeatureContext):
            return (
                ("feature_1", 1.0),
                ("feature_2", 2.5),
            )

    calculator = TypedCalculator()
    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:00:00Z",
        window=tuple()
    )

    result = calculator.calculate(context)

    assert isinstance(result, tuple)
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert isinstance(item[0], str)
        assert isinstance(item[1], (int, float))


def test_calculator_with_multiple_snapshots():
    """Calculator receives full window from context."""

    class WindowCountCalculator(FeatureCalculator):
        def calculate(self, context: FeatureContext):
            return (("window_size", float(len(context.window))),)

    calculator = WindowCountCalculator()

    ts1 = datetime(2024, 1, 15, 10, 0, 0)
    ts2 = datetime(2024, 1, 15, 10, 1, 0)
    ts3 = datetime(2024, 1, 15, 10, 2, 0)

    snapshots = (
        MarketSnapshot(symbol="AAPL", timestamp=ts1, mid_price=150.5),
        MarketSnapshot(symbol="AAPL", timestamp=ts2, mid_price=151.5),
        MarketSnapshot(symbol="AAPL", timestamp=ts3, mid_price=152.5),
    )

    context = FeatureContext(
        symbol="AAPL",
        timestamp="2024-01-15T10:02:00Z",
        window=snapshots
    )

    result = calculator.calculate(context)

    assert result == (("window_size", 3.0),)
