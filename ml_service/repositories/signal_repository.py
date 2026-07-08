"""Repository for querying trading signals."""

from typing import List, Optional
from dataclasses import dataclass

from ml_service.repositories.database import get_connection


@dataclass
class Signal:
    """Represents a trading signal."""
    id: int
    symbol: str
    timeframe: str
    timestamp: int
    direction: str
    confidence: int
    features_json: Optional[str]
    created_at: str
    prob_short: Optional[float] = None
    prob_neutral: Optional[float] = None
    prob_long: Optional[float] = None
    model_version: Optional[str] = None
    feature_version: Optional[str] = None
    prediction_timestamp: Optional[int] = None
    regime: Optional[str] = None
    entry_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    tp_multiplier: Optional[float] = None
    sl_multiplier: Optional[float] = None
    labeling_method: Optional[str] = None
    atr: Optional[float] = None


class SignalRepository:
    """Repository for querying signals table."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._columns = None

    def _get_columns(self) -> List[str]:
        """Fetch available columns dynamically to support tests and different schemas."""
        if self._columns is not None:
            return self._columns

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("PRAGMA table_info(signals)")
            cols = [row['name'] for row in cursor.fetchall()]
            self._columns = cols
            return self._columns
        except Exception:
            return ["id", "symbol", "timeframe", "timestamp", "direction", "confidence", "features_json", "created_at"]
        finally:
            conn.close()

    def _row_to_signal(self, row) -> Signal:
        """Convert database row to Signal."""
        keys = row.keys()
        return Signal(
            id=row['id'],
            symbol=row['symbol'],
            timeframe=row['timeframe'],
            timestamp=row['timestamp'],
            direction=row['direction'],
            confidence=row['confidence'],
            features_json=row['features_json'] if 'features_json' in keys else None,
            created_at=row['created_at'] if 'created_at' in keys else None,
            prob_short=row['prob_short'] if 'prob_short' in keys else None,
            prob_neutral=row['prob_neutral'] if 'prob_neutral' in keys else None,
            prob_long=row['prob_long'] if 'prob_long' in keys else None,
            model_version=row['model_version'] if 'model_version' in keys else None,
            feature_version=row['feature_version'] if 'feature_version' in keys else None,
            prediction_timestamp=row['timestamp'] if 'timestamp' in keys else None,
            regime=row['regime'] if 'regime' in keys else None,
            entry_price=row['entry_price'] if 'entry_price' in keys else None,
            take_profit=row['take_profit'] if 'take_profit' in keys else None,
            stop_loss=row['stop_loss'] if 'stop_loss' in keys else None,
            tp_multiplier=row['tp_multiplier'] if 'tp_multiplier' in keys else None,
            sl_multiplier=row['sl_multiplier'] if 'sl_multiplier' in keys else None,
            labeling_method=row['labeling_method'] if 'labeling_method' in keys else None,
            atr=row['atr'] if 'atr' in keys else None
        )

    def find_by_id(self, signal_id: int) -> Optional[Signal]:
        """Find a signal by ID.

        Args:
            signal_id: Signal ID

        Returns:
            Signal if found, None otherwise
        """
        cols = ", ".join(self._get_columns())
        query = f"""
            SELECT {cols}
            FROM signals
            WHERE id = ?
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (signal_id,))
            row = cursor.fetchone()
            return self._row_to_signal(row) if row else None
        finally:
            conn.close()

    def find_by_symbol_and_timeframe(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Signal]:
        """Find signals by symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1h', '4h')
            limit: Maximum number of results

        Returns:
            List of Signal objects ordered by timestamp descending
        """
        cols = ", ".join(self._get_columns())
        query = f"""
            SELECT {cols}
            FROM signals
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (symbol, timeframe, limit))
            return [self._row_to_signal(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def find_recent(
        self,
        limit: int = 100,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        min_confidence: Optional[int] = None
    ) -> List[Signal]:
        """Find recent signals with optional filtering.

        Args:
            limit: Maximum number of results
            symbol: Optional symbol filter
            direction: Optional direction filter (long, short, neutral)
            min_confidence: Optional minimum confidence filter

        Returns:
            List of Signal objects ordered by timestamp descending
        """
        cols = ", ".join(self._get_columns())
        query = f"""
            SELECT {cols}
            FROM signals
            WHERE 1=1
        """
        params = []

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        if direction is not None:
            query += " AND direction = ?"
            params.append(direction)

        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            return [self._row_to_signal(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def count_by_symbol(self, symbol: str) -> int:
        """Count signals for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Count of signals
        """
        query = "SELECT COUNT(*) as count FROM signals WHERE symbol = ?"

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (symbol,))
            return cursor.fetchone()['count']
        finally:
            conn.close()

