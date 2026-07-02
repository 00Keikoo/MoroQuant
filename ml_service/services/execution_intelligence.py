"""Execution Intelligence Service.

Deterministic trade classification for quantitative research.
Separates model quality from execution quality using empirical metrics.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Literal, Optional

from utils.logger import get_logger

logger = get_logger()

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"

ExecutionClassification = Literal[
    "MODEL_CORRECT_EXECUTION_CORRECT",
    "MODEL_CORRECT_EXECUTION_WEAK",
    "MODEL_WEAK_EXECUTION_CORRECT",
    "MODEL_WEAK_EXECUTION_WEAK",
    "UNKNOWN",
]


def _get_connection():
    """Get database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def classify_trade_execution(
    mfe: Optional[float],
    mae: Optional[float],
    profit_capture_ratio: Optional[float],
    realized_pnl: Optional[float],
    direction: str,
    confidence: Optional[int],
) -> ExecutionClassification:
    """Classify a single closed trade using deterministic rules.

    Model quality:
    - Correct: MFE > 2% (model predicted profitable direction)
    - Weak: MFE <= 2% (model direction was wrong or marginal)

    Execution quality:
    - Correct: Profit capture ratio > 0.5 (captured >50% of MFE)
    - Weak: Profit capture ratio <= 0.5 (poor capture or stopped out)

    Returns UNKNOWN if insufficient empirical data.
    """
    if mfe is None or mae is None or realized_pnl is None:
        return "UNKNOWN"

    mfe_threshold = 0.02
    pcr_threshold = 0.5

    # Model quality: did the model predict a profitable direction?
    model_correct = mfe > mfe_threshold

    # Execution quality: did we capture the opportunity?
    if model_correct:
        # Model was correct: evaluate profit capture
        if profit_capture_ratio is not None and mfe > 0.01:
            execution_correct = profit_capture_ratio > pcr_threshold
        else:
            execution_correct = realized_pnl is not None and realized_pnl > 0
    else:
        # Model was weak: evaluate defensive execution (loss minimization)
        execution_correct = realized_pnl is not None and realized_pnl >= 0

    # Deterministic classification
    if model_correct and execution_correct:
        return "MODEL_CORRECT_EXECUTION_CORRECT"
    elif model_correct and not execution_correct:
        return "MODEL_CORRECT_EXECUTION_WEAK"
    elif not model_correct and execution_correct:
        return "MODEL_WEAK_EXECUTION_CORRECT"
    else:
        return "MODEL_WEAK_EXECUTION_WEAK"


def compute_execution_classifications() -> Dict[ExecutionClassification, int]:
    """Compute execution classification counts for all closed positions.

    Returns a dict mapping classification to count.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT mae, mfe, profit_capture_ratio, realized_pnl, direction, confidence
            FROM paper_positions
            WHERE status != 'OPEN'
            """
        ).fetchall()
    finally:
        conn.close()

    classifications: Dict[ExecutionClassification, int] = {
        "MODEL_CORRECT_EXECUTION_CORRECT": 0,
        "MODEL_CORRECT_EXECUTION_WEAK": 0,
        "MODEL_WEAK_EXECUTION_CORRECT": 0,
        "MODEL_WEAK_EXECUTION_WEAK": 0,
        "UNKNOWN": 0,
    }

    for r in rows:
        classification = classify_trade_execution(
            mfe=r["mfe"],
            mae=r["mae"],
            profit_capture_ratio=r["profit_capture_ratio"],
            realized_pnl=r["realized_pnl"],
            direction=r["direction"],
            confidence=r["confidence"],
        )
        classifications[classification] += 1

    return classifications


def compute_execution_quality_score() -> float:
    """Compute overall Execution Quality Score (0-100).

    Weighted combination of:
    - Model-correct trades with good execution (high weight)
    - Model-weak trades with defensive execution (medium weight)
    - Overall profit capture efficiency (medium weight)

    Returns 0.0 if insufficient data.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT mae, mfe, profit_capture_ratio, realized_pnl, direction, confidence
            FROM paper_positions
            WHERE status != 'OPEN'
            """
        ).fetchall()
    finally:
        conn.close()

    if len(rows) < 5:
        return 0.0

    classifications = {
        "MODEL_CORRECT_EXECUTION_CORRECT": 0,
        "MODEL_CORRECT_EXECUTION_WEAK": 0,
        "MODEL_WEAK_EXECUTION_CORRECT": 0,
        "MODEL_WEAK_EXECUTION_WEAK": 0,
        "UNKNOWN": 0,
    }

    profit_captures = []
    for r in rows:
        classification = classify_trade_execution(
            mfe=r["mfe"],
            mae=r["mae"],
            profit_capture_ratio=r["profit_capture_ratio"],
            realized_pnl=r["realized_pnl"],
            direction=r["direction"],
            confidence=r["confidence"],
        )
        classifications[classification] += 1

        if r["profit_capture_ratio"] is not None:
            profit_captures.append(r["profit_capture_ratio"])

    total_trades = len(rows)
    if total_trades == 0:
        return 0.0

    # Component 1: Model-correct execution rate (0-40 points)
    model_correct_total = (
        classifications["MODEL_CORRECT_EXECUTION_CORRECT"]
        + classifications["MODEL_CORRECT_EXECUTION_WEAK"]
    )
    if model_correct_total > 0:
        model_correct_exec_rate = (
            classifications["MODEL_CORRECT_EXECUTION_CORRECT"] / model_correct_total
        )
        component_1 = model_correct_exec_rate * 40.0
    else:
        component_1 = 0.0

    # Component 2: Defensive execution rate (0-30 points)
    model_weak_total = (
        classifications["MODEL_WEAK_EXECUTION_CORRECT"]
        + classifications["MODEL_WEAK_EXECUTION_WEAK"]
    )
    if model_weak_total > 0:
        defensive_exec_rate = (
            classifications["MODEL_WEAK_EXECUTION_CORRECT"] / model_weak_total
        )
        component_2 = defensive_exec_rate * 30.0
    else:
        component_2 = 15.0

    # Component 3: Average profit capture ratio (0-30 points)
    if profit_captures:
        avg_pcr = sum(profit_captures) / len(profit_captures)
        component_3 = avg_pcr * 30.0
    else:
        component_3 = 0.0

    eqs = component_1 + component_2 + component_3
    return round(max(0.0, min(100.0, eqs)), 1)
