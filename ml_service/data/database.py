"""SQLite database schema and operations for ML trading system."""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from utils.logger import get_logger

logger = get_logger()


class Database:
    """SQLite database manager for OHLCV, events, and signals."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to storage/database.db relative to this file's location
            db_path = Path(__file__).parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe
                ON ohlcv(symbol, timeframe, timestamp DESC)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS macro_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    impact TEXT CHECK(impact IN ('high', 'medium', 'low')),
                    actual TEXT,
                    forecast TEXT,
                    previous TEXT,
                    source TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_date
                ON macro_events(date DESC)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('long', 'short', 'neutral')),
                    confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
                    features_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_timeframe
                ON signals(symbol, timeframe, timestamp DESC)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('long', 'short')),
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    leverage REAL NOT NULL,
                    size_usdt REAL NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_pct REAL NOT NULL,
                    opened_at TIMESTAMP NOT NULL,
                    closed_at TIMESTAMP NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_trades_closed_at
                ON user_trades(closed_at DESC)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_dominance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL UNIQUE,
                    btc_dominance REAL NOT NULL,
                    usdt_dominance REAL,
                    total_market_cap REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_dominance_timestamp
                ON market_dominance(timestamp DESC)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    qty REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    commission REAL NOT NULL,
                    trade_time INTEGER NOT NULL,
                    order_id TEXT UNIQUE NOT NULL,
                    matched_signal_id INTEGER,
                    market_regime TEXT,
                    confidence_at_entry INTEGER,
                    synced_at TEXT NOT NULL,
                    FOREIGN KEY (matched_signal_id) REFERENCES signals(id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_trade_history_symbol_time
                ON user_trade_history(symbol, trade_time DESC)
            """)

            conn.commit()
            logger.info("Database schema initialized")

    def db_info(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with table names and row counts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            tables = ["ohlcv", "macro_events", "signals", "user_trades", "market_dominance"]
            info = {}

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                info[table] = count

            cursor.execute("""
                SELECT symbol, timeframe, COUNT(*) as count
                FROM ohlcv
                GROUP BY symbol, timeframe
            """)
            ohlcv_breakdown = cursor.fetchall()

            info["ohlcv_breakdown"] = [
                {"symbol": row[0], "timeframe": row[1], "count": row[2]}
                for row in ohlcv_breakdown
            ]

            return info

    def print_db_info(self):
        """Print database statistics to console."""
        info = self.db_info()

        print("\n" + "="*50)
        print("DATABASE INFO")
        print("="*50)
        print(f"OHLCV records: {info['ohlcv']}")
        print(f"Macro events: {info['macro_events']}")
        print(f"Signals: {info['signals']}")

        if info['ohlcv_breakdown']:
            print("\nOHLCV Breakdown:")
            for item in info['ohlcv_breakdown']:
                print(f"  {item['symbol']} ({item['timeframe']}): {item['count']} candles")

        print("="*50 + "\n")


def get_database() -> Database:
    """Get database instance."""
    if not hasattr(get_database, "_db"):
        get_database._db = Database()
    return get_database._db
