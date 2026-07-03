"""Integration tests for Regime Execution Policy.

Verifies the complete pipeline:
Scheduler -> Signal -> Execution Policy -> Paper Broker -> Database
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ml_service.trading.paper_broker import open_paper_position
from ml_service.trading.regime_execution_policy import evaluate_regime_execution_policy


@pytest.fixture
def temp_db():
    """Create temporary database with schema."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = Path(temp_file.name)
    temp_file.close()

    conn = sqlite3.connect(str(temp_path))
    conn.row_factory = sqlite3.Row

    # Create required tables
    conn.execute("""
        CREATE TABLE paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT INTO paper_account (id, balance, equity) VALUES (1, 10000.0, 10000.0)"
    )

    conn.execute("""
        CREATE TABLE paper_positions (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
            entry_price REAL NOT NULL,
            current_price REAL,
            size_usdt REAL NOT NULL,
            qty REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            signal_id INTEGER,
            status TEXT NOT NULL DEFAULT 'OPEN',
            realized_pnl REAL NOT NULL DEFAULT 0.0,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            regime TEXT,
            timeframe TEXT,
            confidence INTEGER,
            prob_short REAL,
            prob_neutral REAL,
            prob_long REAL,
            execution_edge REAL,
            skip_reason TEXT,
            execution_policy TEXT DEFAULT 'FIXED_SL'
        )
    """)

    conn.execute("""
        CREATE TABLE regime_blocks (
            id INTEGER PRIMARY KEY,
            regime TEXT UNIQUE,
            is_active INTEGER,
            reason TEXT,
            created_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    yield temp_path
    temp_path.unlink()


class TestExecutionPipeline:
    """Test complete execution pipeline integration."""

    @patch('ml_service.trading.paper_broker._DB_PATH')
    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    @patch('ml_service.trading.mode_manager.get_trading_mode')
    @patch('ml_service.trading.paper_broker._fetch_price')
    def test_signal_executes_with_permitted_regime(
        self, mock_price, mock_mode, mock_policy_db, mock_broker_db, temp_db
    ):
        """Test signal executes when regime has positive EV."""
        mock_policy_db.__str__ = lambda _: str(temp_db)
        mock_policy_db.parent.mkdir = lambda **kwargs: None
        mock_broker_db.__str__ = lambda _: str(temp_db)
        mock_broker_db.parent.mkdir = lambda **kwargs: None
        mock_mode.return_value = "PAPER"
        mock_price.return_value = 100.0

        # Create historical positive EV for regime
        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            conn.execute(
                """
                INSERT INTO paper_positions
                    (symbol, direction, entry_price, current_price, stop_loss,
                     size_usdt, qty, regime, status, realized_pnl, closed_at)
                VALUES (?, 'LONG', 100, 110, 95, 100, 1, ?, 'TP_HIT', 10, datetime('now'))
                """,
                (f"SYM{i}", "trending_high_vol")
            )
        conn.commit()
        conn.close()

        signal = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "confidence": 70,
            "regime": "trending_high_vol",
            "prob_short": 0.1,
            "prob_neutral": 0.2,
            "prob_long": 0.7,
        }

        result = open_paper_position(signal)

        assert result is not None
        assert result["symbol"] == "BTCUSDT"
        assert result["direction"] == "LONG"

    @patch('ml_service.trading.paper_broker._DB_PATH')
    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    @patch('ml_service.trading.mode_manager.get_trading_mode')
    def test_signal_blocked_with_negative_uci_regime(
        self, mock_mode, mock_policy_db, mock_broker_db, temp_db
    ):
        """Test signal blocked when regime UCI < 0."""
        mock_policy_db.__str__ = lambda _: str(temp_db)
        mock_policy_db.parent.mkdir = lambda **kwargs: None
        mock_broker_db.__str__ = lambda _: str(temp_db)
        mock_broker_db.parent.mkdir = lambda **kwargs: None
        mock_mode.return_value = "PAPER"

        # Create historical negative EV for regime
        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            conn.execute(
                """
                INSERT INTO paper_positions
                    (symbol, direction, entry_price, current_price, stop_loss,
                     size_usdt, qty, regime, status, realized_pnl, closed_at)
                VALUES (?, 'LONG', 100, 90, 95, 100, 1, ?, 'SL_HIT', -10, datetime('now'))
                """,
                (f"SYM{i}", "choppy_low_vol")
            )
        conn.commit()
        conn.close()

        signal = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "confidence": 70,
            "regime": "choppy_low_vol",
            "prob_short": 0.1,
            "prob_neutral": 0.2,
            "prob_long": 0.7,
        }

        result = open_paper_position(signal)

        assert result is None

    @patch('ml_service.trading.paper_broker._DB_PATH')
    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    @patch('ml_service.trading.mode_manager.get_trading_mode')
    def test_signal_blocked_with_structural_block(
        self, mock_mode, mock_policy_db, mock_broker_db, temp_db
    ):
        """Test signal blocked when regime has structural block."""
        mock_policy_db.__str__ = lambda _: str(temp_db)
        mock_policy_db.parent.mkdir = lambda **kwargs: None
        mock_broker_db.__str__ = lambda _: str(temp_db)
        mock_broker_db.parent.mkdir = lambda **kwargs: None
        mock_mode.return_value = "PAPER"

        # Add structural block
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO regime_blocks (regime, is_active, reason) VALUES (?, 1, ?)",
            ("extreme_volatility", "API rate limits")
        )
        conn.commit()
        conn.close()

        signal = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "confidence": 70,
            "regime": "extreme_volatility",
            "prob_short": 0.1,
            "prob_neutral": 0.2,
            "prob_long": 0.7,
        }

        result = open_paper_position(signal)

        assert result is None

    @patch('ml_service.trading.paper_broker._DB_PATH')
    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    @patch('ml_service.trading.mode_manager.get_trading_mode')
    @patch('ml_service.trading.paper_broker._fetch_price')
    def test_signal_executes_with_insufficient_data(
        self, mock_price, mock_mode, mock_policy_db, mock_broker_db, temp_db
    ):
        """Test signal executes when N < 100 (insufficient data)."""
        mock_policy_db.__str__ = lambda _: str(temp_db)
        mock_policy_db.parent.mkdir = lambda **kwargs: None
        mock_broker_db.__str__ = lambda _: str(temp_db)
        mock_broker_db.parent.mkdir = lambda **kwargs: None
        mock_mode.return_value = "PAPER"
        mock_price.return_value = 100.0

        # Only 50 trades - below N_min threshold
        conn = sqlite3.connect(str(temp_db))
        for i in range(50):
            conn.execute(
                """
                INSERT INTO paper_positions
                    (symbol, direction, entry_price, current_price, stop_loss,
                     size_usdt, qty, regime, status, realized_pnl, closed_at)
                VALUES (?, 'LONG', 100, 90, 95, 100, 1, ?, 'SL_HIT', -10, datetime('now'))
                """,
                (f"SYM{i}", "new_regime")
            )
        conn.commit()
        conn.close()

        signal = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "confidence": 70,
            "regime": "new_regime",
            "prob_short": 0.1,
            "prob_neutral": 0.2,
            "prob_long": 0.7,
        }

        result = open_paper_position(signal)

        assert result is not None
        assert result["symbol"] == "BTCUSDT"
