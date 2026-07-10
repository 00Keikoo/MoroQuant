"""Verification tests for Paper Trading Execution Integrity (Sprint 3.5).

Tests prove that:
1. Signal price (stale) != execution price (live)
2. Entry uses execution price, not signal price
3. LONG/SHORT PnL formulas are correct
4. Market data freshness check rejects stale data
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ml_service.trading.paper_broker import (
    open_paper_position,
    close_paper_position,
    _get_connection,
    _ensure_account,
)


@pytest.fixture
def db_conn():
    db_path = Path(__file__).parent.parent / "storage" / "test_database.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    with patch('ml_service.trading.paper_broker._DB_PATH', db_path):
        _ensure_account(conn)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                confidence INTEGER,
                regime TEXT,
                timeframe TEXT,
                prob_short REAL,
                prob_neutral REAL,
                prob_long REAL,
                execution_edge REAL,
                skip_reason TEXT,
                mae REAL DEFAULT 0.0,
                mfe REAL DEFAULT 0.0,
                mae_timestamp TIMESTAMP,
                mfe_timestamp TIMESTAMP,
                profit_capture_ratio REAL,
                final_exit_reason TEXT,
                trailing_stop_activated INTEGER DEFAULT 0,
                sl_move_count INTEGER DEFAULT 0,
                break_even_triggered INTEGER DEFAULT 0,
                execution_policy TEXT DEFAULT 'FIXED_SL',
                signal_price REAL,
                execution_price REAL,
                execution_timestamp TIMESTAMP,
                slippage_pct REAL,
                execution_latency_ms INTEGER
            )
        """)
        conn.commit()

    yield conn, db_path

    conn.close()
    if db_path.exists():
        db_path.unlink()


def test_stale_signal_price_vs_execution_price(db_conn):
    """Case 1: Signal price is stale, execution price is different.

    Expected: Entry uses execution_price, not stale signal.price
    """
    conn, db_path = db_conn

    stale_signal_price = 50000.0
    live_execution_price = 51000.0

    signal = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "price": stale_signal_price,
        "stop_loss": 49000.0,
        "take_profit": 53000.0,
        "confidence": 70,
        "regime": "trending_up",
        "timeframe": "1h",
        "prob_short": 0.1,
        "prob_neutral": 0.2,
        "prob_long": 0.7,
    }

    with patch('ml_service.trading.paper_broker._DB_PATH', db_path):
        with patch('ml_service.trading.mode_manager.get_trading_mode', return_value='PAPER'):
            with patch('ml_service.trading.paper_broker._fetch_price', return_value=live_execution_price):
                result = open_paper_position(signal)

    assert result is not None, "Position should open successfully"

    position_id = result["position_id"]
    row = conn.execute(
        "SELECT signal_price, execution_price, entry_price, slippage_pct FROM paper_positions WHERE id = ?",
        (position_id,),
    ).fetchone()

    assert row["signal_price"] == stale_signal_price, "signal_price should store stale price"
    assert row["execution_price"] == live_execution_price, "execution_price should be live price"
    assert row["entry_price"] == live_execution_price, "entry_price MUST use execution_price"

    expected_slippage = ((live_execution_price - stale_signal_price) / stale_signal_price) * 100.0
    assert abs(row["slippage_pct"] - expected_slippage) < 0.01, f"slippage_pct should be {expected_slippage:.2f}%"

    print(f"✓ Test passed: entry_price={row['entry_price']} uses execution_price, not signal_price={stale_signal_price}")


def test_long_pnl_correct(db_conn):
    """Case 2: LONG position PnL calculation is correct.

    Formula: (current - entry) * qty
    """
    conn, db_path = db_conn

    entry_price = 50000.0
    current_price = 52000.0
    qty = 0.1

    signal = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "price": entry_price,
        "stop_loss": 49000.0,
        "take_profit": 53000.0,
        "confidence": 70,
        "regime": "trending_up",
        "timeframe": "1h",
        "prob_short": 0.1,
        "prob_neutral": 0.2,
        "prob_long": 0.7,
    }

    with patch('ml_service.trading.paper_broker._DB_PATH', db_path):
        with patch('ml_service.trading.mode_manager.get_trading_mode', return_value='PAPER'):
            with patch('ml_service.trading.paper_broker._fetch_price', return_value=entry_price):
                result = open_paper_position(signal)

    position_id = result["position_id"]
    actual_qty = result["qty"]

    with patch('ml_service.trading.paper_broker._DB_PATH', db_path):
        close_result = close_paper_position(position_id, status="TP_HIT", close_price=current_price)

    expected_pnl = (current_price - entry_price) * actual_qty
    actual_pnl = close_result["realized_pnl"]

    assert abs(actual_pnl - expected_pnl) < 0.01, f"LONG PnL incorrect: expected {expected_pnl}, got {actual_pnl}"
    print(f"✓ Test passed: LONG PnL correct: {actual_pnl:.2f} (expected {expected_pnl:.2f}) with qty={actual_qty}")


def test_short_pnl_correct(db_conn):
    """Case 3: SHORT position PnL calculation is correct.

    Formula: (entry - current) * qty
    """
    conn, db_path = db_conn

    entry_price = 50000.0
    current_price = 48000.0
    qty = 0.1

    signal = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "price": entry_price,
        "stop_loss": 51000.0,
        "take_profit": 47000.0,
        "confidence": 70,
        "regime": "trending_down",
        "timeframe": "1h",
        "prob_short": 0.7,
        "prob_neutral": 0.2,
        "prob_long": 0.1,
    }

    with patch('ml_service.trading.paper_broker._DB_PATH', db_path):
        with patch('ml_service.trading.mode_manager.get_trading_mode', return_value='PAPER'):
            with patch('ml_service.trading.paper_broker._fetch_price', return_value=entry_price):
                result = open_paper_position(signal)

    position_id = result["position_id"]
    actual_qty = result["qty"]

    with patch('ml_service.trading.paper_broker._DB_PATH', db_path):
        close_result = close_paper_position(position_id, status="TP_HIT", close_price=current_price)

    expected_pnl = (entry_price - current_price) * actual_qty
    actual_pnl = close_result["realized_pnl"]

    assert abs(actual_pnl - expected_pnl) < 0.01, f"SHORT PnL incorrect: expected {expected_pnl}, got {actual_pnl}"
    print(f"✓ Test passed: SHORT PnL correct: {actual_pnl:.2f} (expected {expected_pnl:.2f}) with qty={actual_qty}")


def test_market_data_freshness_rejects_stale():
    """Case 4: Freshness check blocks stale market data.

    Expected: generate_signal() returns None for stale data
    """
    from ml_service.models.predictor import generate_signal
    import pandas as pd

    stale_timestamp = int((datetime.now() - timedelta(hours=10)).timestamp() * 1000)

    mock_df = pd.DataFrame({
        'timestamp': [stale_timestamp],
        'open': [50000.0],
        'high': [50100.0],
        'low': [49900.0],
        'close': [50050.0],
        'volume': [100.0],
    })

    with patch('ml_service.models.predictor.load_latest_model') as mock_load:
        mock_model = MagicMock()
        mock_load.return_value = {
            'model': mock_model,
            'metadata': {'feature_cols': ['close'], 'model_type': 'xgboost'},
        }

        with patch('ml_service.data.database.get_database') as mock_db:
            mock_conn = MagicMock()
            mock_conn.execute.return_value = mock_df
            mock_db.return_value.get_connection.return_value.__enter__.return_value = mock_conn

            with patch('pandas.read_sql_query', return_value=mock_df):
                result = generate_signal("BTCUSDT", "1h", persist=False)

    assert result is None, "generate_signal() should reject stale market data"
    print(f"✓ Test passed: Stale data (10h old) rejected by freshness check")


def test_market_data_freshness_accepts_fresh():
    """Case 5: Freshness check accepts fresh market data.

    Expected: generate_signal() proceeds with fresh data
    """
    from ml_service.models.predictor import generate_signal
    import pandas as pd
    import numpy as np

    fresh_timestamp = int(datetime.now().timestamp() * 1000) - 60000

    timestamps = [fresh_timestamp - (i * 3600000) for i in range(300, 0, -1)]
    mock_df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [50000.0] * 300,
        'high': [50100.0] * 300,
        'low': [49900.0] * 300,
        'close': [50050.0] * 300,
        'volume': [100.0] * 300,
    })

    with patch('ml_service.models.predictor.load_latest_model') as mock_load:
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.array([[0.2, 0.3, 0.5]])
        mock_model.feature_importances_ = np.array([0.5])

        mock_load.return_value = {
            'model': mock_model,
            'metadata': {
                'feature_cols': ['close'],
                'model_type': 'xgboost',
                'labeling_method': 'triple_barrier',
                'trained_at': datetime.now().isoformat(),
            },
            'model_path': '/tmp/test.pkl',
        }

        with patch('pandas.read_sql_query', return_value=mock_df):
            with patch('ml_service.models.predictor.prepare_features', return_value=mock_df):
                with patch('ml_service.models.predictor.save_signal_to_db'):
                    result = generate_signal("BTCUSDT", "1h", persist=False)

    assert result is not None, "generate_signal() should accept fresh market data"
    assert result['direction'] in ['long', 'short', 'neutral']
    print(f"✓ Test passed: Fresh data (1min old) accepted by freshness check")
