"""
Slippage Models

Abstract interface and concrete implementations for simulating execution slippage.
All models are pure functions with no side effects.
"""

from abc import ABC, abstractmethod
from ml_service.simulation.execution.execution_models import ExecutionOrder
from ml_service.simulation.models import MarketSnapshot


class ISlippageModel(ABC):
    """Interface for slippage calculation"""

    @abstractmethod
    def calculate_slippage(
        self, order: ExecutionOrder, snapshot: MarketSnapshot
    ) -> float:
        """Calculate slippage for order execution"""
        pass


class FixedSlippageModel(ISlippageModel):
    """Fixed basis points slippage model"""

    def __init__(self, fixed_bps: float):
        """
        Args:
            fixed_bps: Fixed slippage in basis points (e.g., 5.0 = 0.05%)
        """
        if fixed_bps < 0:
            raise ValueError("fixed_bps must be non-negative")
        self.fixed_bps = fixed_bps

    def calculate_slippage(
        self, order: ExecutionOrder, snapshot: MarketSnapshot
    ) -> float:
        """
        Calculate fixed slippage based on basis points.

        Returns absolute slippage amount in quote currency.
        """
        price = snapshot.mid_price
        slippage_pct = self.fixed_bps / 10000.0
        return price * slippage_pct
