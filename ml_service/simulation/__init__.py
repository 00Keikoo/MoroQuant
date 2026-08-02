"""
Simulation Domain Package

Immutable, pure functional domain models and services for backtesting and simulation.
"""

from ml_service.simulation.models import (
    OrderSide,
    OrderType,
    OrderStatus,
    SimulationStatus,
    MarketSnapshot,
    ExecutionAssumption,
    SimulationConfig,
    Order,
    Fill,
    Position,
    Portfolio,
    Trade,
    EquityCurve,
    PerformanceMetrics,
    SimulationReport,
    SimulationRun,
)

from ml_service.simulation.repository import (
    SimulationRunRepository,
    OrderRepository,
    FillRepository,
    TradeRepository,
    PortfolioRepository,
    EquityCurveRepository,
    SimulationReportRepository,
)

from ml_service.simulation.service import (
    ValidationService,
    LifecycleService,
    PortfolioService,
    EquityCurveService,
    PerformanceService,
)

from ml_service.simulation.orchestrator import SimulationOrchestrator

__all__ = [
    # Enums
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "SimulationStatus",
    # Models
    "MarketSnapshot",
    "ExecutionAssumption",
    "SimulationConfig",
    "Order",
    "Fill",
    "Position",
    "Portfolio",
    "Trade",
    "EquityCurve",
    "PerformanceMetrics",
    "SimulationReport",
    "SimulationRun",
    # Repositories
    "SimulationRunRepository",
    "OrderRepository",
    "FillRepository",
    "TradeRepository",
    "PortfolioRepository",
    "EquityCurveRepository",
    "SimulationReportRepository",
    # Services
    "ValidationService",
    "LifecycleService",
    "PortfolioService",
    "EquityCurveService",
    "PerformanceService",
    # Orchestrator
    "SimulationOrchestrator",
]
