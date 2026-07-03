"""Ground truth signal outcome evaluation using actual signal prices and OHLCV data.

This module evaluates signal outcomes by scanning forward through OHLCV candles to determine
if TP or SL was hit. Unlike reconstruction, this uses the actual entry_price, take_profit,
and stop_loss values stored at signal generation time.

OUTCOME STATE MACHINE
=====================
States: PENDING -> WIN | LOSS | TIMEOUT

A signal remains PENDING until one of three final states is reached:
  - WIN:  TP hit within the evaluation window (up to 7 days)
  - LOSS: SL hit within the evaluation window (up to 7 days)
  - TIMEOUT: Neither TP nor SL hit within 7 full days

CHECKPOINT LOGIC
================
Checkpoints (1h, 4h, 12h, 24h, 48h) are MONITORING EVENTS ONLY.
They do NOT write to signal_outcomes. They are recorded in a separate
signal_checkpoints table. Early resolution (WIN/LOSS) at a checkpoint
IS a final outcome. But a timeout at any checkpoint is NOT final --
the signal stays pending until the 7-day final expiry.

This prevents premature classification and ensures long-duration
winners/lossers are correctly captured.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from ml_service.utils.logger import get_logger
from ml_service.analytics.calibration import CalibrationTracker

logger = get_logger()


# Intermediate checkpoint windows (monitoring only, not final)
CHECKPOINT_INTERVALS_HOURS = [1, 4, 12, 24, 48]

# Final expiry window for TIMEOUT determination
FINAL_TIMEOUT_DAYS = 7


@dataclass
class SignalOutcome:
    """Container for evaluated signal outcome."""
    signal_id: int
    symbol: str
    timeframe: str
    entry_price: float
    take_profit: float
    stop_loss: float
    outcome: str  # 'win', 'loss', or 'timeout' -- always a FINAL state
    exit_price: Optional[float]
    exit_time: Optional[int]
    max_favorable_excursion: float
    max_adverse_excursion: float
    holding_hours: Optional[float]


@dataclass
class CheckpointResult:
    """Result from a single checkpoint monitoring scan."""
    signal_id: int
    checkpoint_hours: int
    outcome_at_checkpoint: str  # 'win', 'loss', or 'still_pending'
    exit_price: Optional[float]
    exit_time: Optional[int]
    mfe: float
    mae: float


class OutcomeEngine:
    """Evaluates signal outcomes using actual signal prices and OHLCV data.

    Two-phase evaluation:
    1. Checkpoint phase: scans 1h/4h/12h/24h/48h windows for early WIN/LOSS.
       Checkpoint timeouts do NOT finalize the signal. They are recorded as
       monitoring events in signal_checkpoints.
    2. Final phase: at FINAL_TIMEOUT_DAYS (7 days), performs full-window scan.
       If still no TP/SL hit, marks as TIMEOUT (final).
    """

    TIMEOUT_DAYS = FINAL_TIMEOUT_DAYS

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)
        self.calibration_tracker = CalibrationTracker(db_path)
        self._ensure_checkpoint_table()
        self._ensure_performance_summary_table()
        self._ensure_confidence_stats_table()

    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_checkpoint_table(self):
        """Create signal_checkpoints table if it doesn't exist.

        This table stores monitoring events ONLY. It does NOT participate
        in the outcome state machine. A signal remains pending in
        signal_outcomes until it reaches WIN, LOSS, or TIMEOUT.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL,
                checkpoint_hours INTEGER NOT NULL,
                outcome_at_checkpoint TEXT NOT NULL,
                exit_price REAL,
                exit_time INTEGER,
                mfe REAL DEFAULT 0,
                mae REAL DEFAULT 0,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(signal_id, checkpoint_hours)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_checkpoints_signal
            ON signal_checkpoints(signal_id)
        """)

        conn.commit()
        conn.close()

    def _ensure_performance_summary_table(self):
        """Create model_performance_summary aggregation table if it doesn't exist.

        This table holds pre-computed per (symbol, timeframe) performance
        metrics derived from final outcomes in signal_outcomes. It is
        updated incrementally whenever a final outcome is saved.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                timeouts INTEGER NOT NULL DEFAULT 0,
                total_signals INTEGER NOT NULL DEFAULT 0,
                win_rate REAL,
                profit_factor_proxy REAL,
                avg_holding_hours REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_perf_summary_symbol
            ON model_performance_summary(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_perf_summary_symbol_tf
            ON model_performance_summary(symbol, timeframe)
        """)

        conn.commit()
        conn.close()

    def _ensure_confidence_stats_table(self):
        """Create model_confidence_stats aggregation table if it doesn't exist.

        This table holds pre-computed per (symbol, timeframe, confidence_bucket)
        outcome counts and the resulting actual_win_rate. It is updated
        incrementally whenever a final outcome is saved.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_confidence_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                confidence_bucket TEXT NOT NULL,
                signal_count INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                timeouts INTEGER NOT NULL DEFAULT 0,
                actual_win_rate REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, confidence_bucket)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_confidence_stats_symbol_tf
            ON model_confidence_stats(symbol, timeframe)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_confidence_stats_bucket
            ON model_confidence_stats(confidence_bucket)
        """)

        conn.commit()
        conn.close()

    def _timeframe_to_ms(self, timeframe: str) -> int:
        """Convert timeframe string to milliseconds."""
        units = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000
        }
        value = int(timeframe[:-1])
        unit = timeframe[-1]
        return value * units[unit]

    def load_signal_for_evaluation(self, signal_id: int) -> Optional[Dict]:
        """
        Load signal with prices for outcome evaluation.

        Returns:
            Dict with signal data or None if signal doesn't have prices
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, symbol, timeframe, timestamp, direction,
                entry_price, take_profit, stop_loss
            FROM signals
            WHERE id = ? AND entry_price IS NOT NULL
        """, (signal_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'id': row['id'],
            'symbol': row['symbol'],
            'timeframe': row['timeframe'],
            'timestamp': row['timestamp'],
            'direction': row['direction'],
            'entry_price': row['entry_price'],
            'take_profit': row['take_profit'],
            'stop_loss': row['stop_loss']
        }

    def evaluate_outcome(
        self,
        symbol: str,
        timeframe: str,
        entry_timestamp: int,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        direction: str,
        timeout_days: int = None
    ) -> Tuple[str, Optional[float], Optional[int], float, float]:
        """
        Scan forward through OHLCV to determine outcome.

        Args:
            symbol: Trading pair
            timeframe: Signal timeframe
            entry_timestamp: Signal generation timestamp
            entry_price: Entry price from signal
            take_profit: TP level from signal
            stop_loss: SL level from signal
            direction: 'long' or 'short'
            timeout_days: Override default timeout window

        Returns:
            (outcome, exit_price, exit_time, mfe, mae)
            outcome: 'win', 'loss', or 'timeout'
            mfe: Max Favorable Excursion (best profit level reached)
            mae: Max Adverse Excursion (worst loss level reached)
        """
        if timeout_days is None:
            timeout_days = self.TIMEOUT_DAYS

        conn = self._get_connection()
        cursor = conn.cursor()

        timeout_ms = timeout_days * 24 * 60 * 60 * 1000
        max_timestamp = entry_timestamp + timeout_ms

        # Get candles after entry
        cursor.execute("""
            SELECT timestamp, open, high, low, close
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
              AND timestamp > ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (symbol, timeframe, entry_timestamp, max_timestamp))

        candles = cursor.fetchall()
        conn.close()

        if not candles:
            return ('timeout', None, None, 0.0, 0.0)

        # Track MFE/MAE
        mfe = 0.0  # Best profit
        mae = 0.0  # Worst loss

        for candle in candles:
            if direction == 'long':
                # Calculate excursion for this candle
                favorable = candle['high'] - entry_price
                adverse = candle['low'] - entry_price

                mfe = max(mfe, favorable)
                mae = min(mae, adverse)

                # Check if TP hit (high >= TP)
                if candle['high'] >= take_profit:
                    holding_ms = candle['timestamp'] - entry_timestamp
                    holding_hours = holding_ms / (60 * 60 * 1000)
                    return ('win', take_profit, candle['timestamp'], mfe, mae)

                # Check if SL hit (low <= SL)
                if candle['low'] <= stop_loss:
                    holding_ms = candle['timestamp'] - entry_timestamp
                    holding_hours = holding_ms / (60 * 60 * 1000)
                    return ('loss', stop_loss, candle['timestamp'], mfe, mae)

            elif direction == 'short':
                # For shorts, profit when price drops
                favorable = entry_price - candle['low']
                adverse = candle['high'] - entry_price

                mfe = max(mfe, favorable)
                mae = min(mae, adverse)

                # Check if TP hit (low <= TP, since we profit when price drops)
                if candle['low'] <= take_profit:
                    holding_ms = candle['timestamp'] - entry_timestamp
                    holding_hours = holding_ms / (60 * 60 * 1000)
                    return ('win', take_profit, candle['timestamp'], mfe, mae)

                # Check if SL hit (high >= SL)
                if candle['high'] >= stop_loss:
                    holding_ms = candle['timestamp'] - entry_timestamp
                    holding_hours = holding_ms / (60 * 60 * 1000)
                    return ('loss', stop_loss, candle['timestamp'], mfe, mae)

        # Timeout - neither TP nor SL hit within window
        return ('timeout', None, None, mfe, mae)

    def evaluate_signal(self, signal_id: int) -> Optional[SignalOutcome]:
        """
        Evaluate a single signal and return outcome using the full 7-day window.

        This performs a FINAL evaluation (no intermediate checkpoints).
        Used for direct evaluation when the full window is available.

        Args:
            signal_id: Signal ID to evaluate

        Returns:
            SignalOutcome or None if signal can't be evaluated
        """
        signal = self.load_signal_for_evaluation(signal_id)
        if not signal:
            logger.warning(f"Signal {signal_id} not found or missing prices")
            return None

        if signal['direction'] == 'neutral':
            logger.debug(f"Skipping neutral signal {signal_id}")
            return None

        outcome, exit_price, exit_time, mfe, mae = self.evaluate_outcome(
            symbol=signal['symbol'],
            timeframe=signal['timeframe'],
            entry_timestamp=signal['timestamp'],
            entry_price=signal['entry_price'],
            take_profit=signal['take_profit'],
            stop_loss=signal['stop_loss'],
            direction=signal['direction']
        )

        holding_hours = None
        if exit_time:
            holding_ms = exit_time - signal['timestamp']
            holding_hours = holding_ms / (60 * 60 * 1000)

        return SignalOutcome(
            signal_id=signal['id'],
            symbol=signal['symbol'],
            timeframe=signal['timeframe'],
            entry_price=signal['entry_price'],
            take_profit=signal['take_profit'],
            stop_loss=signal['stop_loss'],
            outcome=outcome,
            exit_price=exit_price,
            exit_time=exit_time,
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
            holding_hours=holding_hours
        )

    def save_outcome(self, outcome: SignalOutcome):
        """Save a FINAL outcome to the database.

        IMPORTANT: This writes to signal_outcomes ONLY for final states
        (win, loss, timeout). Checkpoint monitoring events go to
        signal_checkpoints instead.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO signal_outcomes (
                signal_id, symbol, timeframe,
                entry_price, take_profit, stop_loss,
                outcome, exit_price, exit_time,
                max_favorable_excursion, max_adverse_excursion,
                holding_hours, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(signal_id) DO UPDATE SET
                outcome = excluded.outcome,
                exit_price = excluded.exit_price,
                exit_time = excluded.exit_time,
                max_favorable_excursion = excluded.max_favorable_excursion,
                max_adverse_excursion = excluded.max_adverse_excursion,
                holding_hours = excluded.holding_hours,
                updated_at = CURRENT_TIMESTAMP
        """, (
            outcome.signal_id, outcome.symbol, outcome.timeframe,
            outcome.entry_price, outcome.take_profit, outcome.stop_loss,
            outcome.outcome, outcome.exit_price, outcome.exit_time,
            outcome.max_favorable_excursion, outcome.max_adverse_excursion,
            outcome.holding_hours
        ))

        conn.commit()

        if outcome.outcome in ('win', 'loss'):
            cursor.execute("""
                SELECT confidence FROM signals WHERE id = ?
            """, (outcome.signal_id,))
            row = cursor.fetchone()
            if row:
                confidence = row[0] / 100.0
                self.calibration_tracker.update_calibration_stats(
                    signal_id=outcome.signal_id,
                    symbol=outcome.symbol,
                    timeframe=outcome.timeframe,
                    confidence=confidence,
                    outcome=outcome.outcome
                )

        conn.close()

        # Auto-update the pre-computed performance summary for this
        # (symbol, timeframe) pair so dashboards don't have to re-scan
        # the full signal_outcomes table on every request.
        try:
            self._refresh_performance_summary(outcome.symbol, outcome.timeframe)
        except Exception as e:
            logger.error(
                f"Failed to update performance summary for "
                f"{outcome.symbol} {outcome.timeframe}: {e}"
            )

        # Auto-update the per-confidence-bucket statistics so confidence
        # vs. accuracy analytics stay in sync with ground truth.
        try:
            self._refresh_confidence_stats(outcome.signal_id, outcome.symbol, outcome.timeframe)
        except Exception as e:
            logger.error(
                f"Failed to update confidence stats for "
                f"{outcome.symbol} {outcome.timeframe}: {e}"
            )

    def _refresh_performance_summary(self, symbol: str, timeframe: str):
        """Recompute and upsert the performance summary for one (symbol, timeframe) pair.

        Recomputation from signal_outcomes is cheap per-pair and keeps the
        summary always consistent with ground truth -- even if rows were
        inserted by other code paths (e.g. migration repairs).
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN outcome = 'timeout' THEN 1 ELSE 0 END) AS timeouts
            FROM signal_outcomes
            WHERE symbol = ? AND timeframe = ?
        """, (symbol, timeframe))

        row = cursor.fetchone()
        total = row['total'] or 0
        wins = row['wins'] or 0
        losses = row['losses'] or 0
        timeouts = row['timeouts'] or 0

        # win_rate: fraction of *decided* outcomes (win + loss) that are wins.
        # Timeouts are excluded from the denominator because they are not
        # directional predictions -- the trade never resolved.
        decided = wins + losses
        win_rate = (wins / decided) if decided > 0 else None

        # profit_factor_proxy: ratio of gross TP distances captured (wins)
        # to gross SL distances suffered (losses), computed from the actual
        # signal prices stored at generation time. This is a structural
        # proxy (risk/reward realized), not a dollar PnL figure.
        cursor.execute("""
            SELECT
                SUM(CASE WHEN outcome = 'win'
                         THEN (take_profit - entry_price)
                         ELSE 0 END) AS gross_win_distance,
                SUM(CASE WHEN outcome = 'loss'
                         THEN (entry_price - stop_loss)
                         ELSE 0 END) AS gross_loss_distance
            FROM signal_outcomes
            WHERE symbol = ? AND timeframe = ?
        """, (symbol, timeframe))

        pf_row = cursor.fetchone()
        gross_win = abs(pf_row['gross_win_distance'] or 0.0)
        gross_loss = abs(pf_row['gross_loss_distance'] or 0.0)
        profit_factor_proxy = (gross_win / gross_loss) if gross_loss > 0 else None

        # avg_holding_hours over all resolved signals that have a holding time
        cursor.execute("""
            SELECT AVG(holding_hours) AS avg_hold
            FROM signal_outcomes
            WHERE symbol = ? AND timeframe = ?
              AND holding_hours IS NOT NULL
              AND outcome IN ('win', 'loss')
        """, (symbol, timeframe))

        hold_row = cursor.fetchone()
        avg_holding_hours = hold_row['avg_hold'] if hold_row['avg_hold'] is not None else None

        cursor.execute("""
            INSERT INTO model_performance_summary (
                symbol, timeframe,
                wins, losses, timeouts, total_signals,
                win_rate, profit_factor_proxy, avg_holding_hours,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol, timeframe) DO UPDATE SET
                wins = excluded.wins,
                losses = excluded.losses,
                timeouts = excluded.timeouts,
                total_signals = excluded.total_signals,
                win_rate = excluded.win_rate,
                profit_factor_proxy = excluded.profit_factor_proxy,
                avg_holding_hours = excluded.avg_holding_hours,
                updated_at = CURRENT_TIMESTAMP
        """, (
            symbol, timeframe,
            wins, losses, timeouts, total,
            win_rate, profit_factor_proxy, avg_holding_hours
        ))

        conn.commit()
        conn.close()

    def _confidence_bucket(self, confidence: int) -> Optional[str]:
        """Map a raw 0-100 signal confidence to a bucket label.

        Buckets align with the ones used elsewhere in the platform
        (model_calibration_stats) so the two views are comparable.

        Returns None for missing confidence (the signal is skipped rather
        than miscategorized).
        """
        if confidence is None:
            return None
        if confidence >= 80:
            return '80-100'
        if confidence >= 60:
            return '60-79'
        if confidence >= 40:
            return '40-59'
        return '0-39'

    def _refresh_confidence_stats(self, signal_id: int, symbol: str, timeframe: str):
        """Recompute and upsert confidence-bucket stats for one (symbol, timeframe) pair.

        For each confidence bucket present in this pair's final outcomes, count
        wins/losses/timeouts and derive actual_win_rate. Like the performance
        summary, full recompute per pair keeps the table resilient to outcome
        corrections and migration repairs.

        Note: the signal_id is passed for future per-signal audit hooks but is
        not required by the recompute-from-signal_outcomes approach.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Join signal_outcomes back to signals to get each signal's confidence.
        cursor.execute("""
            SELECT
                CASE
                    WHEN s.confidence >= 80 THEN '80-100'
                    WHEN s.confidence >= 60 THEN '60-79'
                    WHEN s.confidence >= 40 THEN '40-59'
                    ELSE '0-39'
                END AS confidence_bucket,
                COUNT(*) AS signal_count,
                SUM(CASE WHEN so.outcome = 'win' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN so.outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN so.outcome = 'timeout' THEN 1 ELSE 0 END) AS timeouts
            FROM signal_outcomes so
            JOIN signals s ON s.id = so.signal_id
            WHERE so.symbol = ? AND so.timeframe = ?
              AND s.confidence IS NOT NULL
            GROUP BY confidence_bucket
        """, (symbol, timeframe))

        buckets = cursor.fetchall()

        # Upsert each bucket row. Then delete any stale bucket rows for this
        # pair that no longer have data (e.g. after a correction removed the
        # last signal in a bucket).
        seen_buckets = set()
        for b in buckets:
            bucket = b['confidence_bucket']
            seen_buckets.add(bucket)

            signal_count = b['signal_count'] or 0
            wins = b['wins'] or 0
            losses = b['losses'] or 0
            timeouts = b['timeouts'] or 0

            decided = wins + losses
            actual_win_rate = (wins / decided) if decided > 0 else None

            cursor.execute("""
                INSERT INTO model_confidence_stats (
                    symbol, timeframe, confidence_bucket,
                    signal_count, wins, losses, timeouts,
                    actual_win_rate, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(symbol, timeframe, confidence_bucket) DO UPDATE SET
                    signal_count = excluded.signal_count,
                    wins = excluded.wins,
                    losses = excluded.losses,
                    timeouts = excluded.timeouts,
                    actual_win_rate = excluded.actual_win_rate,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                symbol, timeframe, bucket,
                signal_count, wins, losses, timeouts, actual_win_rate
            ))

        # Remove stale buckets (those with zero signals after correction/repair)
        if seen_buckets:
            placeholders = ','.join('?' for _ in seen_buckets)
            cursor.execute(
                f"""
                DELETE FROM model_confidence_stats
                WHERE symbol = ? AND timeframe = ?
                  AND confidence_bucket NOT IN ({placeholders})
                """,
                (symbol, timeframe, *seen_buckets)
            )
        else:
            cursor.execute(
                """
                DELETE FROM model_confidence_stats
                WHERE symbol = ? AND timeframe = ?
                """,
                (symbol, timeframe)
            )

        conn.commit()
        conn.close()

    def save_checkpoint(self, result: CheckpointResult):
        """Save a checkpoint monitoring event to signal_checkpoints.

        This does NOT affect the outcome state machine. The signal remains
        pending regardless of checkpoint results (unless the checkpoint
        found a WIN/LOSS, which is then promoted to a final outcome).
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO signal_checkpoints (
                signal_id, checkpoint_hours, outcome_at_checkpoint,
                exit_price, exit_time, mfe, mae, checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(signal_id, checkpoint_hours) DO UPDATE SET
                outcome_at_checkpoint = excluded.outcome_at_checkpoint,
                exit_price = excluded.exit_price,
                exit_time = excluded.exit_time,
                mfe = excluded.mfe,
                mae = excluded.mae,
                checked_at = CURRENT_TIMESTAMP
        """, (
            result.signal_id, result.checkpoint_hours,
            result.outcome_at_checkpoint,
            result.exit_price, result.exit_time,
            result.mfe, result.mae
        ))

        conn.commit()
        conn.close()

    def get_checked_checkpoints(self, signal_id: int) -> List[int]:
        """Return list of checkpoint hours already scanned for a signal."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT checkpoint_hours FROM signal_checkpoints
            WHERE signal_id = ?
        """, (signal_id,))

        checked = [row[0] for row in cursor.fetchall()]
        conn.close()
        return checked

    def get_pending_signals(self, limit: int = 100) -> list:
        """
        Get signals that need outcome evaluation.

        A signal is pending if it has NO final outcome (win/loss/timeout)
        in signal_outcomes. Checkpoint events in signal_checkpoints do NOT
        affect pending status.

        Returns:
            List of signal IDs that need evaluation
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.id
            FROM signals s
            LEFT JOIN signal_outcomes so ON s.id = so.signal_id
            WHERE s.entry_price IS NOT NULL
              AND s.direction != 'neutral'
              AND so.id IS NULL
            ORDER BY s.timestamp ASC
            LIMIT ?
        """, (limit,))

        signal_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        return signal_ids

    def evaluate_pending_outcomes(
        self,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Evaluate all pending signal outcomes.

        Two-phase evaluation per signal:
        1. Checkpoint phase: scan intermediate windows (1h, 4h, 12h, 24h, 48h).
           If WIN/LOSS found, record as FINAL outcome and stop.
           If timeout at checkpoint, record as monitoring event and continue.
        2. Final phase: if all checkpoints yielded timeout and enough time has
           elapsed since signal generation (>= FINAL_TIMEOUT_DAYS), perform
           a full-window scan. If still no resolution, mark as TIMEOUT (final).

        Returns:
            Stats dict with counts
        """
        pending_ids = self.get_pending_signals(limit=batch_size)

        stats = {
            'total_pending': len(pending_ids),
            'evaluated': 0,
            'wins': 0,
            'losses': 0,
            'timeouts': 0,
            'checkpoints_scanned': 0,
            'still_pending': 0,
            'failed': 0
        }

        logger.info(f"Evaluating {stats['total_pending']} pending signals")

        now_ms = int(datetime.now().timestamp() * 1000)

        for signal_id in pending_ids:
            try:
                result = self._evaluate_signal_phased(signal_id, now_ms)

                if result is None:
                    stats['failed'] += 1
                    continue

                if result.outcome in ('win', 'loss'):
                    # Final outcome found (possibly at an early checkpoint)
                    self.save_outcome(result)
                    stats['evaluated'] += 1
                    if result.outcome == 'win':
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1
                elif result.outcome == 'timeout':
                    # Final timeout (only after full expiry)
                    self.save_outcome(result)
                    stats['evaluated'] += 1
                    stats['timeouts'] += 1
                else:
                    # Signal still pending (not enough time elapsed)
                    stats['still_pending'] += 1

            except Exception as e:
                logger.error(f"Failed to evaluate signal {signal_id}: {e}")
                stats['failed'] += 1
                continue

        logger.info(f"Outcome evaluation complete: {stats}")
        return stats

    def _evaluate_signal_phased(
        self,
        signal_id: int,
        now_ms: int
    ) -> Optional[SignalOutcome]:
        """
        Evaluate a signal using phased approach.

        Phase 1 - Checkpoint monitoring:
          For each checkpoint window (1h, 4h, 12h, 24h, 48h):
            - Scan forward through OHLCV for that window
            - If WIN/LOSS found: return as FINAL outcome immediately
            - If timeout: record checkpoint event, continue to next
          Checkpoints are skipped if already checked.

        Phase 2 - Final resolution:
          Only triggered if the signal has existed for >= FINAL_TIMEOUT_DAYS
          since its entry timestamp. Performs full-window scan (7 days).
          If still no TP/SL hit, returns TIMEOUT (final).

        Args:
            signal_id: Signal to evaluate
            now_ms: Current time in milliseconds

        Returns:
            SignalOutcome with final state, or None if signal should remain pending
        """
        signal = self.load_signal_for_evaluation(signal_id)
        if not signal:
            return None

        if signal['direction'] == 'neutral':
            return None

        entry_ms = signal['timestamp']
        signal_age_ms = now_ms - entry_ms
        signal_age_hours = signal_age_ms / (60 * 60 * 1000)

        # Get already-checked checkpoints to avoid re-scanning
        checked_checkpoints = self.get_checked_checkpoints(signal_id)
        mfe = 0.0
        mae = 0.0

        # Phase 1: Checkpoint monitoring
        for hours in CHECKPOINT_INTERVALS_HOURS:
            if hours in checked_checkpoints:
                continue

            # Only check a checkpoint if enough time has elapsed for it
            if signal_age_hours < hours:
                continue

            timeout_days = hours / 24.0
            outcome, exit_price, exit_time, cp_mfe, cp_mae = self.evaluate_outcome(
                symbol=signal['symbol'],
                timeframe=signal['timeframe'],
                entry_timestamp=signal['timestamp'],
                entry_price=signal['entry_price'],
                take_profit=signal['take_profit'],
                stop_loss=signal['stop_loss'],
                direction=signal['direction'],
                timeout_days=timeout_days
            )

            # Track best MFE/MAE across all checkpoints
            if cp_mfe > mfe:
                mfe = cp_mfe
            if cp_mae < mae:
                mae = cp_mae

            # Save checkpoint monitoring event (regardless of result)
            cp_result = CheckpointResult(
                signal_id=signal_id,
                checkpoint_hours=hours,
                outcome_at_checkpoint=outcome,
                exit_price=exit_price,
                exit_time=exit_time,
                mfe=cp_mfe,
                mae=cp_mae
            )
            self.save_checkpoint(cp_result)
            stats_key = 'checkpoints_scanned'

            # If checkpoint found WIN or LOSS, that IS the final outcome
            if outcome in ('win', 'loss'):
                holding_hours = None
                if exit_time:
                    holding_ms = exit_time - signal['timestamp']
                    holding_hours = holding_ms / (60 * 60 * 1000)

                return SignalOutcome(
                    signal_id=signal['id'],
                    symbol=signal['symbol'],
                    timeframe=signal['timeframe'],
                    entry_price=signal['entry_price'],
                    take_profit=signal['take_profit'],
                    stop_loss=signal['stop_loss'],
                    outcome=outcome,
                    exit_price=exit_price,
                    exit_time=exit_time,
                    max_favorable_excursion=mfe,
                    max_adverse_excursion=mae,
                    holding_hours=holding_hours
                )

            # outcome == 'timeout' at checkpoint: NOT final, continue

        # Phase 2: Final resolution
        # Only attempt final evaluation if enough time has elapsed
        if signal_age_hours >= FINAL_TIMEOUT_DAYS * 24:
            outcome, exit_price, exit_time, final_mfe, final_mae = self.evaluate_outcome(
                symbol=signal['symbol'],
                timeframe=signal['timeframe'],
                entry_timestamp=signal['timestamp'],
                entry_price=signal['entry_price'],
                take_profit=signal['take_profit'],
                stop_loss=signal['stop_loss'],
                direction=signal['direction'],
                timeout_days=FINAL_TIMEOUT_DAYS
            )

            # Use the best MFE/MAE from both checkpoints and final scan
            if final_mfe > mfe:
                mfe = final_mfe
            if final_mae < mae:
                mae = final_mae

            if outcome in ('win', 'loss'):
                # TP/SL hit between last checkpoint and final expiry
                holding_hours = None
                if exit_time:
                    holding_ms = exit_time - signal['timestamp']
                    holding_hours = holding_ms / (60 * 60 * 1000)

                return SignalOutcome(
                    signal_id=signal['id'],
                    symbol=signal['symbol'],
                    timeframe=signal['timeframe'],
                    entry_price=signal['entry_price'],
                    take_profit=signal['take_profit'],
                    stop_loss=signal['stop_loss'],
                    outcome=outcome,
                    exit_price=exit_price,
                    exit_time=exit_time,
                    max_favorable_excursion=mfe,
                    max_adverse_excursion=mae,
                    holding_hours=holding_hours
                )

            # outcome == 'timeout' after full 7-day scan -- FINAL
            return SignalOutcome(
                signal_id=signal['id'],
                symbol=signal['symbol'],
                timeframe=signal['timeframe'],
                entry_price=signal['entry_price'],
                take_profit=signal['take_profit'],
                stop_loss=signal['stop_loss'],
                outcome='timeout',
                exit_price=None,
                exit_time=None,
                max_favorable_excursion=mfe,
                max_adverse_excursion=mae,
                holding_hours=None
            )

        # Signal is still pending: not enough time elapsed for final expiry
        # Do NOT save anything to signal_outcomes -- signal stays in pending queue
        return None
