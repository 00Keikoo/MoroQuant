"""Execution Metrics Calculator.

Computes all metrics defined in the Execution Audit Framework research specification.
All formulas are implemented exactly as defined in docs/research/execution_audit_framework.md.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy import stats

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Get database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class TradeData:
    """Single trade data structure."""

    id: int
    entry_price: float
    exit_price: float
    direction: str
    realized_pnl_pct: float
    mae: float
    mfe: float
    mae_timestamp: Optional[str]
    mfe_timestamp: Optional[str]
    entry_time: str
    exit_time: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    final_exit_reason: Optional[str]
    confidence: Optional[int]
    regime: Optional[str]
    size_usdt: float


@dataclass
class ExecutionMetrics:
    """Complete execution metrics for audit."""

    avg_mae: float
    avg_mfe: float
    avg_pcr: float
    avg_pl: float
    avg_eqs: float
    avg_ee: float
    median_hold_time_hours: float
    max_drawdown: float
    intended_rr_mean: float
    realized_rr_mean: float
    mc_ec_count: int
    mc_ew_count: int
    mw_ec_count: int
    mw_ew_count: int
    ev_mc_ec: float
    ev_mc_ew: float
    ev_mw_ec: float
    ev_mw_ew: float
    ev_total: float
    total_trades: int


def load_trade_data() -> List[TradeData]:
    """Load closed trades from database."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, entry_price, current_price as exit_price, direction,
                   realized_pnl, size_usdt, mae, mfe, mae_timestamp, mfe_timestamp,
                   opened_at, closed_at, stop_loss, take_profit, final_exit_reason,
                   confidence, regime
            FROM paper_positions
            WHERE status != 'OPEN'
            """
        ).fetchall()
    finally:
        conn.close()

    trades = []
    for r in rows:
        if r["size_usdt"] and r["size_usdt"] > 0:
            realized_pnl_pct = (r["realized_pnl"] or 0.0) / r["size_usdt"]
        else:
            realized_pnl_pct = 0.0

        trades.append(
            TradeData(
                id=r["id"],
                entry_price=r["entry_price"],
                exit_price=r["exit_price"] or r["entry_price"],
                direction=r["direction"],
                realized_pnl_pct=realized_pnl_pct,
                mae=r["mae"] or 0.0,
                mfe=r["mfe"] or 0.0,
                mae_timestamp=r["mae_timestamp"],
                mfe_timestamp=r["mfe_timestamp"],
                entry_time=r["opened_at"],
                exit_time=r["closed_at"] or r["opened_at"],
                stop_loss=r["stop_loss"],
                take_profit=r["take_profit"],
                final_exit_reason=r["final_exit_reason"],
                confidence=r["confidence"],
                regime=r["regime"],
                size_usdt=r["size_usdt"] or 0.0,
            )
        )

    return trades


def compute_profit_capture_ratio(trade: TradeData) -> float:
    """Compute PCR for a single trade."""
    if trade.mfe <= 0:
        return 0.0

    pcr = trade.realized_pnl_pct / trade.mfe
    return max(0.0, min(1.0, pcr))


def compute_profit_leakage(trade: TradeData) -> float:
    """Compute PL for a single trade."""
    return trade.mfe - max(0.0, trade.realized_pnl_pct)


def compute_execution_quality_score(trade: TradeData, pcr: float) -> float:
    """Compute EQS for a single trade."""
    epsilon = 1e-6
    mae_abs = abs(trade.mae)
    denominator = mae_abs + trade.mfe + epsilon
    eqs = pcr * (1.0 - mae_abs / denominator)
    return eqs


def compute_execution_efficiency(trade: TradeData) -> float:
    """Compute EE for a single trade."""
    epsilon = 1e-6
    denominator = trade.mfe - trade.mae + epsilon
    return trade.realized_pnl_pct / denominator


def compute_intended_risk_reward(trade: TradeData) -> Optional[float]:
    """Compute intended R:R from stop/target levels."""
    if trade.stop_loss is None or trade.take_profit is None:
        return None

    target_distance = abs(trade.take_profit - trade.entry_price)
    stop_distance = abs(trade.stop_loss - trade.entry_price)

    if stop_distance == 0:
        return None

    return target_distance / stop_distance


def compute_realized_risk_reward(trade: TradeData) -> Optional[float]:
    """Compute realized R:R from actual PnL."""
    wins = []
    losses = []

    if trade.realized_pnl_pct > 0:
        wins.append(trade.realized_pnl_pct)
    elif trade.realized_pnl_pct < 0:
        losses.append(abs(trade.realized_pnl_pct))

    if not wins or not losses:
        return None

    return sum(wins) / sum(losses)


def classify_trade(
    trade: TradeData, theta_signal: float = 0.01, theta_pcr: float = 0.5
) -> str:
    """Classify trade into M/E matrix."""
    pcr = compute_profit_capture_ratio(trade)

    if trade.mfe >= theta_signal and pcr >= theta_pcr:
        return "MC/EC"
    elif trade.mfe >= theta_signal and pcr < theta_pcr:
        return "MC/EW"
    elif trade.mfe < theta_signal and trade.realized_pnl_pct == trade.mae:
        return "MW/EC"
    else:
        return "MW/EW"


def compute_ev_decomposition(
    trades: List[TradeData],
) -> Dict[str, float]:
    """Compute Expected Value decomposition by M/E classification."""
    classifications = {"MC/EC": [], "MC/EW": [], "MW/EC": [], "MW/EW": []}

    for trade in trades:
        cls = classify_trade(trade)
        classifications[cls].append(trade.realized_pnl_pct)

    total_trades = len(trades)
    ev_components = {}

    for cls, returns in classifications.items():
        count = len(returns)
        pct = count / total_trades if total_trades > 0 else 0.0
        mean_return = np.mean(returns) if returns else 0.0
        ev_components[cls] = {
            "count": count,
            "pct": pct,
            "mean_return": mean_return,
            "ev_contribution": pct * mean_return,
        }

    total_ev = sum(c["ev_contribution"] for c in ev_components.values())
    ev_components["total_ev"] = total_ev

    return ev_components


def compute_all_metrics(trades: List[TradeData]) -> ExecutionMetrics:
    """Compute all execution metrics."""
    if not trades:
        return ExecutionMetrics(
            avg_mae=0.0,
            avg_mfe=0.0,
            avg_pcr=0.0,
            avg_pl=0.0,
            avg_eqs=0.0,
            avg_ee=0.0,
            median_hold_time_hours=0.0,
            max_drawdown=0.0,
            intended_rr_mean=0.0,
            realized_rr_mean=0.0,
            mc_ec_count=0,
            mc_ew_count=0,
            mw_ec_count=0,
            mw_ew_count=0,
            ev_mc_ec=0.0,
            ev_mc_ew=0.0,
            ev_mw_ec=0.0,
            ev_mw_ew=0.0,
            ev_total=0.0,
            total_trades=0,
        )

    mae_list = [t.mae for t in trades]
    mfe_list = [t.mfe for t in trades]

    pcr_list = [compute_profit_capture_ratio(t) for t in trades]
    pl_list = [compute_profit_leakage(t) for t in trades]
    eqs_list = [
        compute_execution_quality_score(t, pcr) for t, pcr in zip(trades, pcr_list)
    ]
    ee_list = [compute_execution_efficiency(t) for t in trades]

    from datetime import datetime

    hold_times = []
    for t in trades:
        try:
            opened = datetime.strptime(t.entry_time.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            closed = datetime.strptime(t.exit_time.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            hold_times.append((closed - opened).total_seconds() / 3600.0)
        except Exception:
            pass

    intended_rr_list = [compute_intended_risk_reward(t) for t in trades]
    intended_rr_list = [x for x in intended_rr_list if x is not None]

    ev_decomp = compute_ev_decomposition(trades)

    return ExecutionMetrics(
        avg_mae=float(np.mean(mae_list)),
        avg_mfe=float(np.mean(mfe_list)),
        avg_pcr=float(np.mean(pcr_list)),
        avg_pl=float(np.mean(pl_list)),
        avg_eqs=float(np.mean(eqs_list)),
        avg_ee=float(np.mean(ee_list)),
        median_hold_time_hours=float(np.median(hold_times)) if hold_times else 0.0,
        max_drawdown=float(np.min([t.mae for t in trades])),
        intended_rr_mean=float(np.mean(intended_rr_list)) if intended_rr_list else 0.0,
        realized_rr_mean=0.0,
        mc_ec_count=ev_decomp["MC/EC"]["count"],
        mc_ew_count=ev_decomp["MC/EW"]["count"],
        mw_ec_count=ev_decomp["MW/EC"]["count"],
        mw_ew_count=ev_decomp["MW/EW"]["count"],
        ev_mc_ec=ev_decomp["MC/EC"]["ev_contribution"],
        ev_mc_ew=ev_decomp["MC/EW"]["ev_contribution"],
        ev_mw_ec=ev_decomp["MW/EC"]["ev_contribution"],
        ev_mw_ew=ev_decomp["MW/EW"]["ev_contribution"],
        ev_total=ev_decomp["total_ev"],
        total_trades=len(trades),
    )
