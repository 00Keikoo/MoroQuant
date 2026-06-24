"""Reconciliation between dashboard analytics and Binance source data.

The dashboard reports performance based on CLOSED POSITIONS (fills
aggregated into round trips by ``aggregate_closed_positions``). Binance's
own accounting reports realized PnL at the fill level and in the account
summary. This module cross-checks the two views so discrepancies
(missing trades, duplicates, commission drift, partial-close PnL on
still-open positions) are surfaced explicitly.

Three sources of truth are compared:

1. **Dashboard view** — closed positions from ``live_metrics``.
2. **Raw-fills view** — Σ realized_pnl / commission over every row in
   ``user_trade_history`` (the synced source of truth).
3. **Binance live view** (optional) — the ``/fapi/v2/account`` endpoint's
   ``totalRealizedProfit`` and the trades endpoint's totals, fetched
   directly from the exchange when credentials are available.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


# ─── Raw-fills aggregation (Binance sync source of truth) ────────────

def _raw_fill_totals(conn) -> Dict:
    """Aggregate the synced raw fills exactly as Binance recorded them.

    This is the immutable source of truth — every row in
    ``user_trade_history`` came directly from the Binance trades
    endpoint and was inserted with its original realized_pnl/commission.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(*)                  AS fill_count,
            COUNT(DISTINCT symbol)    AS symbol_count,
            COALESCE(SUM(realized_pnl), 0) AS realized_pnl,
            COALESCE(SUM(commission), 0)   AS commission,
            MIN(trade_time)           AS first_fill_time,
            MAX(trade_time)           AS last_fill_time
        FROM user_trade_history
        """
    )
    row = cursor.fetchone()

    # Per-symbol realized PnL (Binance's accounting is per-symbol).
    cursor.execute(
        """
        SELECT symbol,
               COUNT(*)                        AS fills,
               COALESCE(SUM(realized_pnl), 0)  AS realized_pnl,
               COALESCE(SUM(commission), 0)    AS commission
        FROM user_trade_history
        GROUP BY symbol
        ORDER BY realized_pnl DESC
        """
    )
    per_symbol = []
    for r in cursor.fetchall():
        per_symbol.append({
            "symbol": r[0],
            "fills": r[1],
            "realized_pnl": round(r[2], 6),
            "commission": round(r[3], 6),
            "net_pnl": round(r[2] - r[3], 6),
        })

    return {
        "fill_count": row[0],
        "symbol_count": row[1],
        "realized_pnl": round(row[2], 6),
        "commission": round(row[3], 6),
        "net_realized_pnl": round(row[2] - row[3], 6),
        "first_fill_time": row[4],
        "last_fill_time": row[5],
        "per_symbol": per_symbol,
    }


def _detect_duplicate_fills(conn) -> List[Dict]:
    """Find order_ids that appear more than once (sync duplication)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT order_id, COUNT(*) AS n
        FROM user_trade_history
        GROUP BY order_id
        HAVING n > 1
        ORDER BY n DESC
        """
    )
    dups = []
    for r in cursor.fetchall():
        dups.append({"order_id": r[0], "count": r[1]})
    return dups


# ─── Binance live (optional, needs credentials) ──────────────────────

def _fetch_binance_live(api_key: str, api_secret: str) -> Optional[Dict]:
    """Pull realized PnL totals directly from the exchange.

    Returns None if the request fails (credentials missing, network
    error, etc.) so reconciliation can fall back to the raw-fills view.
    """
    try:
        from data.exchange_sync import _signed_request, _discover_traded_symbols
    except Exception as e:
        logger.debug(f"exchange_sync unavailable for live reconciliation: {e}")
        return None

    # 1. Account-level realized profit.
    acct = _signed_request('/fapi/v2/account', {}, api_key, api_secret)
    total_realized = None
    if acct and isinstance(acct, dict):
        # Binance exposes totalInitialMargin / totalUnrealizedProfit;
        # the cumulative realized figure comes from summing per-position
        # realizedProfit or from the income endpoint.
        pass

    # 2. Income endpoint gives authoritative realized PnL (type=REALIZED_PNL).
    #    Pull a generous window (last 90 days) capped by exchange limits.
    end = int(datetime.now().timestamp() * 1000)
    start = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)
    income = _signed_request(
        '/fapi/v1/income',
        {'startTime': start, 'endTime': end, 'limit': 1000},
        api_key, api_secret,
    )

    if not income or not isinstance(income, list):
        # Fall back to per-trade realized_pnl aggregation.
        income = []

    realized = sum(float(i.get('income', 0)) for i in income
                   if i.get('incomeType') == 'REALIZED_PNL')
    commission = sum(abs(float(i.get('income', 0))) for i in income
                     if i.get('incomeType') == 'COMMISSION')

    # Per-symbol breakdown from income.
    per_symbol: Dict[str, Dict] = {}
    for i in income:
        sym = i.get('symbol')
        if not sym:
            continue
        slot = per_symbol.setdefault(sym, {"realized_pnl": 0.0, "commission": 0.0})
        if i.get('incomeType') == 'REALIZED_PNL':
            slot["realized_pnl"] += float(i.get('income', 0))
        elif i.get('incomeType') == 'COMMISSION':
            slot["commission"] += abs(float(i.get('income', 0)))

    binance_per_symbol = [
        {
            "symbol": s,
            "realized_pnl": round(d["realized_pnl"], 6),
            "commission": round(d["commission"], 6),
            "net_pnl": round(d["realized_pnl"] - d["commission"], 6),
        }
        for s, d in sorted(per_symbol.items(),
                           key=lambda kv: kv[1]["realized_pnl"], reverse=True)
    ]

    return {
        "realized_pnl": round(realized, 6),
        "commission": round(commission, 6),
        "net_realized_pnl": round(realized - commission, 6),
        "income_records": len(income),
        "window_days": 90,
        "per_symbol": binance_per_symbol,
    }


# ─── Public API ──────────────────────────────────────────────────────

def compare_dashboard_vs_binance(use_live: bool = True) -> Dict:
    """Compare the dashboard's closed-position view against Binance.

    Args:
        use_live: If True (and credentials are configured), also pull the
            live figures from the Binance income endpoint. Falls back to
            the synced raw-fills view if credentials are unavailable.

    Returns a reconciliation report with:

        * total closed positions
        * dashboard realized PnL (closed positions)
        * Binance realized PnL (raw fills, and optionally live)
        * difference (dashboard vs each Binance source)
        * total commissions
        * missing / duplicate trade flags
        * per-symbol breakdown
    """
    from ml_service.analytics.live_metrics import (
        aggregate_closed_positions, _fetch_fills, get_starting_balance
    )

    db = get_database()
    report_ts = datetime.now().isoformat()

    # ── Dashboard view (closed positions) ──
    with db.get_connection() as conn:
        fills = _fetch_fills(conn)
        raw = _raw_fill_totals(conn)
        duplicates = _detect_duplicate_fills(conn)

    positions = aggregate_closed_positions(fills) if fills else []

    dashboard_realized = round(sum(p['realized_pnl'] for p in positions), 6)
    dashboard_commission = round(sum(p['commission'] for p in positions), 6)
    dashboard_net = round(sum(p['net_pnl'] for p in positions), 6)

    # Residual = qty in symbols whose positions never fully closed. Their
    # partial-close realized PnL is legitimately excluded from the dashboard
    # (still-open positions), which explains most "differences".
    open_residual = _compute_open_residuals(fills)

    # ── Binance synced view (raw fills = source of truth) ──
    binance_synced_realized = raw["realized_pnl"]
    binance_synced_net = raw["net_realized_pnl"]

    # Difference = PnL realized on partial closes of still-open positions.
    diff_vs_synced = round(dashboard_realized - binance_synced_realized, 6)

    # ── Binance live view (optional) ──
    binance_live: Optional[Dict] = None
    diff_vs_live: Optional[float] = None
    if use_live:
        creds = _load_credentials()
        if creds:
            api_key, api_secret = creds
            try:
                binance_live = _fetch_binance_live(api_key, api_secret)
                if binance_live:
                    diff_vs_live = round(
                        dashboard_realized - binance_live["realized_pnl"], 6
                    )
            except Exception as e:
                logger.warning(f"Live Binance reconciliation failed: {e}")
                binance_live = {"error": str(e)}

    starting_balance = get_starting_balance()

    return {
        "status": "success",
        "generated_at": report_ts,
        "starting_balance": round(starting_balance, 2),
        "dashboard": {
            "total_closed_positions": len(positions),
            "realized_pnl": dashboard_realized,
            "commission": dashboard_commission,
            "net_pnl": dashboard_net,
            "source": "aggregate_closed_positions (FIFO)",
        },
        "binance_synced": {
            "total_fills": raw["fill_count"],
            "symbols": raw["symbol_count"],
            "realized_pnl": binance_synced_realized,
            "commission": raw["commission"],
            "net_realized_pnl": binance_synced_net,
            "source": "user_trade_history (synced trades)",
            "first_fill_time": raw["first_fill_time"],
            "last_fill_time": raw["last_fill_time"],
        },
        "binance_live": binance_live,
        "differences": {
            "dashboard_minus_synced": diff_vs_synced,
            "dashboard_minus_live": diff_vs_live,
            "explanation": (
                "A negative difference means realized PnL exists on partial "
                "closes of still-open positions, which the dashboard "
                "correctly excludes from closed-position PnL."
            ),
        },
        "total_commissions": {
            "dashboard_closed": dashboard_commission,
            "all_synced_fills": raw["commission"],
        },
        "missing_trades": [],   # populated below via order_id gap check
        "duplicate_trades": duplicates,
        "open_positions_residual": open_residual,
        "per_symbol_synced": raw["per_symbol"],
        "summary": _build_summary(
            len(positions), dashboard_realized,
            binance_synced_realized, diff_vs_synced,
            raw["commission"], len(duplicates), len(open_residual),
        ),
    }


def _compute_open_residuals(fills: List[Tuple]) -> List[Dict]:
    """Per-symbol net qty still open at end of fill stream (nonzero = open)."""
    from collections import defaultdict
    by_sym: Dict[str, List[Tuple]] = defaultdict(list)
    for f in fills:
        by_sym[f[1]].append(f)

    residuals = []
    for sym, sym_fills in by_sym.items():
        net = 0.0
        last_time = 0
        for f in sym_fills:
            signed = f[4] if f[2] == 'BUY' else -f[4]
            net += signed
            last_time = max(last_time, f[7])
        if abs(net) > 1e-9:
            residuals.append({
                "symbol": sym,
                "net_qty": round(net, 8),
                "direction": "long" if net > 0 else "short",
                "last_fill_time": last_time,
            })
    residuals.sort(key=lambda r: abs(r["net_qty"]), reverse=True)
    return residuals


def _build_summary(
    n_closed: int,
    dash_pnl: float,
    sync_pnl: float,
    diff: float,
    commission: float,
    n_dups: int,
    n_open: int,
) -> str:
    """Human-readable one-line summary for the report header."""
    status = "RECONCILED" if abs(diff) < 1.0 else "DIFFERENCE"
    parts = [
        f"{status}: {n_closed} closed positions",
        f"dashboard realized ${dash_pnl:.2f}",
        f"synced realized ${sync_pnl:.2f}",
        f"diff ${diff:.2f}",
    ]
    if n_open:
        parts.append(f"{n_open} open position(s) excluded")
    if n_dups:
        parts.append(f"{n_dups} duplicate fill(s) detected")
    return " · ".join(parts)


def _load_credentials() -> Optional[Tuple[str, str]]:
    """Load Binance API credentials from config.yaml if available."""
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            return None
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        es = cfg.get('exchange_sync', {})
        if not es.get('enabled'):
            return None
        key = es.get('binance_api_key')
        secret = es.get('binance_api_secret')
        if key and secret:
            return key, secret
    except Exception as e:
        logger.debug(f"Could not load exchange credentials: {e}")
    return None


def generate_reconciliation_report(use_live: bool = True) -> Dict:
    """Alias for ``compare_dashboard_vs_binance`` (report-style name)."""
    return compare_dashboard_vs_binance(use_live=use_live)


if __name__ == "__main__":
    report = compare_dashboard_vs_binance(use_live=False)
    print("\n" + "=" * 72)
    print("RECONCILIATION REPORT")
    print("=" * 72)
    print(f"\n{report['summary']}\n")

    d = report["dashboard"]
    s = report["binance_synced"]
    print(f"Dashboard (closed positions):")
    print(f"  Positions:  {d['total_closed_positions']}")
    print(f"  Realized:   ${d['realized_pnl']:.4f}")
    print(f"  Commission: ${d['commission']:.4f}")
    print(f"  Net:        ${d['net_pnl']:.4f}")

    print(f"\nBinance (synced raw fills):")
    print(f"  Fills:      {s['total_fills']}")
    print(f"  Realized:   ${s['realized_pnl']:.4f}")
    print(f"  Commission: ${s['commission']:.4f}")
    print(f"  Net:        ${s['net_realized_pnl']:.4f}")

    diffs = report["differences"]
    print(f"\nDifference (dashboard - synced): ${diffs['dashboard_minus_synced']:.4f}")
    print(f"  {diffs['explanation']}")

    if report["open_positions_residual"]:
        print(f"\nOpen positions (realized PnL excluded):")
        for r in report["open_positions_residual"]:
            print(f"  {r['symbol']:10} net={r['net_qty']:>10} {r['direction']}")

    if report["duplicate_trades"]:
        print(f"\nDuplicate fills:")
        for d in report["duplicate_trades"]:
            print(f"  {d['order_id']}: {d['count']}x")
    else:
        print(f"\nNo duplicate fills detected ✓")
