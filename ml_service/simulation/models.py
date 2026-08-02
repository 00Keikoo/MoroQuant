"""
Simulation Domain Models

Immutable dataclasses representing the core simulation domain.
All models are frozen to ensure deterministic, pure functional execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class OrderSide(Enum):
    """Order direction"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order execution type"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(Enum):
    """Order lifecycle status"""
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class SimulationStatus(Enum):
    """Simulation run lifecycle status"""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class MarketSnapshot:
    """Point-in-time market state representation"""
    timestamp: datetime
    symbol: str
    mid_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    volume: Optional[float] = None
    open_interest: Optional[float] = None
    funding_rate: Optional[float] = None


@dataclass(frozen=True)
class ExecutionAssumption:
    """Immutable execution environment parameters"""
    commission: float
    maker_fee: float
    taker_fee: float
    slippage: float
    latency: int
    spread_model: str
    funding_fee: float
    borrow_fee: float


@dataclass(frozen=True)
class SimulationConfig:
    """Simulation configuration aggregate"""
    symbol_universe: List[str]
    timeframe: str
    start_time: datetime
    end_time: datetime
    initial_capital: float
    execution_assumption: ExecutionAssumption
    model_version_id: str
    dataset_snapshot_id: str
    config_hash: str


@dataclass(frozen=True)
class Order:
    """Strategy order intent"""
    order_id: str
    simulation_run_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    status: OrderStatus
    created_at: datetime


@dataclass(frozen=True)
class Fill:
    """Order execution fill event"""
    fill_id: str
    order_id: str
    simulation_run_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    slippage: float
    executed_at: datetime


@dataclass(frozen=True)
class Position:
    """Active market exposure"""
    symbol: str
    quantity: float
    average_entry_price: float
    unrealized_pnl: float
    realized_pnl: float
    leverage: float
    required_margin: float
    last_updated_at: datetime


@dataclass(frozen=True)
class Portfolio:
    """Portfolio state aggregate"""
    portfolio_id: str
    cash: float
    equity: float
    used_margin: float
    free_margin: float
    reserved_margin: float
    buying_power: float
    leverage: float
    exposure: float
    unrealized_pnl: float
    realized_pnl: float
    positions: Dict[str, Position] = field(default_factory=dict)


@dataclass(frozen=True)
class Trade:
    """Completed round-trip transaction"""
    trade_id: str
    simulation_run_id: str
    symbol: str
    quantity: float
    entry_price: float
    exit_price: float
    realized_pnl: float
    holding_time_seconds: float
    entered_at: datetime
    exited_at: datetime


@dataclass(frozen=True)
class EquityCurve:
    """Time-series equity evolution"""
    simulation_run_id: str
    timestamps: List[datetime]
    equity_values: List[float]

    def __post_init__(self) -> None:
        if len(self.timestamps) != len(self.equity_values):
            raise ValueError("timestamps and equity_values must have same length")


@dataclass(frozen=True)
class PerformanceMetrics:
    """Quantitative performance scorecard"""
    sharpe: float
    sortino: float
    calmar: float
    omega: float
    sterling: float
    mar: float
    profit_factor: float
    expectancy: float
    kelly: float
    recovery_factor: float
    ulcer_index: float
    tail_ratio: float
    skew: float
    kurtosis: float
    cagr: float
    alpha: float
    beta: float
    information_ratio: float
    tracking_error: float
    var: float
    cvar: float
    trade_count: int
    win_rate: float
    average_trade: float
    median_trade: float
    max_drawdown: float
    exposure_time: float
    average_holding_time: float
    brier_score: Optional[float]
    ece: Optional[float]
    profit_capture_ratio: float


@dataclass(frozen=True)
class SimulationReport:
    """Simulation output report aggregate"""
    report_id: str
    simulation_run_id: str
    metrics: PerformanceMetrics
    manifest_checksum: str
    bundle_path: str
    created_at: datetime


@dataclass(frozen=True)
class SimulationRun:
    """Simulation execution aggregate root"""
    run_id: str
    config: SimulationConfig
    status: SimulationStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
