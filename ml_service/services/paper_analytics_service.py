"""Paper Trading Analytics Service.

Centralized analytics computation for paper trading research.
All research-focused analytics should live here rather than scattered
across the paper broker.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict

from utils.logger import get_logger

logger = get_logger()

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Get a database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def compute_confidence_analytics() -> Dict:
    """Compute analytics breakdown by confidence bucket for research."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT confidence, realized_pnl FROM paper_positions "
            "WHERE status != 'OPEN' AND confidence IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {}

    buckets = {}
    for conf, pnl in rows:
        try:
            conf_val = int(conf)
            bucket_key = f"{(conf_val // 10) * 10}-{(conf_val // 10) * 10 + 9}%"
            if bucket_key not in buckets:
                buckets[bucket_key] = {"trades": [], "pnls": []}
            buckets[bucket_key]["trades"].append(1)
            buckets[bucket_key]["pnls"].append(pnl)
        except (ValueError, TypeError):
            continue

    result = {}
    for bucket, data in buckets.items():
        total_trades = len(data["trades"])
        wins = sum(1 for p in data["pnls"] if p > 0)
        win_rate = (wins / total_trades * 100) if total_trades else 0
        total_pnl = sum(data["pnls"])
        avg_pnl = total_pnl / total_trades if total_trades else 0
        gross_profit = sum(p for p in data["pnls"] if p > 0)
        gross_loss = abs(sum(p for p in data["pnls"] if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        result[bucket] = {
            "bucket": bucket,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.0,
        }

    return result


def compute_regime_analytics() -> Dict:
    """Compute analytics breakdown by market regime for research."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT regime, realized_pnl FROM paper_positions "
            "WHERE status != 'OPEN' AND regime IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {}

    regimes = {}
    for regime, pnl in rows:
        if not regime:
            regime = "unknown"
        if regime not in regimes:
            regimes[regime] = {"trades": [], "pnls": []}
        regimes[regime]["trades"].append(1)
        regimes[regime]["pnls"].append(pnl)

    result = {}
    for regime_name, data in regimes.items():
        total_trades = len(data["trades"])
        wins = sum(1 for p in data["pnls"] if p > 0)
        win_rate = (wins / total_trades * 100) if total_trades else 0
        total_pnl = sum(data["pnls"])
        avg_pnl = total_pnl / total_trades if total_trades else 0

        result[regime_name] = {
            "regime": regime_name,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
        }

    return result


def compute_sharpe_ratio() -> float | None:
    """Compute Sharpe ratio for paper trading returns.

    Returns None if insufficient observations (< 10 trades).
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT realized_pnl FROM paper_positions WHERE status != 'OPEN'"
        ).fetchall()
    finally:
        conn.close()

    if len(rows) < 10:
        return None

    pnls = [r[0] for r in rows]
    mean_pnl = sum(pnls) / len(pnls)

    variance = sum((p - mean_pnl) ** 2 for p in pnls) / len(pnls)
    std_dev = variance ** 0.5

    if std_dev == 0:
        return None

    sharpe = mean_pnl / std_dev
    return round(sharpe, 2)


def get_research_summary() -> Dict:
    """Get research summary card with key health indicators."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT realized_pnl, opened_at, closed_at FROM paper_positions "
            "WHERE status != 'OPEN'"
        ).fetchall()
        open_count = conn.execute(
            "SELECT COUNT(*) AS c FROM paper_positions WHERE status = 'OPEN'"
        ).fetchone()["c"]
    finally:
        conn.close()

    total_trades = len(rows)

    if total_trades == 0:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe": None,
            "expectancy": 0.0,
            "avg_hold_hours": 0.0,
            "open_positions": open_count,
            "last_updated": datetime.now().isoformat(),
        }

    wins = [r for r in rows if r["realized_pnl"] > 0]
    losses = [r for r in rows if r["realized_pnl"] <= 0]

    win_rate = len(wins) / total_trades * 100.0
    total_pnl = sum(r["realized_pnl"] for r in rows)
    expectancy = total_pnl / total_trades

    gross_profit = sum(r["realized_pnl"] for r in wins) if wins else 0.0
    gross_loss = abs(sum(r["realized_pnl"] for r in losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    hold_hours_list = []
    for r in rows:
        try:
            opened = datetime.strptime(r["opened_at"].replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            closed_str = r["closed_at"] or r["opened_at"]
            closed = datetime.strptime(closed_str.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            hold_hours_list.append((closed - opened).total_seconds() / 3600.0)
        except Exception:
            pass

    avg_hold = sum(hold_hours_list) / len(hold_hours_list) if hold_hours_list else 0.0
    sharpe = compute_sharpe_ratio()

    return {
        "trades": total_trades,
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.0,
        "sharpe": sharpe,
        "expectancy": round(expectancy, 2),
        "avg_hold_hours": round(avg_hold, 1),
        "open_positions": open_count,
        "last_updated": datetime.now().isoformat(),
    }


def _calculate_eqs(mae: float, mfe: float, realized_pnl: float,
                   size_usdt: float, status: str) -> int:
    """Calculate Execution Quality Score (0-100) from raw metrics.

    EQS is derived, not persisted. Combines:
    - MAE (drawdown management)
    - MFE (profit capture)
    - Exit quality
    """
    if size_usdt <= 0:
        return 0

    score = 50.0

    # Profit Capture (0-30 points)
    if mfe > 0.01:
        realized_pct = (realized_pnl / size_usdt) / mfe
        profit_capture = min(realized_pct, 1.0)
        score += profit_capture * 30.0
    elif realized_pnl > 0:
        score += 15.0

    # Drawdown Management (-20 to +10 points)
    if mae < -0.02:
        mae_penalty = abs(mae) * 100
        score -= min(mae_penalty, 20.0)
    else:
        score += 10.0

    # Exit Quality (0-20 points)
    if status == "TP_HIT":
        score += 20.0
    elif status == "SL_HIT":
        score += 5.0
    elif status == "EXPIRED":
        score += 0.0
    elif status == "MANUAL_CLOSE":
        score += 10.0

    return max(0, min(100, int(score)))


def compute_execution_analytics() -> Dict:
    """Compute execution quality analytics from closed paper positions.

    Returns metrics for Execution Research Laboratory:
    - Derived EQS (from raw metrics)
    - Average MAE/MFE
    - Lost Opportunity
    - Profit Capture
    - Trailing Analytics
    - Execution Classifications (model vs execution quality breakdown)
    """
    from services.execution_intelligence import (
        compute_execution_classifications,
        compute_execution_quality_score,
    )

    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT mae, mfe, profit_capture_ratio, opened_at, closed_at,
                   trailing_stop_activated, break_even_triggered, sl_move_count,
                   final_exit_reason, realized_pnl, size_usdt, status,
                   entry_price, stop_loss
            FROM paper_positions
            WHERE status != 'OPEN'
            """
        ).fetchall()
    finally:
        conn.close()

    total_trades = len(rows)

    if total_trades == 0:
        return {
            "total_trades": 0,
            "avg_eqs": 0.0,
            "avg_mae": 0.0,
            "avg_mfe": 0.0,
            "avg_lost_opportunity": 0.0,
            "avg_profit_capture": 0.0,
            "avg_hold_hours": 0.0,
            "trailing_activated": 0,
            "break_even_saves": 0,
            "avg_sl_moves": 0.0,
            "exit_reasons": {},
            "execution_classifications": {},
            "execution_quality_score": 0.0,
        }

    # Derive EQS from raw metrics
    eqs_list = []
    for r in rows:
        mae = r["mae"] or 0.0
        mfe = r["mfe"] or 0.0
        realized_pnl = r["realized_pnl"] or 0.0
        size_usdt = r["size_usdt"] or 0.0
        status = r["status"] or "UNKNOWN"
        if size_usdt > 0:
            eqs = _calculate_eqs(mae, mfe, realized_pnl, size_usdt, status)
            eqs_list.append(eqs)

    # Raw metrics
    mae_list = [r["mae"] for r in rows if r["mae"] is not None]
    mfe_list = [r["mfe"] for r in rows if r["mfe"] is not None]
    profit_capture_list = [r["profit_capture_ratio"] for r in rows if r["profit_capture_ratio"] is not None]

    # Lost Opportunity = MFE - Captured Profit
    lost_opportunity_list = []
    for r in rows:
        mfe = r["mfe"] or 0.0
        realized_pnl = r["realized_pnl"] or 0.0
        size_usdt = r["size_usdt"] or 0.0
        if size_usdt > 0 and mfe > 0:
            captured_profit_pct = realized_pnl / size_usdt
            lost_opportunity = mfe - captured_profit_pct
            lost_opportunity_list.append(lost_opportunity)

    avg_eqs = sum(eqs_list) / len(eqs_list) if eqs_list else 0.0
    avg_mae = sum(mae_list) / len(mae_list) if mae_list else 0.0
    avg_mfe = sum(mfe_list) / len(mfe_list) if mfe_list else 0.0
    avg_lost_opportunity = sum(lost_opportunity_list) / len(lost_opportunity_list) if lost_opportunity_list else 0.0
    avg_profit_capture = sum(profit_capture_list) / len(profit_capture_list) if profit_capture_list else 0.0

    # Hold time
    hold_hours_list = []
    for r in rows:
        try:
            opened = datetime.strptime(r["opened_at"].replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            closed_str = r["closed_at"] or r["opened_at"]
            closed = datetime.strptime(closed_str.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            hold_hours_list.append((closed - opened).total_seconds() / 3600.0)
        except Exception:
            pass

    avg_hold = sum(hold_hours_list) / len(hold_hours_list) if hold_hours_list else 0.0

    # Trailing analytics
    trailing_activated_count = sum(1 for r in rows if r["trailing_stop_activated"])
    break_even_count = sum(1 for r in rows if r["break_even_triggered"])
    sl_moves = [r["sl_move_count"] for r in rows if r["sl_move_count"] is not None]
    avg_sl_moves = sum(sl_moves) / len(sl_moves) if sl_moves else 0.0

    # Exit reasons
    exit_reasons = {}
    for r in rows:
        reason = r["final_exit_reason"] or "UNKNOWN"
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    # Execution Intelligence: classify trades by model vs execution quality
    execution_classifications = compute_execution_classifications()
    execution_quality_score = compute_execution_quality_score()

    return {
        "total_trades": total_trades,
        "avg_eqs": round(avg_eqs, 1),
        "avg_mae": round(avg_mae * 100, 2),
        "avg_mfe": round(avg_mfe * 100, 2),
        "avg_lost_opportunity": round(avg_lost_opportunity * 100, 2),
        "avg_profit_capture": round(avg_profit_capture * 100, 1),
        "avg_hold_hours": round(avg_hold, 1),
        "trailing_activated": trailing_activated_count,
        "break_even_saves": break_even_count,
        "avg_sl_moves": round(avg_sl_moves, 2),
        "exit_reasons": exit_reasons,
        "execution_classifications": execution_classifications,
        "execution_quality_score": execution_quality_score,
    }
