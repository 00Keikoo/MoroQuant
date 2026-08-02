"""
Simulation Repository Layer

In-memory repositories for simulation domain entities.
NO SQLite, NO filesystem writes, NO API - pure in-memory storage only.
"""

from typing import Dict, List, Optional
from datetime import datetime
import threading

from ml_service.simulation.models import (
    SimulationRun,
    Order,
    Fill,
    Trade,
    Portfolio,
    EquityCurve,
    SimulationReport,
)
from ml_service.simulation.interfaces import (
    ISimulationRunRepository,
    IOrderRepository,
    IFillRepository,
    ITradeRepository,
    IPortfolioRepository,
    IEquityCurveRepository,
    ISimulationReportRepository,
)


class SimulationRunRepository(ISimulationRunRepository):
    """In-memory repository for SimulationRun entities"""

    def __init__(self) -> None:
        self._store: Dict[str, SimulationRun] = {}
        self._lock = threading.Lock()

    def create(self, run: SimulationRun) -> SimulationRun:
        """Store a new simulation run"""
        with self._lock:
            if run.run_id in self._store:
                raise ValueError(f"SimulationRun {run.run_id} already exists")
            self._store[run.run_id] = run
            return run

    def get(self, run_id: str) -> Optional[SimulationRun]:
        """Retrieve simulation run by ID"""
        with self._lock:
            return self._store.get(run_id)

    def update(self, run: SimulationRun) -> SimulationRun:
        """Update existing simulation run"""
        with self._lock:
            if run.run_id not in self._store:
                raise ValueError(f"SimulationRun {run.run_id} not found")
            self._store[run.run_id] = run
            return run

    def list_all(self) -> List[SimulationRun]:
        """List all simulation runs"""
        with self._lock:
            return list(self._store.values())

    def delete(self, run_id: str) -> None:
        """Delete simulation run"""
        with self._lock:
            if run_id in self._store:
                del self._store[run_id]

    def clear(self) -> None:
        """Clear all simulation runs"""
        with self._lock:
            self._store.clear()


class OrderRepository(IOrderRepository):
    """In-memory repository for Order entities"""

    def __init__(self) -> None:
        self._store: Dict[str, Order] = {}
        self._by_run: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def create(self, order: Order) -> Order:
        """Store a new order"""
        with self._lock:
            if order.order_id in self._store:
                raise ValueError(f"Order {order.order_id} already exists")
            self._store[order.order_id] = order
            if order.simulation_run_id not in self._by_run:
                self._by_run[order.simulation_run_id] = []
            self._by_run[order.simulation_run_id].append(order.order_id)
            return order

    def get(self, order_id: str) -> Optional[Order]:
        """Retrieve order by ID"""
        with self._lock:
            return self._store.get(order_id)

    def list_by_run(self, run_id: str) -> List[Order]:
        """List all orders for a simulation run"""
        with self._lock:
            order_ids = self._by_run.get(run_id, [])
            return [self._store[oid] for oid in order_ids if oid in self._store]

    def clear(self) -> None:
        """Clear all orders"""
        with self._lock:
            self._store.clear()
            self._by_run.clear()


class FillRepository(IFillRepository):
    """In-memory repository for Fill entities"""

    def __init__(self) -> None:
        self._store: Dict[str, Fill] = {}
        self._by_order: Dict[str, List[str]] = {}
        self._by_run: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def create(self, fill: Fill) -> Fill:
        """Store a new fill"""
        with self._lock:
            if fill.fill_id in self._store:
                raise ValueError(f"Fill {fill.fill_id} already exists")
            self._store[fill.fill_id] = fill
            if fill.order_id not in self._by_order:
                self._by_order[fill.order_id] = []
            self._by_order[fill.order_id].append(fill.fill_id)
            if fill.simulation_run_id not in self._by_run:
                self._by_run[fill.simulation_run_id] = []
            self._by_run[fill.simulation_run_id].append(fill.fill_id)
            return fill

    def get(self, fill_id: str) -> Optional[Fill]:
        """Retrieve fill by ID"""
        with self._lock:
            return self._store.get(fill_id)

    def list_by_order(self, order_id: str) -> List[Fill]:
        """List all fills for an order"""
        with self._lock:
            fill_ids = self._by_order.get(order_id, [])
            return [self._store[fid] for fid in fill_ids if fid in self._store]

    def list_by_run(self, run_id: str) -> List[Fill]:
        """List all fills for a simulation run"""
        with self._lock:
            fill_ids = self._by_run.get(run_id, [])
            return [self._store[fid] for fid in fill_ids if fid in self._store]

    def clear(self) -> None:
        """Clear all fills"""
        with self._lock:
            self._store.clear()
            self._by_order.clear()
            self._by_run.clear()


class TradeRepository(ITradeRepository):
    """In-memory repository for Trade entities"""

    def __init__(self) -> None:
        self._store: Dict[str, Trade] = {}
        self._by_run: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def create(self, trade: Trade) -> Trade:
        """Store a new trade"""
        with self._lock:
            if trade.trade_id in self._store:
                raise ValueError(f"Trade {trade.trade_id} already exists")
            self._store[trade.trade_id] = trade
            if trade.simulation_run_id not in self._by_run:
                self._by_run[trade.simulation_run_id] = []
            self._by_run[trade.simulation_run_id].append(trade.trade_id)
            return trade

    def get(self, trade_id: str) -> Optional[Trade]:
        """Retrieve trade by ID"""
        with self._lock:
            return self._store.get(trade_id)

    def list_by_run(self, run_id: str) -> List[Trade]:
        """List all trades for a simulation run"""
        with self._lock:
            trade_ids = self._by_run.get(run_id, [])
            return [self._store[tid] for tid in trade_ids if tid in self._store]

    def clear(self) -> None:
        """Clear all trades"""
        with self._lock:
            self._store.clear()
            self._by_run.clear()


class PortfolioRepository(IPortfolioRepository):
    """In-memory repository for Portfolio snapshots"""

    def __init__(self) -> None:
        self._store: Dict[str, List[Portfolio]] = {}
        self._lock = threading.Lock()

    def append_snapshot(self, run_id: str, portfolio: Portfolio) -> None:
        """Append portfolio snapshot for a simulation run"""
        with self._lock:
            if run_id not in self._store:
                self._store[run_id] = []
            self._store[run_id].append(portfolio)

    def get_snapshots(self, run_id: str) -> List[Portfolio]:
        """Get all portfolio snapshots for a simulation run"""
        with self._lock:
            return list(self._store.get(run_id, []))

    def get_latest(self, run_id: str) -> Optional[Portfolio]:
        """Get latest portfolio snapshot for a simulation run"""
        with self._lock:
            snapshots = self._store.get(run_id, [])
            return snapshots[-1] if snapshots else None

    def clear(self) -> None:
        """Clear all portfolio snapshots"""
        with self._lock:
            self._store.clear()


class EquityCurveRepository(IEquityCurveRepository):
    """In-memory repository for EquityCurve entities"""

    def __init__(self) -> None:
        self._store: Dict[str, EquityCurve] = {}
        self._lock = threading.Lock()

    def save(self, curve: EquityCurve) -> EquityCurve:
        """Save or update equity curve"""
        with self._lock:
            self._store[curve.simulation_run_id] = curve
            return curve

    def get(self, run_id: str) -> Optional[EquityCurve]:
        """Retrieve equity curve by simulation run ID"""
        with self._lock:
            return self._store.get(run_id)

    def clear(self) -> None:
        """Clear all equity curves"""
        with self._lock:
            self._store.clear()


class SimulationReportRepository(ISimulationReportRepository):
    """In-memory repository for SimulationReport entities"""

    def __init__(self) -> None:
        self._store: Dict[str, SimulationReport] = {}
        self._by_run: Dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, report: SimulationReport) -> SimulationReport:
        """Store a new simulation report"""
        with self._lock:
            if report.report_id in self._store:
                raise ValueError(f"SimulationReport {report.report_id} already exists")
            self._store[report.report_id] = report
            self._by_run[report.simulation_run_id] = report.report_id
            return report

    def get(self, report_id: str) -> Optional[SimulationReport]:
        """Retrieve report by ID"""
        with self._lock:
            return self._store.get(report_id)

    def get_by_run(self, run_id: str) -> Optional[SimulationReport]:
        """Retrieve report by simulation run ID"""
        with self._lock:
            report_id = self._by_run.get(run_id)
            return self._store.get(report_id) if report_id else None

    def clear(self) -> None:
        """Clear all reports"""
        with self._lock:
            self._store.clear()
            self._by_run.clear()
