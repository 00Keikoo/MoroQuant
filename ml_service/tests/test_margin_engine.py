"""
Tests for Margin Engine - margin calculations and liquidation prices.
"""

import pytest
from datetime import datetime
from dataclasses import replace

from ml_service.portfolio.margin import (
    MarginService,
    HealthStatus,
    MarginUpdated,
    LiquidationTriggered,
)
from ml_service.portfolio.models import (
    Position,
    PositionType,
    PositionLifecycle,
    PositionMarginContext,
)


@pytest.fixture
def spot_position():
    """Spot position with no margin context."""
    return Position(
        symbol="BTCUSDT",
        position_type=PositionType.SPOT,
        status=PositionLifecycle.OPEN,
        quantity=1.0,
        average_entry_price=50000.0,
        average_exit_price=0.0,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        margin_required=0.0,
        margin_context=None,
        opened_at=datetime(2026, 8, 1, 10, 0, 0),
        updated_at=datetime(2026, 8, 1, 10, 0, 0),
    )


@pytest.fixture
def futures_long_position():
    """Futures long position with 10x leverage."""
    margin_context = PositionMarginContext(
        leverage=10.0,
        initial_margin_ratio=0.10,
        maintenance_margin_ratio=0.05,
        allocated_margin=1000.0,
    )
    return Position(
        symbol="BTCUSDT",
        position_type=PositionType.FUTURES,
        status=PositionLifecycle.OPEN,
        quantity=1.0,
        average_entry_price=10000.0,
        average_exit_price=0.0,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        margin_required=1000.0,
        margin_context=margin_context,
        opened_at=datetime(2026, 8, 1, 10, 0, 0),
        updated_at=datetime(2026, 8, 1, 10, 0, 0),
    )


@pytest.fixture
def futures_short_position():
    """Futures short position with 10x leverage."""
    margin_context = PositionMarginContext(
        leverage=10.0,
        initial_margin_ratio=0.10,
        maintenance_margin_ratio=0.05,
        allocated_margin=1000.0,
    )
    return Position(
        symbol="BTCUSDT",
        position_type=PositionType.FUTURES,
        status=PositionLifecycle.OPEN,
        quantity=-1.0,
        average_entry_price=10000.0,
        average_exit_price=0.0,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        margin_required=1000.0,
        margin_context=margin_context,
        opened_at=datetime(2026, 8, 1, 10, 0, 0),
        updated_at=datetime(2026, 8, 1, 10, 0, 0),
    )


class TestSpotAccountBypass:
    """Test 1: Spot account bypass."""

    def test_spot_initial_margin_is_zero(self, spot_position):
        margin = MarginService.calculate_initial_margin(spot_position, mark_price=55000.0)
        assert margin == 0.0

    def test_spot_maintenance_margin_is_zero(self, spot_position):
        margin = MarginService.calculate_maintenance_margin(spot_position, mark_price=55000.0)
        assert margin == 0.0

    def test_spot_liquidation_price_is_none(self, spot_position):
        lp = MarginService.calculate_long_liquidation_price(spot_position)
        assert lp is None

        lp = MarginService.calculate_short_liquidation_price(spot_position)
        assert lp is None

        lp = MarginService.calculate_isolated_liquidation_price(spot_position)
        assert lp is None


class TestFuturesLongInitialMargin:
    """Test 2: Futures long initial margin."""

    def test_initial_margin_calculation(self, futures_long_position):
        mark_price = 10000.0
        im = MarginService.calculate_initial_margin(futures_long_position, mark_price)
        expected = mark_price * 1.0 * 0.10
        assert abs(im - expected) < 1e-8
        assert abs(im - 1000.0) < 1e-8

    def test_initial_margin_with_price_change(self, futures_long_position):
        mark_price = 12000.0
        im = MarginService.calculate_initial_margin(futures_long_position, mark_price)
        expected = mark_price * 1.0 * 0.10
        assert abs(im - expected) < 1e-8
        assert abs(im - 1200.0) < 1e-8


class TestFuturesShortInitialMargin:
    """Test 3: Futures short initial margin."""

    def test_initial_margin_calculation(self, futures_short_position):
        mark_price = 10000.0
        im = MarginService.calculate_initial_margin(futures_short_position, mark_price)
        expected = mark_price * abs(-1.0) * 0.10
        assert abs(im - expected) < 1e-8
        assert abs(im - 1000.0) < 1e-8

    def test_initial_margin_with_price_change(self, futures_short_position):
        mark_price = 8000.0
        im = MarginService.calculate_initial_margin(futures_short_position, mark_price)
        expected = mark_price * 1.0 * 0.10
        assert abs(im - expected) < 1e-8
        assert abs(im - 800.0) < 1e-8


class TestMaintenanceMarginMarkPrice:
    """Test 4: Maintenance margin mark-price calculation."""

    def test_mm_changes_with_mark_price(self, futures_long_position):
        mm_at_10k = MarginService.calculate_maintenance_margin(futures_long_position, mark_price=10000.0)
        assert abs(mm_at_10k - 500.0) < 1e-8

        mm_at_11k = MarginService.calculate_maintenance_margin(futures_long_position, mark_price=11000.0)
        assert abs(mm_at_11k - 550.0) < 1e-8

        mm_at_9k = MarginService.calculate_maintenance_margin(futures_long_position, mark_price=9000.0)
        assert abs(mm_at_9k - 450.0) < 1e-8

    def test_mm_formula_accuracy(self, futures_short_position):
        mark_price = 10476.19
        mm = MarginService.calculate_maintenance_margin(futures_short_position, mark_price)
        expected = mark_price * 1.0 * 0.05
        assert abs(mm - expected) < 1e-6
        assert abs(mm - 523.8095) < 1e-4


class TestMarginRatioHealthy:
    """Test 5: Margin ratio healthy."""

    def test_margin_ratio_calculation(self):
        equity = 1000.0
        maintenance_margin = 400.0
        margin_ratio = MarginService.calculate_margin_ratio(equity, maintenance_margin)
        assert abs(margin_ratio - 0.4) < 1e-8

    def test_margin_ratio_none_for_zero_mm(self):
        margin_ratio = MarginService.calculate_margin_ratio(equity=1000.0, maintenance_margin=0.0)
        assert margin_ratio is None

    def test_margin_ratio_infinity_for_zero_equity(self):
        margin_ratio = MarginService.calculate_margin_ratio(equity=0.0, maintenance_margin=100.0)
        assert margin_ratio == float('inf')


class TestMarginRatioLiquidationTrigger:
    """Test 6: Margin ratio liquidation trigger."""

    def test_margin_ratio_at_liquidation_threshold(self):
        equity = 473.68
        maintenance_margin = 473.68
        margin_ratio = MarginService.calculate_margin_ratio(equity, maintenance_margin)
        assert abs(margin_ratio - 1.0) < 1e-8

    def test_margin_ratio_exceeds_threshold(self):
        equity = 400.0
        maintenance_margin = 500.0
        margin_ratio = MarginService.calculate_margin_ratio(equity, maintenance_margin)
        assert margin_ratio > 1.0


class TestLongLiquidationPrice:
    """Test 7: Long liquidation price."""

    def test_long_liquidation_price_formula(self, futures_long_position):
        lp = MarginService.calculate_long_liquidation_price(futures_long_position)
        expected = 10000.0 * (1.0 - 0.10) / (1.0 - 0.05)
        assert abs(lp - expected) < 1e-6
        assert abs(lp - 9473.684210526316) < 1e-6

    def test_long_liquidation_verification(self, futures_long_position):
        lp = MarginService.calculate_long_liquidation_price(futures_long_position)
        unrealized_pnl = 1.0 * (lp - 10000.0)
        equity = 1000.0 + unrealized_pnl
        mm = lp * 1.0 * 0.05
        margin_ratio = mm / equity
        assert abs(margin_ratio - 1.0) < 1e-6


class TestShortLiquidationPrice:
    """Test 8: Short liquidation price."""

    def test_short_liquidation_price_formula(self, futures_short_position):
        lp = MarginService.calculate_short_liquidation_price(futures_short_position)
        expected = 10000.0 * (1.0 + 0.10) / (1.0 + 0.05)
        assert abs(lp - expected) < 1e-6
        assert abs(lp - 10476.190476190476) < 1e-6

    def test_short_liquidation_verification(self, futures_short_position):
        lp = MarginService.calculate_short_liquidation_price(futures_short_position)
        unrealized_pnl = -1.0 * (lp - 10000.0)
        equity = 1000.0 + unrealized_pnl
        mm = lp * 1.0 * 0.05
        margin_ratio = mm / equity
        assert abs(margin_ratio - 1.0) < 1e-6


class TestIsolatedMarginLiquidation:
    """Test 9: Isolated margin liquidation."""

    def test_isolated_long_liquidation_price(self, futures_long_position):
        lp = MarginService.calculate_isolated_liquidation_price(futures_long_position)
        expected = (10000.0 - 1000.0 / 1.0) / (1.0 - 0.05)
        assert abs(lp - expected) < 1e-6
        assert abs(lp - 9473.684210526316) < 1e-6

    def test_isolated_short_liquidation_price(self, futures_short_position):
        lp = MarginService.calculate_isolated_liquidation_price(futures_short_position)
        expected = (10000.0 + 1000.0 / 1.0) / (1.0 + 0.05)
        assert abs(lp - expected) < 1e-6
        assert abs(lp - 10476.190476190476) < 1e-6

    def test_isolated_liquidation_with_increased_collateral(self, futures_long_position):
        position_with_more_margin = replace(
            futures_long_position,
            margin_context=replace(
                futures_long_position.margin_context,
                allocated_margin=1500.0
            )
        )
        lp = MarginService.calculate_isolated_liquidation_price(position_with_more_margin)
        expected = (10000.0 - 1500.0 / 1.0) / (1.0 - 0.05)
        assert abs(lp - expected) < 1e-6
        assert abs(lp - 8947.368421052632) < 1e-6


class TestCrossMarginCalculation:
    """Test 10: Cross margin calculation."""

    def test_cross_margin_health_evaluation(self, futures_long_position):
        equity = 1000.0
        mark_prices = {"BTCUSDT": 10000.0}
        health = MarginService.evaluate_margin_health(equity, [futures_long_position], mark_prices)
        mm = 10000.0 * 1.0 * 0.05
        assert mm == 500.0
        margin_ratio = mm / equity
        assert margin_ratio == 0.5
        assert health == HealthStatus.WARNING

    def test_cross_margin_multiple_positions(self, futures_long_position, futures_short_position):
        eth_long = replace(
            futures_long_position,
            symbol="ETHUSDT",
            quantity=10.0,
            average_entry_price=2000.0,
        )
        equity = 5000.0
        mark_prices = {"BTCUSDT": 10000.0, "ETHUSDT": 2100.0}
        positions = [futures_long_position, eth_long]

        health = MarginService.evaluate_margin_health(equity, positions, mark_prices)
        btc_mm = 10000.0 * 1.0 * 0.05
        eth_mm = 2100.0 * 10.0 * 0.05
        total_mm = btc_mm + eth_mm
        assert abs(total_mm - 1550.0) < 1e-8
        margin_ratio = total_mm / equity
        assert abs(margin_ratio - 0.31) < 1e-8
        assert health == HealthStatus.HEALTHY


class TestInvalidMarginContext:
    """Test 11: Invalid margin context."""

    def test_missing_margin_context_for_futures(self):
        with pytest.raises(ValueError, match="margin_context required"):
            position = Position(
                symbol="BTCUSDT",
                position_type=PositionType.FUTURES,
                status=PositionLifecycle.OPEN,
                quantity=1.0,
                average_entry_price=10000.0,
                average_exit_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=0.0,
                margin_context=None,
                opened_at=datetime(2026, 8, 1, 10, 0, 0),
                updated_at=datetime(2026, 8, 1, 10, 0, 0),
            )

    def test_zero_quantity_rejection(self, futures_long_position):
        with pytest.raises(ValueError, match="quantity cannot be zero"):
            zero_qty_position = replace(
                futures_long_position,
                quantity=0.0,
                status=PositionLifecycle.OPEN
            )

    def test_invalid_mark_price(self, futures_long_position):
        with pytest.raises(ValueError, match="Invalid mark_price"):
            MarginService.calculate_initial_margin(futures_long_position, mark_price=0.0)

        with pytest.raises(ValueError, match="Invalid mark_price"):
            MarginService.calculate_initial_margin(futures_long_position, mark_price=-100.0)

    def test_negative_equity_rejection(self):
        with pytest.raises(ValueError, match="Equity cannot be negative"):
            MarginService.calculate_margin_ratio(equity=-100.0, maintenance_margin=500.0)

        with pytest.raises(ValueError, match="Equity cannot be negative"):
            MarginService.evaluate_margin_health(equity=-100.0, positions=[], mark_prices={})


class TestMMRValidation:
    """Test 12: MMR validation."""

    def test_mmr_must_be_less_than_imr(self):
        with pytest.raises(ValueError, match="maintenance_margin_ratio.*must be less than initial_margin_ratio"):
            margin_context = PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.10,
                maintenance_margin_ratio=0.10,
                allocated_margin=1000.0,
            )

    def test_mmr_greater_than_imr(self):
        with pytest.raises(ValueError, match="maintenance_margin_ratio.*must be less than initial_margin_ratio"):
            margin_context = PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.05,
                maintenance_margin_ratio=0.10,
                allocated_margin=1000.0,
            )


class TestEventImmutability:
    """Test 13: Event immutability."""

    def test_margin_updated_event_immutability(self):
        event = MarginUpdated(
            portfolio_id="portfolio-1",
            timestamp=datetime(2026, 8, 1, 10, 0, 0),
            margin_ratio=0.5,
            maintenance_margin=500.0,
            health_status=HealthStatus.WARNING,
        )

        with pytest.raises(Exception):
            event.margin_ratio = 0.6

        with pytest.raises(Exception):
            event.health_status = HealthStatus.HEALTHY

    def test_liquidation_triggered_event_immutability(self):
        event = LiquidationTriggered(
            position_id="pos-1",
            liquidation_price=9473.68,
            timestamp=datetime(2026, 8, 1, 10, 0, 0),
            reason="Margin ratio exceeded 1.0",
        )

        with pytest.raises(Exception):
            event.liquidation_price = 9500.0

        with pytest.raises(Exception):
            event.reason = "Different reason"


class TestHealthStatusEvaluation:
    """Additional tests for health status evaluation."""

    def test_healthy_status(self, futures_long_position):
        equity = 2000.0
        mark_prices = {"BTCUSDT": 10000.0}
        health = MarginService.evaluate_margin_health(equity, [futures_long_position], mark_prices)
        mm = 10000.0 * 1.0 * 0.05
        margin_ratio = mm / equity
        assert margin_ratio == 0.25
        assert health == HealthStatus.HEALTHY

    def test_warning_status(self, futures_long_position):
        equity = 833.33
        mark_prices = {"BTCUSDT": 10000.0}
        health = MarginService.evaluate_margin_health(equity, [futures_long_position], mark_prices)
        mm = 10000.0 * 1.0 * 0.05
        margin_ratio = mm / equity
        assert 0.5 <= margin_ratio < 0.8
        assert health == HealthStatus.WARNING

    def test_danger_status(self, futures_long_position):
        equity = 600.0
        mark_prices = {"BTCUSDT": 10000.0}
        health = MarginService.evaluate_margin_health(equity, [futures_long_position], mark_prices)
        mm = 10000.0 * 1.0 * 0.05
        margin_ratio = mm / equity
        assert 0.8 <= margin_ratio < 1.0
        assert health == HealthStatus.DANGER

    def test_liquidation_status(self, futures_long_position):
        equity = 500.0
        mark_prices = {"BTCUSDT": 10000.0}
        health = MarginService.evaluate_margin_health(equity, [futures_long_position], mark_prices)
        mm = 10000.0 * 1.0 * 0.05
        margin_ratio = mm / equity
        assert margin_ratio >= 1.0
        assert health == HealthStatus.LIQUIDATION

    def test_zero_equity_triggers_liquidation(self, futures_long_position):
        equity = 0.0
        mark_prices = {"BTCUSDT": 10000.0}
        health = MarginService.evaluate_margin_health(equity, [futures_long_position], mark_prices)
        assert health == HealthStatus.LIQUIDATION

    def test_only_spot_positions_healthy(self, spot_position):
        equity = 1000.0
        mark_prices = {"BTCUSDT": 50000.0}
        health = MarginService.evaluate_margin_health(equity, [spot_position], mark_prices)
        assert health == HealthStatus.HEALTHY
