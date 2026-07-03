"""Signal outcome tracking - connects signals to trade results."""

import json
from typing import Dict, List, Optional
from datetime import datetime

from ml_service.utils.logger import get_logger
from ml_service.data.database import get_database

logger = get_logger(__name__)


def aggregate_positions_from_trades() -> int:
    """
    Aggregate individual trades from user_trade_history into complete positions.

    Positions are identified by matching:
    - Same symbol
    - Same direction (BUY/SELL)
    - Trades within reasonable time window
    - Net position closes to zero or reverses

    Returns:
        Number of new positions created
    """
    db = get_database()
    inserted = 0

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get all matched trades that haven't been aggregated yet
        cursor.execute("""
            SELECT id, symbol, side, price, qty, realized_pnl, trade_time,
                   matched_signal_id, market_regime, confidence_at_entry
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
            ORDER BY symbol, trade_time ASC
        """)

        trades = cursor.fetchall()

        if not trades:
            logger.info("No matched trades to aggregate")
            return 0

        # Group trades by symbol and matched_signal_id
        positions = {}
        for trade in trades:
            trade_id, symbol, side, price, qty, realized_pnl, trade_time, signal_id, regime, confidence = trade

            key = (symbol, signal_id)
            if key not in positions:
                positions[key] = []
            positions[key].append({
                'id': trade_id,
                'symbol': symbol,
                'side': side,
                'price': price,
                'qty': qty,
                'realized_pnl': realized_pnl,
                'trade_time': trade_time,
                'signal_id': signal_id,
                'regime': regime,
                'confidence': confidence,
            })

        # Process each position group
        for (symbol, signal_id), trade_group in positions.items():
            # Get signal details
            cursor.execute("""
                SELECT timeframe, direction, confidence, model_version, regime
                FROM signals
                WHERE id = ?
            """, (signal_id,))

            signal_row = cursor.fetchone()
            if not signal_row:
                logger.warning(f"Signal {signal_id} not found for position")
                continue

            timeframe, direction, confidence, model_version, regime = signal_row

            # Check if outcome already exists for this signal
            cursor.execute("""
                SELECT id FROM signal_outcomes WHERE signal_id = ?
            """, (signal_id,))

            if cursor.fetchone():
                continue  # Already processed

            # Calculate position metrics
            total_pnl = sum(t['realized_pnl'] for t in trade_group)
            entry_time = min(t['trade_time'] for t in trade_group)
            exit_time = max(t['trade_time'] for t in trade_group)
            holding_period_ms = exit_time - entry_time
            holding_period_hours = holding_period_ms / (1000 * 60 * 60)

            # Determine outcome
            if total_pnl > 0:
                outcome = 'win'
            elif total_pnl < 0:
                outcome = 'loss'
            else:
                outcome = 'breakeven'

            # Map BUY/SELL to long/short
            trade_direction = 'long' if trade_group[0]['side'] == 'BUY' else 'short'

            # Store trade IDs as JSON array
            trade_ids = json.dumps([t['id'] for t in trade_group])

            # Insert into signal_outcomes
            cursor.execute("""
                INSERT INTO signal_outcomes (
                    signal_id, symbol, timeframe, direction, model_version, regime,
                    confidence, entry_time, exit_time, holding_period_hours,
                    realized_pnl, outcome, trade_ids
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, symbol, timeframe, trade_direction, model_version, regime,
                confidence, entry_time, exit_time, holding_period_hours,
                total_pnl, outcome, trade_ids
            ))

            inserted += 1

        conn.commit()

    logger.info(f"Created {inserted} signal outcomes from trade aggregation")
    return inserted


def get_win_rate_by_confidence() -> List[Dict]:
    """
    Calculate win rate by confidence bucket.

    Returns:
        List of dicts with confidence bucket stats
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                CASE
                    WHEN confidence >= 80 THEN '80-100'
                    WHEN confidence >= 60 THEN '60-79'
                    WHEN confidence >= 40 THEN '40-59'
                    ELSE '0-39'
                END as confidence_bucket,
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                AVG(realized_pnl) as avg_pnl,
                SUM(realized_pnl) as total_pnl,
                AVG(holding_period_hours) as avg_holding_hours
            FROM signal_outcomes
            GROUP BY confidence_bucket
            ORDER BY confidence_bucket DESC
        """)

        results = []
        for row in cursor.fetchall():
            bucket, total, wins, losses, avg_pnl, total_pnl, avg_hold = row
            win_rate = (wins / total * 100) if total > 0 else 0

            results.append({
                'confidence_range': bucket,
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate_pct': round(win_rate, 1),
                'avg_pnl': round(avg_pnl, 4),
                'total_pnl': round(total_pnl, 4),
                'avg_holding_hours': round(avg_hold, 1) if avg_hold else None,
            })

        return results


def get_win_rate_by_regime() -> List[Dict]:
    """
    Calculate win rate by market regime.

    Returns:
        List of dicts with regime stats
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                regime,
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                AVG(realized_pnl) as avg_pnl,
                SUM(realized_pnl) as total_pnl,
                AVG(confidence) as avg_confidence
            FROM signal_outcomes
            GROUP BY regime
            ORDER BY total_trades DESC
        """)

        results = []
        for row in cursor.fetchall():
            regime, total, wins, losses, avg_pnl, total_pnl, avg_conf = row
            win_rate = (wins / total * 100) if total > 0 else 0

            results.append({
                'regime': regime or 'unknown',
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate_pct': round(win_rate, 1),
                'avg_pnl': round(avg_pnl, 4),
                'total_pnl': round(total_pnl, 4),
                'avg_confidence': round(avg_conf, 1) if avg_conf else None,
            })

        return results


def get_win_rate_by_symbol() -> List[Dict]:
    """
    Calculate win rate by trading symbol.

    Returns:
        List of dicts with symbol stats
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                symbol,
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                AVG(realized_pnl) as avg_pnl,
                SUM(realized_pnl) as total_pnl,
                AVG(confidence) as avg_confidence
            FROM signal_outcomes
            GROUP BY symbol
            ORDER BY total_pnl DESC
        """)

        results = []
        for row in cursor.fetchall():
            symbol, total, wins, losses, avg_pnl, total_pnl, avg_conf = row
            win_rate = (wins / total * 100) if total > 0 else 0

            results.append({
                'symbol': symbol,
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate_pct': round(win_rate, 1),
                'avg_pnl': round(avg_pnl, 4),
                'total_pnl': round(total_pnl, 4),
                'avg_confidence': round(avg_conf, 1) if avg_conf else None,
            })

        return results


def get_pnl_by_model_version() -> List[Dict]:
    """
    Calculate PnL and performance by model version.

    Returns:
        List of dicts with model version stats
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                model_version,
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                AVG(realized_pnl) as avg_pnl,
                SUM(realized_pnl) as total_pnl,
                AVG(confidence) as avg_confidence,
                MIN(entry_time) as first_trade_time,
                MAX(entry_time) as last_trade_time
            FROM signal_outcomes
            GROUP BY model_version
            ORDER BY last_trade_time DESC
        """)

        results = []
        for row in cursor.fetchall():
            model_ver, total, wins, losses, avg_pnl, total_pnl, avg_conf, first_time, last_time = row
            win_rate = (wins / total * 100) if total > 0 else 0

            results.append({
                'model_version': model_ver or 'unknown',
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate_pct': round(win_rate, 1),
                'avg_pnl': round(avg_pnl, 4),
                'total_pnl': round(total_pnl, 4),
                'avg_confidence': round(avg_conf, 1) if avg_conf else None,
                'first_trade': datetime.fromtimestamp(first_time / 1000).isoformat() if first_time else None,
                'last_trade': datetime.fromtimestamp(last_time / 1000).isoformat() if last_time else None,
            })

        return results


def get_outcome_summary() -> Dict:
    """
    Get overall summary statistics for signal outcomes.

    Returns:
        Dict with summary metrics
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_positions,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as total_wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as total_losses,
                SUM(CASE WHEN outcome = 'breakeven' THEN 1 ELSE 0 END) as total_breakeven,
                AVG(realized_pnl) as avg_pnl,
                SUM(realized_pnl) as total_pnl,
                AVG(holding_period_hours) as avg_holding_hours,
                AVG(confidence) as avg_confidence
            FROM signal_outcomes
        """)

        row = cursor.fetchone()
        total, wins, losses, breakeven, avg_pnl, total_pnl, avg_hold, avg_conf = row

        win_rate = (wins / total * 100) if total > 0 else 0

        return {
            'total_positions': total or 0,
            'total_wins': wins or 0,
            'total_losses': losses or 0,
            'total_breakeven': breakeven or 0,
            'win_rate_pct': round(win_rate, 1),
            'avg_pnl': round(avg_pnl, 4) if avg_pnl else 0,
            'total_pnl': round(total_pnl, 4) if total_pnl else 0,
            'avg_holding_hours': round(avg_hold, 1) if avg_hold else None,
            'avg_confidence': round(avg_conf, 1) if avg_conf else None,
        }
