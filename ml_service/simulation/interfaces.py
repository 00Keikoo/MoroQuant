"""
Simulation Domain Interfaces

Abstract interfaces for dependency injection and testability.
All repositories and execution components implement these contracts.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from ml_service.simulation.models import (
    SimulationRun,
    Order,
    Fill,
    Trade,
    Portfolio,
    EquityCurve,
    SimulationReport,
    MarketSnapshot,
)


class ISimulationRunRepository(ABC):
    """Interface for SimulationRun persistence"""

    @abstractmethod
    def create(self, run: SimulationRun) -> SimulationRun:
        """Store a new simulation run"""
        pass

    @abstractmethod
    def get(self, run_id: str) -> Optional[SimulationRun]:
        """Retrieve simulation run by ID"""
        pass

    @abstractmethod
    def update(self, run: SimulationRun) -> SimulationRun:
        """Update existing simulation run"""
        pass

    @abstractmethod
    def list_all(self) -> List[SimulationRun]:
        """List all simulation runs"""
        pass

    @abstractmethod
    def delete(self, run_id: str) -> None:
        """Delete simulation run"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all simulation runs"""
        pass


class IOrderRepository(ABC):
    """Interface for Order persistence"""

    @abstractmethod
    def create(self, order: Order) -> Order:
        """Store a new order"""
        pass

    @abstractmethod
    def get(self, order_id: str) -> Optional[Order]:
        """Retrieve order by ID"""
        pass

    @abstractmethod
    def list_by_run(self, run_id: str) -> List[Order]:
        """List all orders for a simulation run"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all orders"""
        pass


class IFillRepository(ABC):
    """Interface for Fill persistence"""

    @abstractmethod
    def create(self, fill: Fill) -> Fill:
        """Store a new fill"""
        pass

    @abstractmethod
    def get(self, fill_id: str) -> Optional[Fill]:
        """Retrieve fill by ID"""
        pass

    @abstractmethod
    def list_by_order(self, order_id: str) -> List[Fill]:
        """List all fills for an order"""
        pass

    @abstractmethod
    def list_by_run(self, run_id: str) -> List[Fill]:
        """List all fills for a simulation run"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all fills"""
        pass


class ITradeRepository(ABC):
    """Interface for Trade persistence"""

    @abstractmethod
    def create(self, trade: Trade) -> Trade:
        """Store a new trade"""
        pass

    @abstractmethod
    def get(self, trade_id: str) -> Optional[Trade]:
        """Retrieve trade by ID"""
        pass

    @abstractmethod
    def list_by_run(self, run_id: str) -> List[Trade]:
        """List all trades for a simulation run"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all trades"""
        pass


class IPortfolioRepository(ABC):
    """Interface for Portfolio snapshot persistence"""

    @abstractmethod
    def append_snapshot(self, run_id: str, portfolio: Portfolio) -> None:
        """Append portfolio snapshot for a simulation run"""
        pass

    @abstractmethod
    def get_snapshots(self, run_id: str) -> List[Portfolio]:
        """Get all portfolio snapshots for a simulation run"""
        pass

    @abstractmethod
    def get_latest(self, run_id: str) -> Optional[Portfolio]:
        """Get latest portfolio snapshot for a simulation run"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all portfolio snapshots"""
        pass


class IEquityCurveRepository(ABC):
    """Interface for EquityCurve persistence"""

    @abstractmethod
    def save(self, curve: EquityCurve) -> EquityCurve:
        """Save or update equity curve"""
        pass

    @abstractmethod
    def get(self, run_id: str) -> Optional[EquityCurve]:
        """Retrieve equity curve by simulation run ID"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all equity curves"""
        pass


class ISimulationReportRepository(ABC):
    """Interface for SimulationReport persistence"""

    @abstractmethod
    def create(self, report: SimulationReport) -> SimulationReport:
        """Store a new simulation report"""
        pass

    @abstractmethod
    def get(self, report_id: str) -> Optional[SimulationReport]:
        """Retrieve report by ID"""
        pass

    @abstractmethod
    def get_by_run(self, run_id: str) -> Optional[SimulationReport]:
        """Retrieve report by simulation run ID"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all reports"""
        pass


class IExecutionContext(ABC):
    """Interface for execution context state"""

    @abstractmethod
    def get_current_time(self) -> datetime:
        """Get current simulation time"""
        pass

    @abstractmethod
    def get_market_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Get current market snapshot for symbol"""
        pass

    @abstractmethod
    def get_all_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols"""
        pass


class IExecutionResult(ABC):
    """Interface for execution simulation results"""

    @abstractmethod
    def get_filled_quantity(self) -> float:
        """Get total filled quantity"""
        pass

    @abstractmethod
    def get_average_price(self) -> float:
        """Get average execution price"""
        pass

    @abstractmethod
    def get_total_fees(self) -> float:
        """Get total fees paid"""
        pass

    @abstractmethod
    def get_slippage(self) -> float:
        """Get total slippage incurred"""
        pass

    @abstractmethod
    def is_fully_filled(self) -> bool:
        """Check if order was fully filled"""
        pass


class IExecutionSimulator(ABC):
    """Interface for order execution simulation"""

    @abstractmethod
    def simulate_execution(
        self,
        order: Order,
        context: IExecutionContext,
    ) -> IExecutionResult:
        """Simulate order execution in given market context"""
        pass

    @abstractmethod
    def estimate_fill_price(
        self,
        order: Order,
        context: IExecutionContext,
    ) -> float:
        """Estimate likely fill price for order"""
        pass

    @abstractmethod
    def estimate_slippage(
        self,
        order: Order,
        context: IExecutionContext,
    ) -> float:
        """Estimate slippage for order"""
        pass
