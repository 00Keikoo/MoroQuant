"""Immutable dataclasses for Execution Analytics Platform."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass(frozen=True)
class ExecutionDecisionRecord:
    """Represents an execution decision from execution_decisions table."""
    id: int
    symbol: str
    direction: Optional[str]
    decision: str
    reason: Optional[str]
    reason_detail: Optional[str]
    signal_id: Optional[int]
    position_id: Optional[int]
    confidence: Optional[int]
    regime: Optional[str]
    timeframe: Optional[str]
    execution_edge: Optional[float]
    signal_price: Optional[float]
    execution_price: Optional[float]
    slippage_pct: Optional[float]
    execution_latency_ms: Optional[int]
    created_at: datetime
    source: str
    execution_policy: Optional[str]


@dataclass(frozen=True)
class TradePositionRecord:
    """Represents a trade position from paper_positions table."""
    id: int
    symbol: str
    direction: str
    entry_price: float
    current_price: Optional[float]
    size_usdt: float
    qty: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: str
    realized_pnl: float
    opened_at: datetime
    closed_at: Optional[datetime]
    confidence: Optional[int]
    regime: Optional[str]
    timeframe: Optional[str]
    execution_edge: Optional[float]
    mae: float
    mfe: float
    final_exit_reason: Optional[str]
    execution_policy: str
    signal_price: Optional[float]
    execution_price: Optional[float]
    slippage_pct: Optional[float]
    execution_latency_ms: Optional[int]


@dataclass(frozen=True)
class SignalRecord:
    """Represents a signal from signals table."""
    id: int
    symbol: str
    timeframe: str
    timestamp: int
    direction: str
    confidence: int
    created_at: datetime
    regime: Optional[str]
    entry_price: Optional[float]


@dataclass(frozen=True)
class FunnelMetrics:
    """Execution funnel conversion metrics."""
    signals_generated: int
    accepted_count: int
    rejected_count: int
    opened_positions: int
    closed_positions: int
    acceptance_rate: float
    fill_rate: float


@dataclass(frozen=True)
class QualityMetrics:
    """Execution quality metrics."""
    avg_slippage_pct: float
    median_slippage_pct: float
    max_slippage_pct: float
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float


@dataclass(frozen=True)
class PerformanceMetrics:
    """Position performance metrics."""
    win_rate: float
    profit_factor: float
    expectancy: float
    total_pnl: float
    avg_holding_duration_seconds: float
    median_holding_duration_seconds: float
    exit_reason_distribution: Dict[str, int]


@dataclass(frozen=True)
class SegmentationGroup:
    """Metrics grouped by a segmentation dimension."""
    segment_value: str
    funnel: FunnelMetrics
    quality: QualityMetrics
    performance: PerformanceMetrics


@dataclass(frozen=True)
class ExecutionAnalyticsReport:
    """Complete execution analytics report."""
    source: str
    start_time: str
    end_time: str
    overall_funnel: FunnelMetrics
    overall_quality: QualityMetrics
    overall_performance: PerformanceMetrics
    rejection_reasons: Dict[str, int]
    by_symbol: List[SegmentationGroup]
    by_regime: List[SegmentationGroup]
    by_policy: List[SegmentationGroup]
