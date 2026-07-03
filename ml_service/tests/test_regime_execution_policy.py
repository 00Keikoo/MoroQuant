"""Unit tests for Regime Execution Policy.

Tests the statistical framework defined in docs/research/regime_execution_policy.md
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ml_service.trading.regime_execution_policy import (
    ExecutionDecision,
    _bootstrap_confidence_interval,
    _compute_newey_west_adjustment,
    _is_structurally_blocked,
    _load_regime_trade_returns,
    evaluate_regime_execution_policy,
    get_regime_statistics,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = Path(temp_file.name)
    temp_file.close()

    conn = sqlite3.connect(str(temp_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE paper_positions (
            id INTEGER PRIMARY KEY,
            entry_price REAL,
            current_price REAL,
            stop_loss REAL,
            direction TEXT,
            realized_pnl REAL,
            size_usdt REAL,
            regime TEXT,
            status TEXT,
            closed_at TIMESTAMP
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
    conn.commit()
    conn.close()

    yield temp_path

    temp_path.unlink()


def _insert_trade(conn, regime, entry, exit_price, sl, direction, status="TP_HIT"):
    """Helper to insert a trade."""
    price_move = exit_price - entry
    if direction == "SHORT":
        price_move = -price_move
    initial_risk = abs(entry - sl)
    realized_pnl_pct = price_move / entry if entry > 0 else 0.0
    size_usdt = 100.0

    conn.execute(
        """
        INSERT INTO paper_positions
            (entry_price, current_price, stop_loss, direction, realized_pnl,
             size_usdt, regime, status, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (entry, exit_price, sl, direction, realized_pnl_pct * size_usdt, size_usdt, regime, status)
    )


class TestBootstrapConfidenceInterval:
    """Test bootstrap CI computation per Section 5.3."""

    def test_positive_returns(self):
        """Test bootstrap with positive mean returns."""
        returns = [0.5, 0.8, 1.2, 0.3, 0.9, 1.1, 0.6, 0.7, 1.0, 0.4]
        mean, lci, uci = _bootstrap_confidence_interval(returns, alpha=0.05, n_bootstrap=1000)

        assert mean > 0
        assert lci < mean < uci
        assert lci > 0

    def test_negative_returns(self):
        """Test bootstrap with negative mean returns."""
        returns = [-0.5, -0.8, -1.2, -0.3, -0.9, -1.1, -0.6, -0.7, -1.0, -0.4]
        mean, lci, uci = _bootstrap_confidence_interval(returns, alpha=0.05, n_bootstrap=1000)

        assert mean < 0
        assert lci < mean < uci
        assert uci < 0

    def test_mixed_returns(self):
        """Test bootstrap with mixed returns."""
        returns = [0.5, -0.3, 0.2, -0.1, 0.4, -0.2, 0.1, -0.4, 0.3, -0.1]
        mean, lci, uci = _bootstrap_confidence_interval(returns, alpha=0.05, n_bootstrap=1000)

        assert lci < mean < uci

    def test_zero_mean_returns(self):
        """Test bootstrap with returns centered at zero."""
        returns = [0.0] * 10
        mean, lci, uci = _bootstrap_confidence_interval(returns, alpha=0.05, n_bootstrap=1000)

        assert mean == 0.0
        assert lci <= 0.0 <= uci


class TestNeweyWestAdjustment:
    """Test autocorrelation adjustment per Section 5.2."""

    def test_no_autocorrelation(self):
        """Test with no significant autocorrelation."""
        returns = np.random.randn(100)
        adjustment = _compute_newey_west_adjustment(returns, 100)

        assert adjustment >= 1.0

    def test_positive_autocorrelation(self):
        """Test with positive autocorrelation (trend persistence)."""
        returns = np.cumsum(np.random.randn(100)) / 10
        adjustment = _compute_newey_west_adjustment(returns, 100)

        assert adjustment >= 1.0

    def test_small_sample(self):
        """Test with sample size too small for Ljung-Box."""
        returns = np.array([1.0, 2.0])
        adjustment = _compute_newey_west_adjustment(returns, 2)

        assert adjustment == 1.0


class TestStructuralBlocking:
    """Test structural blocking per Section 6."""

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_regime_not_blocked(self, mock_db_path, temp_db):
        """Test regime that is not structurally blocked."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        result = _is_structurally_blocked("trending_high_vol", conn)
        conn.close()

        assert result is False

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_regime_blocked(self, mock_db_path, temp_db):
        """Test regime that is structurally blocked."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO regime_blocks (regime, is_active, reason) VALUES (?, 1, ?)",
            ("choppy_low_vol", "API rate limits")
        )
        conn.commit()

        result = _is_structurally_blocked("choppy_low_vol", conn)
        conn.close()

        assert result is True

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_regime_blocked_inactive(self, mock_db_path, temp_db):
        """Test regime with inactive block."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO regime_blocks (regime, is_active, reason) VALUES (?, 0, ?)",
            ("choppy_low_vol", "Previously blocked")
        )
        conn.commit()

        result = _is_structurally_blocked("choppy_low_vol", conn)
        conn.close()

        assert result is False


class TestDecisionRules:
    """Test decision rules per Section 6."""

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_insufficient_data_permits_execution(self, mock_db_path, temp_db):
        """Test N_r < 100 permits execution per Section 9."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        for i in range(50):
            _insert_trade(conn, "trending_high_vol", 100, 105, 95, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("trending_high_vol")

        assert decision.execution_permitted is True
        assert decision.sizing_multiplier == 1.0
        assert decision.statistical_metadata["sample_size"] == 50
        assert decision.statistical_metadata["reason"] == "insufficient_data"

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_exactly_100_triggers_dynamic_review(self, mock_db_path, temp_db):
        """Test N_r = 100 exactly triggers dynamic review."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            _insert_trade(conn, "trending_high_vol", 100, 105, 95, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("trending_high_vol")

        assert decision.execution_permitted is True
        assert decision.statistical_metadata["sample_size"] == 100
        assert "lci" in decision.statistical_metadata
        assert "uci" in decision.statistical_metadata

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_uci_negative_blocks_execution(self, mock_db_path, temp_db):
        """Test UCI_r < 0 blocks execution per Section 6 Rule A."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            _insert_trade(conn, "choppy_low_vol", 100, 95, 105, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("choppy_low_vol")

        assert decision.execution_permitted is False
        assert decision.sizing_multiplier == 0.0
        assert decision.block_reason == "uci_negative"
        assert decision.statistical_metadata["uci"] < 0.0

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_lci_negative_restricts_sizing(self, mock_db_path, temp_db):
        """Test LCI_r < 0 restricts sizing per Section 6 Rule B."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        # Create distribution: mean +0.02R with high variance
        # 70 small wins (+0.2R each) and 30 larger losses (-0.4R each)
        # Mean = (70*0.2 - 30*0.4)/100 = +0.02R
        for i in range(70):
            _insert_trade(conn, "mixed_regime", 100, 101, 95, "LONG")  # +0.2R
        for i in range(30):
            _insert_trade(conn, "mixed_regime", 100, 98, 95, "LONG")   # -0.4R
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("mixed_regime")

        assert decision.execution_permitted is True
        assert 0.1 <= decision.sizing_multiplier < 1.0
        assert decision.statistical_metadata["lci"] < 0.0
        assert decision.statistical_metadata["uci"] >= 0.0

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_positive_ev_permits_full_sizing(self, mock_db_path, temp_db):
        """Test LCI_r >= 0 permits full sizing."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            _insert_trade(conn, "trending_high_vol", 100, 110, 95, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("trending_high_vol")

        assert decision.execution_permitted is True
        assert decision.sizing_multiplier == 1.0
        assert decision.statistical_metadata["lci"] >= 0.0
        assert decision.statistical_metadata["uci"] > 0.0

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_structural_block_overrides_statistics(self, mock_db_path, temp_db):
        """Test structural block overrides positive statistics."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO regime_blocks (regime, is_active, reason) VALUES (?, 1, ?)",
            ("trending_high_vol", "System design limit")
        )
        for i in range(100):
            _insert_trade(conn, "trending_high_vol", 100, 110, 95, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("trending_high_vol")

        assert decision.execution_permitted is False
        assert decision.sizing_multiplier == 0.0
        assert decision.block_reason == "structural_block"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_no_trades_for_regime(self, mock_db_path, temp_db):
        """Test regime with no historical trades."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        decision = evaluate_regime_execution_policy("unknown_regime")

        assert decision.execution_permitted is True
        assert decision.sizing_multiplier == 1.0

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_exactly_nmin_trades(self, mock_db_path, temp_db):
        """Test exactly N_min = 100 trades."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            _insert_trade(conn, "regime_100", 100, 105, 98, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("regime_100")

        assert decision.statistical_metadata["sample_size"] == 100
        assert "lci" in decision.statistical_metadata

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_zero_initial_risk_excluded(self, mock_db_path, temp_db):
        """Test trades with zero initial risk are excluded."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        for i in range(100):
            _insert_trade(conn, "test_regime", 100, 100, 100, "LONG")
        conn.commit()
        conn.close()

        decision = evaluate_regime_execution_policy("test_regime")

        assert decision.statistical_metadata["sample_size"] == 0


class TestRMultipleCalculation:
    """Test R-multiple calculation per Section 4."""

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_long_winning_trade(self, mock_db_path, temp_db):
        """Test R-multiple for winning LONG trade."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        _insert_trade(conn, "test", entry=100, exit_price=105, sl=95, direction="LONG")
        conn.commit()

        returns = _load_regime_trade_returns("test", conn)
        conn.close()

        assert len(returns) == 1
        assert returns[0] == pytest.approx(1.0, abs=0.01)

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_short_winning_trade(self, mock_db_path, temp_db):
        """Test R-multiple for winning SHORT trade."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        _insert_trade(conn, "test", entry=100, exit_price=95, sl=105, direction="SHORT")
        conn.commit()

        returns = _load_regime_trade_returns("test", conn)
        conn.close()

        assert len(returns) == 1
        assert returns[0] == pytest.approx(1.0, abs=0.01)

    @patch('ml_service.trading.regime_execution_policy._DB_PATH')
    def test_long_losing_trade(self, mock_db_path, temp_db):
        """Test R-multiple for losing LONG trade."""
        mock_db_path.__str__ = lambda _: str(temp_db)
        mock_db_path.parent.mkdir = lambda **kwargs: None

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        _insert_trade(conn, "test", entry=100, exit_price=95, sl=95, direction="LONG")
        conn.commit()

        returns = _load_regime_trade_returns("test", conn)
        conn.close()

        assert len(returns) == 1
        assert returns[0] == pytest.approx(-1.0, abs=0.01)
