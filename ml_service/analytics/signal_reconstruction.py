"""Legacy signal reconstruction for estimated performance analysis.

IMPORTANT: This module generates ESTIMATED performance data, not actual results.
All reconstructed prices and outcomes are approximations based on:
  - ATR calculated from historical OHLCV
  - Standard TP/SL multipliers (2.0x ATR TP, 1.0x ATR SL)
  - Entry price from signal timestamp candle close
  - Forward OHLCV scanning for outcome determination
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger()


@dataclass
class ReconstructedSignal:
    """Container for reconstructed signal data."""
    signal_id: int
    symbol: str
    timeframe: str
    direction: str
    confidence: int
    reconstructed_entry_price: float
    reconstructed_take_profit: float
    reconstructed_stop_loss: float
    reconstructed_exit_price: Optional[float]
    reconstructed_exit_time: Optional[int]
    reconstructed_outcome: Optional[str]
    reconstruction_method: str
    reconstruction_confidence: str
    atr_used: float
    tp_multiplier_used: float
    sl_multiplier_used: float


class SignalReconstructor:
    """Reconstruct estimated performance for legacy signals."""

    # Default multipliers based on common trading practices
    DEFAULT_TP_MULTIPLIER = 2.0
    DEFAULT_SL_MULTIPLIER = 1.0
    ATR_PERIOD = 14
    TIMEOUT_HOURS = 168  # 7 days

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)

    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _calculate_atr(self, symbol: str, timeframe: str, timestamp: int) -> Optional[float]:
        """Calculate ATR from OHLCV data at given timestamp."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get 14 candles ending at or before signal timestamp
        cursor.execute("""
            SELECT high, low, close
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, timeframe, timestamp, self.ATR_PERIOD + 1))

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < self.ATR_PERIOD:
            return None

        # Calculate True Range for each candle
        true_ranges = []
        for i in range(len(rows) - 1):
            current = rows[i]
            previous = rows[i + 1]

            tr = max(
                current['high'] - current['low'],
                abs(current['high'] - previous['close']),
                abs(current['low'] - previous['close'])
            )
            true_ranges.append(tr)

        if not true_ranges:
            return None

        return np.mean(true_ranges)

    def _get_entry_price(self, symbol: str, timeframe: str, timestamp: int) -> Optional[Tuple[float, int]]:
        """
        Get entry price from nearest candle at or before signal timestamp.

        Returns:
            (close_price, time_gap_ms) or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Find nearest candle at or before signal timestamp
        cursor.execute("""
            SELECT close, timestamp
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (symbol, timeframe, timestamp))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        time_gap = timestamp - row['timestamp']
        return (row['close'], time_gap)

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

    def _determine_outcome(
        self,
        symbol: str,
        timeframe: str,
        entry_timestamp: int,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        direction: str
    ) -> Tuple[Optional[str], Optional[float], Optional[int]]:
        """
        Scan forward through OHLCV to determine if TP or SL was hit.

        Returns:
            (outcome, exit_price, exit_time)
            outcome: 'win', 'loss', or 'timeout'
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        timeframe_ms = self._timeframe_to_ms(timeframe)
        timeout_ms = self.TIMEOUT_HOURS * 60 * 60 * 1000
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
            return ('timeout', entry_price, None)

        for candle in candles:
            if direction == 'long':
                # Check if TP hit (high >= TP)
                if candle['high'] >= take_profit:
                    return ('win', take_profit, candle['timestamp'])
                # Check if SL hit (low <= SL)
                if candle['low'] <= stop_loss:
                    return ('loss', stop_loss, candle['timestamp'])

            elif direction == 'short':
                # Check if TP hit (low <= TP, since we profit when price drops)
                if candle['low'] <= take_profit:
                    return ('win', take_profit, candle['timestamp'])
                # Check if SL hit (high >= SL)
                if candle['high'] >= stop_loss:
                    return ('loss', stop_loss, candle['timestamp'])

        # No hit within timeout period - use last close price
        last_candle = candles[-1]
        return ('timeout', last_candle['close'], last_candle['timestamp'])

    def reconstruct_signal(self, signal_id: int, signal_data: Dict) -> Optional[ReconstructedSignal]:
        """
        Reconstruct estimated performance for a single signal.

        Args:
            signal_id: Signal ID
            signal_data: Dict with keys: symbol, timeframe, timestamp, direction, confidence

        Returns:
            ReconstructedSignal or None if reconstruction failed
        """
        symbol = signal_data['symbol']
        timeframe = signal_data['timeframe']
        timestamp = signal_data['timestamp']
        direction = signal_data['direction']
        confidence = signal_data['confidence']

        # Skip neutral signals
        if direction == 'neutral':
            return None

        # Calculate ATR
        atr = self._calculate_atr(symbol, timeframe, timestamp)
        if atr is None:
            logger.warning(f"Could not calculate ATR for signal {signal_id}")
            return None

        # Get entry price
        entry_result = self._get_entry_price(symbol, timeframe, timestamp)
        if entry_result is None:
            logger.warning(f"Could not find entry price for signal {signal_id}")
            return None

        entry_price, time_gap = entry_result

        # Determine reconstruction confidence based on time gap
        timeframe_ms = self._timeframe_to_ms(timeframe)
        if time_gap <= timeframe_ms:
            reconstruction_confidence = 'high'
        elif time_gap <= timeframe_ms * 3:
            reconstruction_confidence = 'medium'
        else:
            reconstruction_confidence = 'low'

        # Calculate TP and SL
        tp_multiplier = self.DEFAULT_TP_MULTIPLIER
        sl_multiplier = self.DEFAULT_SL_MULTIPLIER

        if direction == 'long':
            take_profit = entry_price + (atr * tp_multiplier)
            stop_loss = entry_price - (atr * sl_multiplier)
        else:  # short
            take_profit = entry_price - (atr * tp_multiplier)
            stop_loss = entry_price + (atr * sl_multiplier)

        # Determine outcome
        outcome, exit_price, exit_time = self._determine_outcome(
            symbol, timeframe, timestamp, entry_price,
            take_profit, stop_loss, direction
        )

        return ReconstructedSignal(
            signal_id=signal_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            confidence=confidence,
            reconstructed_entry_price=entry_price,
            reconstructed_take_profit=take_profit,
            reconstructed_stop_loss=stop_loss,
            reconstructed_exit_price=exit_price,
            reconstructed_exit_time=exit_time,
            reconstructed_outcome=outcome,
            reconstruction_method='nearest_candle_atr',
            reconstruction_confidence=reconstruction_confidence,
            atr_used=atr,
            tp_multiplier_used=tp_multiplier,
            sl_multiplier_used=sl_multiplier
        )

    def save_reconstruction(self, reconstruction: ReconstructedSignal):
        """Save reconstructed signal to database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO signal_reconstruction (
                signal_id, symbol, timeframe, direction, confidence,
                reconstructed_entry_price, reconstructed_take_profit, reconstructed_stop_loss,
                reconstructed_exit_price, reconstructed_exit_time, reconstructed_outcome,
                reconstruction_method, reconstruction_confidence,
                atr_used, tp_multiplier_used, sl_multiplier_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reconstruction.signal_id, reconstruction.symbol, reconstruction.timeframe,
            reconstruction.direction, reconstruction.confidence,
            reconstruction.reconstructed_entry_price, reconstruction.reconstructed_take_profit,
            reconstruction.reconstructed_stop_loss, reconstruction.reconstructed_exit_price,
            reconstruction.reconstructed_exit_time, reconstruction.reconstructed_outcome,
            reconstruction.reconstruction_method, reconstruction.reconstruction_confidence,
            reconstruction.atr_used, reconstruction.tp_multiplier_used,
            reconstruction.sl_multiplier_used
        ))

        conn.commit()
        conn.close()

    def reconstruct_all_legacy_signals(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Reconstruct all legacy signals without entry_price.

        Returns:
            Stats dict with counts
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get legacy signals
        cursor.execute("""
            SELECT id, symbol, timeframe, timestamp, direction, confidence
            FROM signals
            WHERE entry_price IS NULL
            ORDER BY timestamp ASC
        """)

        signals = cursor.fetchall()
        conn.close()

        stats = {
            'total': len(signals),
            'reconstructed': 0,
            'skipped_neutral': 0,
            'failed': 0,
            'wins': 0,
            'losses': 0,
            'timeouts': 0
        }

        logger.info(f"Starting reconstruction of {stats['total']} legacy signals")

        for signal in signals:
            signal_data = {
                'symbol': signal['symbol'],
                'timeframe': signal['timeframe'],
                'timestamp': signal['timestamp'],
                'direction': signal['direction'],
                'confidence': signal['confidence']
            }

            reconstruction = self.reconstruct_signal(signal['id'], signal_data)

            if reconstruction is None:
                if signal['direction'] == 'neutral':
                    stats['skipped_neutral'] += 1
                else:
                    stats['failed'] += 1
                continue

            self.save_reconstruction(reconstruction)
            stats['reconstructed'] += 1

            if reconstruction.reconstructed_outcome == 'win':
                stats['wins'] += 1
            elif reconstruction.reconstructed_outcome == 'loss':
                stats['losses'] += 1
            elif reconstruction.reconstructed_outcome == 'timeout':
                stats['timeouts'] += 1

            if stats['reconstructed'] % batch_size == 0:
                logger.info(f"Progress: {stats['reconstructed']}/{stats['total']} signals reconstructed")

        logger.info(f"Reconstruction complete: {stats}")
        return stats
