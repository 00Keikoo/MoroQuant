"""Live performance metrics computation from real Binance trades.

Two complementary views are exposed:

1. Fill-level  — raw rows from ``user_trade_history`` (source of truth,
   never modified). Used for the "raw fills" audit/debug view.

2. Position-level — fills aggregated into closed round-trip positions.
   A *position* is a sequence of fills in the same symbol whose signed
   qty returns to zero (or reverses). This is what a trader sees in the
   Binance UI as a "closed position" and is the basis for the equity
   curve and the Recent Trades table.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


# ─── Raw fill queries ────────────────────────────────────────────────

def _fetch_fills(
    conn,
    symbol: Optional[str] = None,
    days_back: Optional[int] = None,
) -> List[Tuple]:
    """Return raw fill rows from user_trade_history ordered by trade_time."""
    cursor = conn.cursor()

    query = """
        SELECT id, symbol, side, price, qty, realized_pnl, commission,
               trade_time, matched_signal_id, market_regime, confidence_at_entry
        FROM user_trade_history
        WHERE 1=1
    """
    params: List = []

    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)

    if days_back:
        cutoff_ts = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
        query += " AND trade_time >= ?"
        params.append(cutoff_ts)

    query += " ORDER BY trade_time ASC"

    cursor.execute(query, params)
    return cursor.fetchall()


# ─── Position aggregation ────────────────────────────────────────────

def aggregate_closed_positions(fills: List[Tuple]) -> List[Dict]:
    """Aggregate raw fills into closed round-trip positions.

    A *position* is built by accumulating signed qty (BUY = +, SELL = -)
    for a symbol until the net qty returns to zero, at which point the
    position is "closed". Partial closes reduce the open qty but do not
    close the position. A reversal (sign flip) closes the current
    position and opens a new one in the opposite direction.

    Realized PnL and commission are summed across all fills in the
    position; the close time is the last fill's trade_time.
    """
    # Group fills by symbol first (each symbol tracked independently).
    by_symbol: Dict[str, List[Tuple]] = {}
    for f in fills:
        fill_id, sym, side, price, qty, rpnl, comm, ttime, sig_id, regime, conf = f
        by_symbol.setdefault(sym, []).append(f)

    closed_positions: List[Dict] = []

    for sym, sym_fills in by_symbol.items():
        # Already ordered ASC by trade_time from _fetch_fills.
        open_qty = 0.0
        open_direction: Optional[str] = None
        position_fills: List[Tuple] = []

        for f in sym_fills:
            fill_id, _, side, price, qty, rpnl, comm, ttime, sig_id, regime, conf = f
            signed = qty if side == 'BUY' else -qty

            # Direction of the fill relative to the current open position.
            fill_dir = 'long' if side == 'BUY' else 'short'

            if open_qty == 0:
                # Opening a new position.
                open_qty = signed
                open_direction = fill_dir
                position_fills = [f]
            else:
                # Does this fill close or reduce the open position?
                same_sign = (signed > 0) == (open_qty > 0)

                if same_sign:
                    # Adding to the position (scaling in).
                    open_qty += signed
                    position_fills.append(f)
                else:
                    # Reducing or closing.
                    open_qty += signed
                    position_fills.append(f)

                    if abs(open_qty) < 1e-12:
                        # Position fully closed.
                        closed_positions.append(
                            _build_position(sym, open_direction, position_fills)
                        )
                        open_qty = 0.0
                        open_direction = None
                        position_fills = []
                    elif (open_qty > 0) != (open_direction == 'long'):
                        # Reversal: the position flipped direction.
                        # Close the old position, open a new one with the
                        # residual qty in the new direction.
                        closed_positions.append(
                            _build_position(sym, open_direction, position_fills)
                        )
                        open_direction = 'long' if open_qty > 0 else 'short'
                        position_fills = []

        # Any leftover open position (not yet closed) is intentionally NOT
        # included — the dashboard only shows realized/closed performance.

    # Sort closed positions by close time ascending (chronological).
    closed_positions.sort(key=lambda p: p['closed_at'])
    return closed_positions


def _build_position(symbol: str, direction: str, fills: List[Tuple]) -> Dict:
    """Build a closed-position dict from its constituent fills."""
    realized_pnl = sum(f[5] for f in fills)
    commission = sum(f[6] for f in fills)
    net_pnl = realized_pnl - commission

    entry_fill = fills[0]
    exit_fill = fills[-1]

    entry_price = entry_fill[3]
    exit_price = exit_fill[3]

    opened_at = entry_fill[7]
    closed_at = exit_fill[7]

    total_qty = sum(abs(f[4]) for f in fills)

    # Carry signal attribution from the most confident matched fill.
    matched_signal_id = None
    market_regime = 'unknown'
    confidence_at_entry = None
    best_conf = -1
    for f in fills:
        _, _, _, _, _, _, _, _, sig_id, regime, conf = f
        if sig_id is not None and (conf or 0) > best_conf:
            best_conf = conf or 0
            matched_signal_id = sig_id
            market_regime = regime or 'unknown'
            confidence_at_entry = conf

    return {
        'symbol': symbol,
        'direction': direction,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'total_qty': total_qty,
        'realized_pnl': round(realized_pnl, 6),
        'commission': round(commission, 6),
        'net_pnl': round(net_pnl, 6),
        'opened_at': opened_at,
        'closed_at': closed_at,
        'matched_signal_id': matched_signal_id,
        'market_regime': market_regime,
        'confidence_at_entry': confidence_at_entry,
        'fill_count': len(fills),
    }


# ─── Metrics computation (position-level) ────────────────────────────

def compute_live_metrics(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """Compute live trading performance metrics from CLOSED POSITIONS.

    Args:
        symbol: Filter by symbol (None = all symbols)
        days_back: Look back period in days (None = all time)

    Returns:
        Dictionary with performance metrics
    """
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    if not fills:
        return {
            "status": "no_data",
            "message": "No trades found matching criteria",
            "metrics": {}
        }

    positions = aggregate_closed_positions(fills)

    if not positions:
        return {
            "status": "no_data",
            "message": "Trades exist but no positions have been fully closed yet",
            "metrics": {}
        }

    pnls = np.array([p['net_pnl'] for p in positions])
    total_trades = len(pnls)

    winning_trades = int(np.sum(pnls > 0))
    losing_trades = int(np.sum(pnls < 0))
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    total_pnl = float(np.sum(pnls))
    avg_pnl = float(np.mean(pnls))

    gross_profit = float(np.sum(pnls[pnls > 0])) if np.any(pnls > 0) else 0
    gross_loss = abs(float(np.sum(pnls[pnls < 0]))) if np.any(pnls < 0) else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    avg_win = float(np.mean(pnls[pnls > 0])) if np.any(pnls > 0) else 0
    avg_loss = float(np.mean(pnls[pnls < 0])) if np.any(pnls < 0) else 0
    win_rate_decimal = win_rate / 100
    expectancy = (win_rate_decimal * avg_win) - ((1 - win_rate_decimal) * abs(avg_loss))

    # Hold time: closed_at - opened_at per position (precise, not heuristic).
    hold_times_hours = [
        (p['closed_at'] - p['opened_at']) / (1000 * 3600)
        for p in positions
        if p['closed_at'] and p['opened_at']
    ]
    avg_hold_time_hours = float(np.mean(hold_times_hours)) if hold_times_hours else None

    # Sharpe ratio (annualized from per-trade PnL)
    if len(pnls) > 1:
        returns_std = float(np.std(pnls))
        if returns_std > 0:
            sharpe_ratio = (avg_pnl / returns_std) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = None

    # Max drawdown based on cumulative net PnL over closed positions
    cumulative_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = running_max - cumulative_pnl
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0

    # Peak drawdown percentage
    dd_peak_idx = int(np.argmax(drawdowns)) if len(drawdowns) > 0 else 0
    peak_value = running_max[dd_peak_idx] if len(running_max) > 0 else 0
    max_drawdown_pct = (max_drawdown / peak_value * 100) if peak_value > 0 else 0

    # ROI: total net PnL vs configured initial capital
    from ml_service.utils.config import get_config
    try:
        config = get_config()
        initial_capital = float(config.backtest.get('initial_capital', 10000.0))
    except Exception as e:
        logger.error(f"Error loading initial capital from config: {e}")
        initial_capital = 10000.0

    roi = (total_pnl / initial_capital) * 100

    metrics = {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "inf",
        "expectancy": round(expectancy, 2),
        "roi": round(roi, 4),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio is not None else None,
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_hold_time_hours": round(avg_hold_time_hours, 2) if avg_hold_time_hours else None,
    }

    return {
        "status": "success",
        "symbol": symbol or "all",
        "period_days": days_back or "all_time",
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }


def get_equity_curve(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> List[Dict]:
    """Generate equity curve from CLOSED POSITIONS.

    Each point on the curve represents one closed position (round trip),
    not a raw fill. The cumulative net PnL is the running sum of
    (realized_pnl - commission) across all fills in that position.

    Returns:
        List of equity curve points
        [{timestamp, cumulative_pnl, trade_count, trade_pnl}]
    """
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    if not fills:
        return []

    positions = aggregate_closed_positions(fills)

    equity_curve = []
    cumulative_pnl = 0.0
    trade_count = 0

    for pos in positions:
        cumulative_pnl += pos['net_pnl']
        trade_count += 1

        equity_curve.append({
            "timestamp": pos['closed_at'],
            "cumulative_pnl": round(cumulative_pnl, 2),
            "trade_count": trade_count,
            "trade_pnl": round(pos['net_pnl'], 2),
        })

    return equity_curve


if __name__ == "__main__":
    metrics = compute_live_metrics()
    print("\nLive Trading Metrics:")
    print("=" * 60)
    print(f"Status: {metrics['status']}")
    if metrics['status'] == 'success':
        for key, value in metrics['metrics'].items():
            print(f"{key}: {value}")
    else:
        print(metrics['message'])
