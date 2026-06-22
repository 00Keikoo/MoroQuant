"""Calibration measurement and Expected Calibration Error (ECE) calculation."""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np

from utils.logger import get_logger

logger = get_logger()


class CalibrationTracker:
    """Tracks model calibration statistics and calculates ECE."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)

    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_confidence_bucket(self, confidence: float) -> str:
        """Map confidence value to bucket."""
        if confidence >= 0.80:
            return '80-100'
        elif confidence >= 0.60:
            return '60-79'
        elif confidence >= 0.40:
            return '40-59'
        else:
            return '0-39'

    def update_calibration_stats(
        self,
        signal_id: int,
        symbol: str,
        timeframe: str,
        confidence: float,
        outcome: str
    ):
        """
        Update calibration statistics when an outcome is finalized.

        Args:
            signal_id: Signal ID
            symbol: Trading symbol
            timeframe: Timeframe
            confidence: Model confidence (0-1)
            outcome: 'win' or 'loss'
        """
        if outcome not in ('win', 'loss'):
            logger.debug(f"Skipping calibration update for signal {signal_id}: outcome={outcome}")
            return

        bucket = self._get_confidence_bucket(confidence)
        is_win = 1 if outcome == 'win' else 0

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO model_calibration_stats (
                symbol, timeframe, confidence_bucket,
                signal_count, win_count, loss_count,
                avg_confidence, actual_win_rate,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol, timeframe, confidence_bucket) DO UPDATE SET
                signal_count = signal_count + 1,
                win_count = win_count + ?,
                loss_count = loss_count + ?,
                avg_confidence = (
                    (avg_confidence * signal_count + ?) / (signal_count + 1)
                ),
                actual_win_rate = (
                    CAST(win_count + ? AS REAL) / (signal_count + 1)
                ),
                updated_at = CURRENT_TIMESTAMP
        """, (
            symbol, timeframe, bucket,
            is_win, 1 - is_win, confidence, confidence,
            is_win, 1 - is_win, confidence, is_win
        ))

        conn.commit()
        conn.close()

        logger.info(
            f"Updated calibration stats: {symbol} {timeframe} "
            f"bucket={bucket} outcome={outcome}"
        )

    def calculate_ece(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        num_bins: int = 10
    ) -> Tuple[float, float, int]:
        """
        Calculate Expected Calibration Error.

        ECE measures the difference between predicted confidence and actual accuracy
        across confidence bins.

        Args:
            symbol: Filter by symbol (None for all)
            timeframe: Filter by timeframe (None for all)
            num_bins: Number of confidence bins

        Returns:
            (ece_score, max_calibration_error, sample_size)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if symbol:
            where_clauses.append("s.symbol = ?")
            params.append(symbol)
        if timeframe:
            where_clauses.append("s.timeframe = ?")
            params.append(timeframe)

        where_clause = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        cursor.execute(f"""
            SELECT s.confidence, so.outcome
            FROM signals s
            JOIN signal_outcomes so ON s.id = so.signal_id
            WHERE so.outcome IN ('win', 'loss')
            {where_clause}
        """, params)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return (0.0, 0.0, 0)

        confidences = np.array([row['confidence'] / 100.0 for row in rows])
        outcomes = np.array([1 if row['outcome'] == 'win' else 0 for row in rows])

        bins = np.linspace(0, 1, num_bins + 1)
        bin_indices = np.digitize(confidences, bins[1:-1])

        ece = 0.0
        max_error = 0.0

        for i in range(num_bins):
            mask = bin_indices == i
            if not mask.any():
                continue

            bin_confidences = confidences[mask]
            bin_outcomes = outcomes[mask]

            avg_confidence = np.mean(bin_confidences)
            avg_accuracy = np.mean(bin_outcomes)
            bin_size = len(bin_confidences)

            calibration_error = abs(avg_confidence - avg_accuracy)
            ece += (bin_size / len(confidences)) * calibration_error
            max_error = max(max_error, calibration_error)

        return (float(ece), float(max_error), len(rows))

    def save_ece(
        self,
        ece_score: float,
        max_error: float,
        sample_size: int,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ):
        """Save ECE calculation to database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO model_calibration_ece (
                symbol, timeframe, ece_score, max_calibration_error, sample_size
            )
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, timeframe, ece_score, max_error, sample_size))

        conn.commit()
        conn.close()

        logger.info(
            f"Saved ECE: symbol={symbol} timeframe={timeframe} "
            f"ece={ece_score:.4f} max_err={max_error:.4f} n={sample_size}"
        )

    def calculate_and_save_ece(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Dict:
        """Calculate and save ECE, returning results."""
        ece, max_error, sample_size = self.calculate_ece(symbol, timeframe)

        if sample_size > 0:
            self.save_ece(ece, max_error, sample_size, symbol, timeframe)

        return {
            'ece_score': round(ece, 4),
            'max_calibration_error': round(max_error, 4),
            'sample_size': sample_size,
            'symbol': symbol,
            'timeframe': timeframe
        }

    def get_calibration_stats(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> List[Dict]:
        """Get calibration statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if symbol:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        if timeframe:
            where_clauses.append("timeframe = ?")
            params.append(timeframe)

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        cursor.execute(f"""
            SELECT
                symbol, timeframe, confidence_bucket,
                signal_count, win_count, loss_count,
                avg_confidence, actual_win_rate,
                updated_at
            FROM model_calibration_stats
            {where_clause}
            ORDER BY symbol, timeframe, confidence_bucket DESC
        """, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'confidence_bucket': row['confidence_bucket'],
                'signal_count': row['signal_count'],
                'win_count': row['win_count'],
                'loss_count': row['loss_count'],
                'avg_confidence': round(row['avg_confidence'], 3) if row['avg_confidence'] else None,
                'actual_win_rate': round(row['actual_win_rate'], 3) if row['actual_win_rate'] else None,
                'updated_at': row['updated_at']
            })

        conn.close()
        return results

    def get_latest_ece(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Optional[Dict]:
        """Get most recent ECE calculation."""
        conn = self._get_connection()
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if symbol:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        if timeframe:
            where_clauses.append("timeframe = ?")
            params.append(timeframe)

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        cursor.execute(f"""
            SELECT
                symbol, timeframe, ece_score,
                max_calibration_error, sample_size, calculated_at
            FROM model_calibration_ece
            {where_clause}
            ORDER BY calculated_at DESC
            LIMIT 1
        """, params)

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'symbol': row['symbol'],
            'timeframe': row['timeframe'],
            'ece_score': round(row['ece_score'], 4),
            'max_calibration_error': round(row['max_calibration_error'], 4),
            'sample_size': row['sample_size'],
            'calculated_at': row['calculated_at']
        }
