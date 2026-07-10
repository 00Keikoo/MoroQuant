"""Execution decisions audit logger.

Persists every execution attempt (ACCEPTED or REJECTED) to execution_decisions table.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from ml_service.utils.logger import get_logger

logger = get_logger()

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


# Rejection reason codes (map to return None paths in paper_broker.py)
class RejectReason:
    MODE_NOT_PAPER = "MODE_NOT_PAPER"
    NEUTRAL_SIGNAL = "NEUTRAL_SIGNAL"
    INVALID_DIRECTION = "INVALID_DIRECTION"
    MISSING_SYMBOL = "MISSING_SYMBOL"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    REGIME_BLOCK = "REGIME_BLOCK"
    LOW_EDGE = "LOW_EDGE"
    NO_PRICE = "NO_PRICE"
    COOLDOWN = "COOLDOWN"
    MAX_POSITIONS = "MAX_POSITIONS"
    DUPLICATE_POSITION = "DUPLICATE_POSITION"
    INVALID_QUANTITY = "INVALID_QUANTITY"


def _get_connection():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def log_execution_decision(
    decision: str,
    symbol: str,
    direction: Optional[str] = None,
    reason: Optional[str] = None,
    signal_id: Optional[int] = None,
    position_id: Optional[int] = None,
    confidence: Optional[int] = None,
    regime: Optional[str] = None,
    timeframe: Optional[str] = None,
    prob_short: Optional[float] = None,
    prob_neutral: Optional[float] = None,
    prob_long: Optional[float] = None,
    execution_edge: Optional[float] = None,
    signal_price: Optional[float] = None,
    execution_price: Optional[float] = None,
    slippage_pct: Optional[float] = None,
    execution_latency_ms: Optional[int] = None,
) -> Optional[int]:
    """Log an execution decision (ACCEPTED or REJECTED).

    Returns the inserted row ID, or None on failure.
    """
    if decision not in ("ACCEPTED", "REJECTED"):
        logger.warning(f"Invalid decision type: {decision}")
        return None

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO execution_decisions
                (symbol, direction, decision, reason, signal_id, position_id,
                 confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                 execution_edge, signal_price, execution_price, slippage_pct, execution_latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                direction,
                decision,
                reason,
                signal_id,
                position_id,
                confidence,
                regime,
                timeframe,
                prob_short,
                prob_neutral,
                prob_long,
                execution_edge,
                signal_price,
                execution_price,
                slippage_pct,
                execution_latency_ms,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Failed to log execution decision: {e}")
        return None
    finally:
        conn.close()
