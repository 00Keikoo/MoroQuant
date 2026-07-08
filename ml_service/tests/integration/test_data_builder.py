"""Build test data for integration tests using real SQLite inserts."""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional


class TestDataBuilder:
    """Builder for seeding test database with realistic trade data."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def insert_trade(
        self,
        symbol: str = "BTCUSDT",
        direction: str = "LONG",
        entry_price: float = 50000.0,
        current_price: Optional[float] = None,
        size_usdt: float = 1000.0,
        qty: float = 0.02,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_id: Optional[int] = None,
        status: str = "OPEN",
        realized_pnl: float = 0.0,
        opened_at: Optional[str] = None,
        closed_at: Optional[str] = None,
        confidence: Optional[int] = None,
        regime: Optional[str] = None,
        timeframe: Optional[str] = None,
        prob_short: Optional[float] = None,
        prob_neutral: Optional[float] = None,
        prob_long: Optional[float] = None,
        execution_edge: Optional[float] = None,
        skip_reason: Optional[str] = None,
        mae: Optional[float] = None,
        mfe: Optional[float] = None,
        mae_timestamp: Optional[str] = None,
        mfe_timestamp: Optional[str] = None,
        profit_capture_ratio: Optional[float] = None,
        final_exit_reason: Optional[str] = None,
        trailing_stop_activated: int = 0,
        sl_move_count: int = 0,
        break_even_triggered: int = 0,
        execution_policy: str = "FIXED_SL"
    ) -> int:
        """Insert trade and return its ID."""
        if opened_at is None:
            opened_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO paper_positions (
                    symbol, direction, entry_price, current_price, size_usdt, qty,
                    stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at,
                    confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                    execution_edge, skip_reason, mae, mfe, mae_timestamp, mfe_timestamp,
                    profit_capture_ratio, final_exit_reason, trailing_stop_activated,
                    sl_move_count, break_even_triggered, execution_policy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, direction, entry_price, current_price, size_usdt, qty,
                stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at,
                confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                execution_edge, skip_reason, mae, mfe, mae_timestamp, mfe_timestamp,
                profit_capture_ratio, final_exit_reason, trailing_stop_activated,
                sl_move_count, break_even_triggered, execution_policy
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def insert_signal(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        timestamp: int = None,
        direction: str = "LONG",
        confidence: int = 75,
        features_json: Optional[str] = None
    ) -> int:
        """Insert signal and return its ID."""
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signals (symbol, timeframe, timestamp, direction, confidence, features_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, timeframe, timestamp, direction, confidence, features_json))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def seed_winning_trades(self, count: int = 3) -> List[int]:
        """Seed winning closed trades."""
        trade_ids = []
        base_time = datetime.now() - timedelta(days=7)

        for i in range(count):
            opened_at = (base_time + timedelta(hours=i * 2)).isoformat()
            closed_at = (base_time + timedelta(hours=i * 2 + 1)).isoformat()

            trade_id = self.insert_trade(
                symbol="BTCUSDT",
                direction="LONG",
                entry_price=50000.0 + i * 100,
                size_usdt=1000.0,
                qty=0.02,
                status="TP_HIT",
                realized_pnl=50.0 + i * 10,
                opened_at=opened_at,
                closed_at=closed_at,
                confidence=75 + i,
                regime="TRENDING_UP",
                timeframe="1h"
            )
            trade_ids.append(trade_id)

        return trade_ids

    def seed_losing_trades(self, count: int = 2) -> List[int]:
        """Seed losing closed trades."""
        trade_ids = []
        base_time = datetime.now() - timedelta(days=5)

        for i in range(count):
            opened_at = (base_time + timedelta(hours=i * 3)).isoformat()
            closed_at = (base_time + timedelta(hours=i * 3 + 1)).isoformat()

            trade_id = self.insert_trade(
                symbol="ETHUSDT",
                direction="SHORT",
                entry_price=3000.0 - i * 10,
                size_usdt=500.0,
                qty=0.166,
                status="SL_HIT",
                realized_pnl=-25.0 - i * 5,
                opened_at=opened_at,
                closed_at=closed_at,
                confidence=65 + i,
                regime="RANGING",
                timeframe="4h"
            )
            trade_ids.append(trade_id)

        return trade_ids

    def seed_open_trades(self, count: int = 2) -> List[int]:
        """Seed open trades."""
        trade_ids = []
        base_time = datetime.now() - timedelta(hours=12)

        for i in range(count):
            opened_at = (base_time + timedelta(hours=i * 2)).isoformat()

            trade_id = self.insert_trade(
                symbol="SOLUSDT",
                direction="LONG",
                entry_price=100.0 + i * 5,
                current_price=102.0 + i * 5,
                size_usdt=300.0,
                qty=3.0,
                status="OPEN",
                realized_pnl=0.0,
                opened_at=opened_at,
                confidence=70 + i * 2,
                regime="TRENDING_UP",
                timeframe="1h"
            )
            trade_ids.append(trade_id)

        return trade_ids

    def seed_mixed_dataset(self) -> dict:
        """Seed realistic mixed dataset."""
        return {
            "winning_trades": self.seed_winning_trades(3),
            "losing_trades": self.seed_losing_trades(2),
            "open_trades": self.seed_open_trades(2)
        }
