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

def get_starting_balance() -> float:
    """Configurable starting balance for the equity curve.

    Resolution order:
      1. ``ML_STARTING_BALANCE`` env var (easiest to override per-deploy)
      2. ``live_analytics.starting_balance`` in config.yaml (explicit key)
      3. ``exchange_sync.starting_balance`` in config.yaml
      4. ``backtest.initial_capital`` in config.yaml (existing setting)
      5. 10000.0 sane default

    Returns the resolved float balance.
    """
    import os
    # 1. Environment override wins.
    env_val = os.environ.get('ML_STARTING_BALANCE')
    if env_val:
        try:
            return float(env_val)
        except ValueError:
            logger.warning(f"ML_STARTING_BALANCE='{env_val}' is not numeric, ignoring")

    # 2/3/4. config.yaml keys.
    try:
        from ml_service.utils.config import get_config
        config = get_config()
        es = None
        # 2. Explicit live_analytics section (preferred).
        if hasattr(config, 'live_analytics'):
            es = config.live_analytics.get('starting_balance')
        # 3. exchange_sync section.
        if es is None and hasattr(config, 'exchange_sync'):
            es = config.exchange_sync.get('starting_balance')
        # 3b. data_sources.binance section.
        if es is None and hasattr(config, 'data_sources'):
            es = config.data_sources.get('binance', {}).get('starting_balance')
        # 4. backtest fallback.
        if es is None and hasattr(config, 'backtest'):
            es = config.backtest.get('initial_capital', 10000.0)
        if es is not None:
            return float(es)
    except Exception as e:
        logger.debug(f"Could not load starting balance from config: {e}")

    # 5. Fallback.
    return 10000.0


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
    """Aggregate raw fills into closed round-trip positions (FIFO lots).

    Each symbol is tracked independently. Within a symbol, fills are
    processed in chronological order and assigned to FIFO *lots*:

    * An **opening fill** (same direction as current net position, or the
      first fill when flat) opens/adds to lots.
    * A **reducing fill** (opposite direction) closes the oldest open lots
      first. A partial close closes some lots and leaves the rest open.
    * A **reversal** (reducing fill larger than the open position) closes
      *all* current lots — emitting a closed position — and the excess qty
      opens a fresh position in the opposite direction.

    A *position* is the set of lots opened together that get fully closed
    by one or more reducing fills. Only fully-closed positions are emitted;
    any residual open qty at the end of the fill stream is ignored (still
    open, unrealized).

    Binance attributes ``realized_pnl`` and ``commission`` per fill; we
    sum those across the fills that close each position, so the dashboard
    total reconciles exactly with Binance's realized PnL.
    """
    # Group fills by symbol first (each symbol tracked independently).
    by_symbol: Dict[str, List[Tuple]] = {}
    for f in fills:
        fill_id, sym, side, price, qty, rpnl, comm, ttime, sig_id, regime, conf = f
        by_symbol.setdefault(sym, []).append(f)

    closed_positions: List[Dict] = []

    for sym, sym_fills in by_symbol.items():
        # fills already ordered ASC by trade_time from _fetch_fills.
        closed_positions.extend(_aggregate_symbol(sym, sym_fills))

    # Sort closed positions by close time ascending (chronological).
    closed_positions.sort(key=lambda p: p['closed_at'])
    return closed_positions


def _aggregate_symbol(symbol: str, fills: List[Tuple]) -> List[Dict]:
    """FIFO lot engine for a single symbol's chronological fills."""
    closed_positions: List[Dict] = []

    # An "open position" groups one or more lots opened in the same
    # direction, waiting to be closed. We keep a single active builder at
    # a time per symbol (Binance hedge-mode aside, which is not used here).
    builder: Optional[_PositionBuilder] = None

    for f in fills:
        fill_id, _, side, price, qty, rpnl, comm, ttime, sig_id, regime, conf = f
        signed = qty if side == 'BUY' else -qty

        if builder is None or signed == 0:
            # Flat — opening a brand new position (or a zero-qty fill).
            if signed != 0:
                builder = _PositionBuilder(symbol, signed, f)
            continue

        # Same direction as the open position → scale in.
        if (signed > 0) == (builder.net_qty > 0):
            builder.add_open_fill(f)
            continue

        # Opposite direction → reduce (partial close, full close, reversal).
        # A reducing fill moves net_qty toward zero (and possibly past it on
        # a reversal). Reduce by close_qty in the reducing fill's direction.
        fill_abs = abs(signed)
        remaining = fill_abs
        reduce_dir = 1 if signed > 0 else -1

        # How much of THIS fill actually closes existing open qty? Everything
        # up to |net_qty| closes; anything beyond is a reversal that opens a
        # new position. Binance's realized_pnl is only earned on the closing
        # portion, while commission is charged on the entire fill qty.
        builder_open = abs(builder.net_qty) if builder else 0.0
        closing_total = min(fill_abs, builder_open)

        # Close lots FIFO until this reducing fill is consumed.
        while remaining > 1e-12 and builder is not None:
            open_abs = abs(builder.net_qty)
            close_qty = min(remaining, open_abs)

            # realized_pnl: earned only on closing qty → share by how much of
            #   the fill's closing portion this lot represents.
            # commission: charged on the whole fill → share by qty / fill_abs.
            rpnl_frac = (close_qty / closing_total) if closing_total > 0 else 0.0
            comm_frac = (close_qty / fill_abs) if fill_abs > 0 else 0.0
            builder.add_close_fill(f, close_qty, rpnl_frac, comm_frac)

            remaining -= close_qty
            # Moving net_qty toward zero by close_qty in the reduce direction.
            builder.net_qty += reduce_dir * close_qty

            if abs(builder.net_qty) < 1e-12:
                # Position fully closed → emit it.
                closed_positions.append(builder.build())
                builder = None

        # Any leftover reducing qty after closing everything → reversal:
        # opens a new position in the opposite direction with the excess.
        if remaining > 1e-12 and builder is None:
            reversal_signed = reduce_dir * remaining
            # Commission charged on the residual's share of the original fill.
            # realized_pnl is 0 — opening a new position earns no realized PnL.
            residual_comm = comm * (remaining / fill_abs) if fill_abs > 0 else 0.0
            # Reconstruct a synthetic opening fill carrying the residual qty,
            # its commission share, and the original fill's price/time.
            residual_fill = (
                fill_id, symbol,
                'BUY' if reversal_signed > 0 else 'SELL',
                price, abs(reversal_signed),
                0.0,            # realized_pnl — none on an opening residual
                residual_comm,  # commission share for the opening qty
                ttime, sig_id, regime, conf,
            )
            builder = _PositionBuilder(symbol, reversal_signed, residual_fill)

    # Any leftover open position (not yet closed) is intentionally NOT
    # emitted — the dashboard only shows realized/closed performance.

    return closed_positions


class _PositionBuilder:
    """Accumulates fills for one open position until it is closed.

    Tracks volume-weighted average entry/exit prices, the position's
    realized PnL/commission share, and signal attribution.
    """

    def __init__(self, symbol: str, signed_qty: float, opening_fill: Tuple):
        self.symbol = symbol
        self.direction = 'long' if signed_qty > 0 else 'short'
        self.net_qty = signed_qty

        # Weighted-average entry price over opening fills.
        self._entry_notional = opening_fill[3] * abs(signed_qty)
        self._entry_qty = abs(signed_qty)

        # Weighted-average exit price over closing fills.
        self._exit_notional = 0.0
        self._exit_qty = 0.0

        # Seed realized_pnl / commission from the opening fill. For a normal
        # opening fill these are 0, but the reversal-residual synthetic fill
        # (built in _aggregate_symbol) reuses the original fill's values, so
        # seeding here avoids silently dropping the opening commission.
        self.realized_pnl = float(opening_fill[5] or 0.0)
        self.commission = float(opening_fill[6] or 0.0)
        self.opened_at = opening_fill[7]
        self.closed_at = opening_fill[7]
        self.open_fill_ids = [opening_fill[0]]
        self.close_fill_ids: List = []

        # Signal attribution (pick highest-confidence matched fill).
        self._best_sig_id = opening_fill[8]
        self._best_regime = opening_fill[9]
        self._best_conf = opening_fill[10] or -1
        self._consider_attribution(opening_fill)

    def add_open_fill(self, fill: Tuple) -> None:
        """Scale in: add an opening (same-direction) fill."""
        _, _, _, price, qty, _, comm, ttime, _, _, _ = fill
        q = abs(qty)
        self._entry_notional += price * q
        self._entry_qty += q
        signed = qty if self.direction == 'long' else -qty
        self.net_qty += signed
        self.commission += comm
        self.closed_at = ttime
        self.open_fill_ids.append(fill[0])
        self._consider_attribution(fill)

    def add_close_fill(self, fill: Tuple, close_qty: float, rpnl_frac: float, comm_frac: float) -> None:
        """Reduce: attribute a share of a reducing fill.

        ``rpnl_frac`` and ``comm_frac`` differ on a reversal: Binance's
        realized_pnl only covers the closing qty, while commission covers
        the entire fill qty (including the reversal-residual that opens a
        new position).
        """
        _, _, _, price, _, rpnl, comm, ttime, _, _, _ = fill
        self._exit_notional += price * close_qty
        self._exit_qty += close_qty
        self.realized_pnl += rpnl * rpnl_frac
        self.commission += comm * comm_frac
        self.closed_at = ttime
        self.close_fill_ids.append(fill[0])
        self._consider_attribution(fill)

    def _consider_attribution(self, fill: Tuple) -> None:
        sig_id = fill[8]
        regime = fill[9]
        conf = fill[10]
        if sig_id is not None and (conf or 0) >= self._best_conf:
            self._best_conf = conf or 0
            self._best_sig_id = sig_id
            self._best_regime = regime or 'unknown'

    def build(self) -> Dict:
        entry_price = self._entry_notional / self._entry_qty if self._entry_qty else 0.0
        exit_price = self._exit_notional / self._exit_qty if self._exit_qty else 0.0
        net_pnl = self.realized_pnl - self.commission
        all_fill_ids = self.open_fill_ids + self.close_fill_ids

        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'side': self.direction,  # alias for API consumers
            'entry_price': round(entry_price, 8),
            'exit_price': round(exit_price, 8) if exit_price else None,
            'quantity': round(self._entry_qty, 8),
            'total_qty': round(self._entry_qty, 8),  # backward-compat alias
            'gross_pnl': round(self.realized_pnl, 6),
            'realized_pnl': round(self.realized_pnl, 6),
            'commission': round(self.commission, 6),
            'net_pnl': round(net_pnl, 6),
            'entry_time': self.opened_at,
            'exit_time': self.closed_at,
            'opened_at': self.opened_at,  # backward-compat alias
            'closed_at': self.closed_at,  # backward-compat alias
            'duration_ms': self.closed_at - self.opened_at,
            'duration_minutes': round((self.closed_at - self.opened_at) / 60000.0, 2),
            'matched_signal_id': self._best_sig_id,
            'market_regime': self._best_regime or 'unknown',
            'confidence_at_entry': self._best_conf if self._best_conf >= 0 else None,
            'fill_count': len(all_fill_ids),
            'fill_ids': all_fill_ids,
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

    # Starting balance & ROI (single source of truth for both equity + ROI).
    starting_balance = get_starting_balance()
    roi = (total_pnl / starting_balance) * 100 if starting_balance > 0 else 0

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
        "starting_balance": round(starting_balance, 2),
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
    not a raw fill. The equity at each point is:

        equity[n] = starting_balance + Σ(net_realized_pnl[0:n])

    where ``net_realized_pnl = realized_pnl - commission`` for the
    position. Open (unrealized) positions are ignored, matching the
    Binance "closed positions" view.

    Returns:
        List of equity curve points. Backward-compatible fields
        (``cumulative_pnl``, ``trade_count``, ``trade_pnl``) are kept;
        ``equity`` is the absolute account balance.
    """
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    if not fills:
        return []

    positions = aggregate_closed_positions(fills)

    starting_balance = get_starting_balance()

    equity_curve = []
    cumulative_pnl = 0.0
    trade_count = 0

    for pos in positions:
        cumulative_pnl += pos['net_pnl']
        trade_count += 1
        equity = starting_balance + cumulative_pnl

        equity_curve.append({
            "timestamp": pos['closed_at'],
            "equity": round(equity, 2),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "trade_count": trade_count,
            "trade_pnl": round(pos['net_pnl'], 2),
        })

    return equity_curve


def get_recent_trades(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None,
    limit: int = 50,
) -> List[Dict]:
    """Return the most recent CLOSED POSITIONS (newest first).

    Each trade row matches the schema required by the Recent Trades
    table — completed round trips, not raw fills:

        symbol, side, entry_time, exit_time, duration_minutes,
        entry_price, exit_price, quantity, gross_pnl, commission,
        net_pnl, regime, confidence, outcome

    Args:
        symbol: Filter by symbol (None = all symbols).
        days_back: Look back period in days (None = all time).
        limit: Maximum number of trades to return (default 50).
    """
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    if not fills:
        return []

    positions = aggregate_closed_positions(fills)

    # Newest closed position first.
    positions.sort(key=lambda p: p['closed_at'], reverse=True)

    recent = positions[:limit] if limit else positions

    trades = []
    for pos in recent:
        net = pos['net_pnl']
        # Outcome label derived from net PnL (after commissions).
        if net > 0:
            outcome = 'win'
        elif net < 0:
            outcome = 'loss'
        else:
            outcome = 'breakeven'

        trades.append({
            "symbol": pos['symbol'],
            "side": pos['direction'],
            "direction": pos['direction'],
            "entry_time": pos['entry_time'],
            "exit_time": pos['exit_time'],
            "duration_minutes": pos['duration_minutes'],
            "entry_price": pos['entry_price'],
            "exit_price": pos['exit_price'],
            "quantity": pos['quantity'],
            "gross_pnl": pos['gross_pnl'],
            "commission": pos['commission'],
            "net_pnl": net,
            "regime": pos['market_regime'],
            "confidence": pos['confidence_at_entry'],
            "outcome": outcome,
            "matched_signal_id": pos['matched_signal_id'],
            "fill_count": pos['fill_count'],
        })

    return trades


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
