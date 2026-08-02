"""
Liquidity Models

Abstract interface and concrete implementations for simulating market liquidity.
All models are pure functions with no side effects.
"""

from abc import ABC, abstractmethod
from ml_service.simulation.models import MarketSnapshot


class ILiquidityModel(ABC):
    """Interface for liquidity calculation"""

    @abstractmethod
    def get_available_volume(self, price: float, snapshot: MarketSnapshot) -> float:
        """Get available volume at given price level"""
        pass


class InfiniteLiquidityModel(ILiquidityModel):
    """Infinite liquidity model - all orders can be filled"""

    def get_available_volume(self, price: float, snapshot: MarketSnapshot) -> float:
        """Return infinite volume (represented as float max)"""
        return float('inf')
