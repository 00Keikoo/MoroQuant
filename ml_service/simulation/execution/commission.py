"""
Commission Models

Abstract interface and concrete implementations for trading commission calculation.
All models are pure functions with no side effects.
"""

from abc import ABC, abstractmethod


class ICommissionModel(ABC):
    """Interface for commission calculation"""

    @abstractmethod
    def calculate_commission(
        self, quantity: float, price: float, is_maker: bool
    ) -> float:
        """Calculate commission for trade execution"""
        pass


class BinanceSpotCommission(ICommissionModel):
    """Binance Spot trading commission model"""

    def __init__(self, fee_pct: float = 0.1):
        """
        Args:
            fee_pct: Commission fee percentage (default 0.1% for standard Binance Spot)
        """
        if fee_pct < 0:
            raise ValueError("fee_pct must be non-negative")
        self.fee_pct = fee_pct

    def calculate_commission(
        self, quantity: float, price: float, is_maker: bool
    ) -> float:
        """
        Calculate Binance Spot commission.

        Returns absolute commission in quote currency.
        """
        notional_value = quantity * price
        return notional_value * (self.fee_pct / 100.0)


class BinanceFuturesCommission(ICommissionModel):
    """Binance Futures trading commission model with maker/taker distinction"""

    def __init__(self, maker_fee_pct: float = 0.02, taker_fee_pct: float = 0.04):
        """
        Args:
            maker_fee_pct: Maker fee percentage (default 0.02% for Binance Futures)
            taker_fee_pct: Taker fee percentage (default 0.04% for Binance Futures)
        """
        if maker_fee_pct < 0 or taker_fee_pct < 0:
            raise ValueError("fee percentages must be non-negative")
        self.maker_fee_pct = maker_fee_pct
        self.taker_fee_pct = taker_fee_pct

    def calculate_commission(
        self, quantity: float, price: float, is_maker: bool
    ) -> float:
        """
        Calculate Binance Futures commission based on maker/taker role.

        Returns absolute commission in quote currency.
        """
        notional_value = quantity * price
        fee_pct = self.maker_fee_pct if is_maker else self.taker_fee_pct
        return notional_value * (fee_pct / 100.0)
