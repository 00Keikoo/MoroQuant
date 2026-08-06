"""
Margin Engine - Calculation of margin requirements and liquidation prices.

Pure functional margin calculations with no side effects.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum

from ml_service.portfolio.models import (
    Position,
    PositionType,
    AccountType,
    PositionMarginContext,
)


class HealthStatus(Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DANGER = "DANGER"
    LIQUIDATION = "LIQUIDATION"


@dataclass(frozen=True)
class MarginUpdated:
    portfolio_id: str
    timestamp: datetime
    margin_ratio: float
    maintenance_margin: float
    health_status: HealthStatus


@dataclass(frozen=True)
class LiquidationTriggered:
    position_id: str
    liquidation_price: float
    timestamp: datetime
    reason: str


class MarginService:
    """Service for calculating margin requirements and liquidation prices."""

    @staticmethod
    def calculate_initial_margin(
        position: Position,
        mark_price: float,
    ) -> float:
        """
        Calculate initial margin required for a position.

        For SPOT: returns 0
        For MARGIN/FUTURES: mark_price × |quantity| × IMR
        """
        if position.position_type == PositionType.SPOT:
            return 0.0

        if position.margin_context is None:
            raise ValueError(
                f"Missing margin_context for {position.position_type} position: {position.symbol}"
            )

        if mark_price <= 0:
            raise ValueError(f"Invalid mark_price: {mark_price}")

        if position.quantity == 0:
            raise ValueError(f"Position quantity cannot be zero: {position.symbol}")

        initial_margin = mark_price * abs(position.quantity) * position.margin_context.initial_margin_ratio
        return initial_margin

    @staticmethod
    def calculate_maintenance_margin(
        position: Position,
        mark_price: float,
    ) -> float:
        """
        Calculate maintenance margin required for a position.

        For SPOT: returns 0
        For MARGIN/FUTURES: mark_price × |quantity| × MMR
        """
        if position.position_type == PositionType.SPOT:
            return 0.0

        if position.margin_context is None:
            raise ValueError(
                f"Missing margin_context for {position.position_type} position: {position.symbol}"
            )

        if mark_price <= 0:
            raise ValueError(f"Invalid mark_price: {mark_price}")

        if position.quantity == 0:
            raise ValueError(f"Position quantity cannot be zero: {position.symbol}")

        maintenance_margin = mark_price * abs(position.quantity) * position.margin_context.maintenance_margin_ratio
        return maintenance_margin

    @staticmethod
    def calculate_margin_ratio(
        equity: float,
        maintenance_margin: float,
    ) -> Optional[float]:
        """
        Calculate margin ratio.

        Margin Ratio = Maintenance Margin / Equity

        Returns None for SPOT accounts or when maintenance_margin is 0.
        Liquidation trigger: Margin Ratio >= 1.0
        """
        if maintenance_margin == 0:
            return None

        if equity < 0:
            raise ValueError(f"Equity cannot be negative: {equity}")

        if equity == 0:
            return float('inf')

        return maintenance_margin / equity

    @staticmethod
    def calculate_long_liquidation_price(
        position: Position,
    ) -> Optional[float]:
        """
        Calculate liquidation price for a long position (cross margin).

        LP = Entry Price × (1 - IMR) / (1 - MMR)

        Returns None for SPOT positions.
        """
        if position.position_type == PositionType.SPOT:
            return None

        if position.margin_context is None:
            raise ValueError(
                f"Missing margin_context for {position.position_type} position: {position.symbol}"
            )

        if position.quantity <= 0:
            raise ValueError(
                f"Long liquidation price requires positive quantity, got: {position.quantity}"
            )

        imr = position.margin_context.initial_margin_ratio
        mmr = position.margin_context.maintenance_margin_ratio

        if mmr >= imr:
            raise ValueError(
                f"MMR ({mmr}) must be less than IMR ({imr})"
            )

        denominator = 1.0 - mmr
        if denominator <= 0:
            raise ValueError(f"Invalid MMR leads to non-positive denominator: {mmr}")

        liquidation_price = position.average_entry_price * (1.0 - imr) / denominator
        return liquidation_price

    @staticmethod
    def calculate_short_liquidation_price(
        position: Position,
    ) -> Optional[float]:
        """
        Calculate liquidation price for a short position (cross margin).

        LP = Entry Price × (1 + IMR) / (1 + MMR)

        Returns None for SPOT positions.
        """
        if position.position_type == PositionType.SPOT:
            return None

        if position.margin_context is None:
            raise ValueError(
                f"Missing margin_context for {position.position_type} position: {position.symbol}"
            )

        if position.quantity >= 0:
            raise ValueError(
                f"Short liquidation price requires negative quantity, got: {position.quantity}"
            )

        imr = position.margin_context.initial_margin_ratio
        mmr = position.margin_context.maintenance_margin_ratio

        if mmr >= imr:
            raise ValueError(
                f"MMR ({mmr}) must be less than IMR ({imr})"
            )

        denominator = 1.0 + mmr
        liquidation_price = position.average_entry_price * (1.0 + imr) / denominator
        return liquidation_price

    @staticmethod
    def calculate_isolated_liquidation_price(
        position: Position,
    ) -> Optional[float]:
        """
        Calculate liquidation price for isolated margin position.

        LONG: LP = (Entry Price - Allocated Margin / Quantity) / (1 - MMR)
        SHORT: LP = (Entry Price + Allocated Margin / |Quantity|) / (1 + MMR)

        Returns None for SPOT positions.
        """
        if position.position_type == PositionType.SPOT:
            return None

        if position.margin_context is None:
            raise ValueError(
                f"Missing margin_context for {position.position_type} position: {position.symbol}"
            )

        if position.quantity == 0:
            raise ValueError(f"Position quantity cannot be zero: {position.symbol}")

        mmr = position.margin_context.maintenance_margin_ratio
        allocated_margin = position.margin_context.allocated_margin

        if position.quantity > 0:
            numerator = position.average_entry_price - (allocated_margin / position.quantity)
            denominator = 1.0 - mmr
            if denominator <= 0:
                raise ValueError(f"Invalid MMR leads to non-positive denominator: {mmr}")
            liquidation_price = numerator / denominator
        else:
            numerator = position.average_entry_price + (allocated_margin / abs(position.quantity))
            denominator = 1.0 + mmr
            liquidation_price = numerator / denominator

        return liquidation_price

    @staticmethod
    def evaluate_margin_health(
        equity: float,
        positions: List[Position],
        mark_prices: Dict[str, float],
    ) -> HealthStatus:
        """
        Evaluate overall margin health based on margin ratio.

        HEALTHY: margin_ratio < 0.5
        WARNING: 0.5 <= margin_ratio < 0.8
        DANGER: 0.8 <= margin_ratio < 1.0
        LIQUIDATION: margin_ratio >= 1.0
        """
        if equity < 0:
            raise ValueError(f"Equity cannot be negative: {equity}")

        total_maintenance_margin = 0.0

        for position in positions:
            if position.position_type == PositionType.SPOT:
                continue

            if position.symbol not in mark_prices:
                raise ValueError(f"Missing mark_price for position: {position.symbol}")

            mark_price = mark_prices[position.symbol]
            mm = MarginService.calculate_maintenance_margin(position, mark_price)
            total_maintenance_margin += mm

        if total_maintenance_margin == 0:
            return HealthStatus.HEALTHY

        if equity == 0:
            return HealthStatus.LIQUIDATION

        margin_ratio = total_maintenance_margin / equity

        if margin_ratio >= 1.0:
            return HealthStatus.LIQUIDATION
        elif margin_ratio >= 0.8:
            return HealthStatus.DANGER
        elif margin_ratio >= 0.5:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
