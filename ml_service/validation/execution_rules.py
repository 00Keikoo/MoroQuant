"""Execution Validation Rules.

Deterministic validation rules for paper trading execution metrics.
Each rule validates a specific invariant that must hold for all closed positions.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from ml_service.services.execution_intelligence import ExecutionClassification


@dataclass
class ValidationFailure:
    """Single validation failure record."""

    position_id: int
    rule_violated: str
    expected: str
    actual: str
    severity: str


KNOWN_EXIT_REASONS = {"TP_HIT", "SL_HIT", "EXPIRED", "MANUAL_CLOSE"}
KNOWN_STATUSES = {"OPEN", "TP_HIT", "SL_HIT", "EXPIRED", "MANUAL_CLOSE"}
KNOWN_CLASSIFICATIONS = {
    "MODEL_CORRECT_EXECUTION_CORRECT",
    "MODEL_CORRECT_EXECUTION_WEAK",
    "MODEL_WEAK_EXECUTION_CORRECT",
    "MODEL_WEAK_EXECUTION_WEAK",
    "UNKNOWN",
}


def rule_mae_non_positive(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 1: MAE <= 0 (Maximum Adverse Excursion must be non-positive)."""
    mae = position.get("mae")
    if mae is None:
        return None

    if mae > 0:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="MAE_NON_POSITIVE",
            expected="MAE <= 0",
            actual=f"MAE = {mae}",
            severity="ERROR",
        )
    return None


def rule_mfe_non_negative(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 2: MFE >= 0 (Maximum Favorable Excursion must be non-negative)."""
    mfe = position.get("mfe")
    if mfe is None:
        return None

    if mfe < 0:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="MFE_NON_NEGATIVE",
            expected="MFE >= 0",
            actual=f"MFE = {mfe}",
            severity="ERROR",
        )
    return None


def rule_mae_timestamp_exists(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 3: MAE timestamp must exist if MAE changed from initial."""
    mae = position.get("mae")
    mae_timestamp = position.get("mae_timestamp")

    if mae is not None and mae != 0.0 and mae_timestamp is None:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="MAE_TIMESTAMP_MISSING",
            expected="mae_timestamp exists when MAE changed",
            actual="mae_timestamp is NULL",
            severity="WARNING",
        )
    return None


def rule_mfe_timestamp_exists(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 4: MFE timestamp must exist if MFE changed from initial."""
    mfe = position.get("mfe")
    mfe_timestamp = position.get("mfe_timestamp")

    if mfe is not None and mfe != 0.0 and mfe_timestamp is None:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="MFE_TIMESTAMP_MISSING",
            expected="mfe_timestamp exists when MFE changed",
            actual="mfe_timestamp is NULL",
            severity="WARNING",
        )
    return None


def rule_opened_before_closed(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 5: opened_at < closed_at."""
    opened_at = position.get("opened_at")
    closed_at = position.get("closed_at")

    if opened_at is None or closed_at is None:
        return None

    try:
        opened = datetime.strptime(opened_at.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
        closed = datetime.strptime(closed_at.replace("Z", ""), "%Y-%m-%d %H:%M:%S")

        if opened >= closed:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="OPENED_BEFORE_CLOSED",
                expected="opened_at < closed_at",
                actual=f"opened_at={opened_at}, closed_at={closed_at}",
                severity="ERROR",
            )
    except (ValueError, AttributeError):
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="TIMESTAMP_PARSE_ERROR",
            expected="Valid ISO timestamps",
            actual=f"opened_at={opened_at}, closed_at={closed_at}",
            severity="ERROR",
        )

    return None


def rule_hold_time_positive(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 6: Hold time > 0."""
    opened_at = position.get("opened_at")
    closed_at = position.get("closed_at")

    if opened_at is None or closed_at is None:
        return None

    try:
        opened = datetime.strptime(opened_at.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
        closed = datetime.strptime(closed_at.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
        hold_seconds = (closed - opened).total_seconds()

        if hold_seconds <= 0:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="HOLD_TIME_POSITIVE",
                expected="hold_time > 0",
                actual=f"hold_time = {hold_seconds}s",
                severity="ERROR",
            )
    except (ValueError, AttributeError):
        pass

    return None


def rule_profit_capture_ratio_bounds(
    position: Dict[str, Any]
) -> Optional[ValidationFailure]:
    """Rule 7: 0 <= PCR <= 1, if MFE == 0 then PCR must be NULL or 0."""
    pcr = position.get("profit_capture_ratio")
    mfe = position.get("mfe")

    if pcr is None:
        return None

    if math.isnan(pcr) or math.isinf(pcr):
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="PCR_INVALID_VALUE",
            expected="PCR is finite number",
            actual=f"PCR = {pcr}",
            severity="ERROR",
        )

    if pcr < 0 or pcr > 1:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="PCR_OUT_OF_BOUNDS",
            expected="0 <= PCR <= 1",
            actual=f"PCR = {pcr}",
            severity="ERROR",
        )

    if mfe is not None and abs(mfe) < 1e-9:
        if pcr != 0:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="PCR_DIVIDE_BY_ZERO",
                expected="PCR = 0 when MFE = 0",
                actual=f"PCR = {pcr}, MFE = {mfe}",
                severity="ERROR",
            )

    return None


def rule_trailing_consistency(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 8: if trailing_stop_activated == 1 then sl_move_count >= 1."""
    trailing_activated = position.get("trailing_stop_activated")
    sl_move_count = position.get("sl_move_count")

    if trailing_activated == 1:
        if sl_move_count is None or sl_move_count < 1:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="TRAILING_INCONSISTENCY",
                expected="sl_move_count >= 1 when trailing_stop_activated = 1",
                actual=f"sl_move_count = {sl_move_count}",
                severity="ERROR",
            )

    return None


def rule_break_even_consistency(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 9: if break_even_triggered == 1 then sl_move_count must indicate modification."""
    break_even_triggered = position.get("break_even_triggered")
    sl_move_count = position.get("sl_move_count")

    if break_even_triggered == 1:
        if sl_move_count is None or sl_move_count < 1:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="BREAK_EVEN_INCONSISTENCY",
                expected="sl_move_count >= 1 when break_even_triggered = 1",
                actual=f"sl_move_count = {sl_move_count}",
                severity="WARNING",
            )

    return None


def rule_execution_classification_valid(
    position: Dict[str, Any]
) -> Optional[ValidationFailure]:
    """Rule 10: Execution classification must be one of known values."""
    from ml_service.services.execution_intelligence import classify_trade_execution

    classification = classify_trade_execution(
        mfe=position.get("mfe"),
        mae=position.get("mae"),
        profit_capture_ratio=position.get("profit_capture_ratio"),
        realized_pnl=position.get("realized_pnl"),
        direction=position.get("direction", "LONG"),
        confidence=position.get("confidence"),
    )

    if classification not in KNOWN_CLASSIFICATIONS:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="INVALID_EXECUTION_CLASSIFICATION",
            expected=f"One of {KNOWN_CLASSIFICATIONS}",
            actual=f"classification = {classification}",
            severity="ERROR",
        )

    return None


def rule_exit_reason_valid(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 11: Exit reason must belong to known enum."""
    exit_reason = position.get("final_exit_reason")

    if exit_reason is None:
        return None

    if exit_reason not in KNOWN_EXIT_REASONS:
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="INVALID_EXIT_REASON",
            expected=f"One of {KNOWN_EXIT_REASONS}",
            actual=f"exit_reason = {exit_reason}",
            severity="ERROR",
        )

    return None


def rule_no_impossible_values(position: Dict[str, Any]) -> Optional[ValidationFailure]:
    """Rule 12: No impossible values (NaN, inf, out-of-bounds)."""
    confidence = position.get("confidence")
    prob_short = position.get("prob_short")
    prob_neutral = position.get("prob_neutral")
    prob_long = position.get("prob_long")

    if confidence is not None:
        if math.isnan(confidence) or math.isinf(confidence):
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="CONFIDENCE_INVALID",
                expected="confidence is finite number",
                actual=f"confidence = {confidence}",
                severity="ERROR",
            )
        if confidence < 0 or confidence > 100:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="CONFIDENCE_OUT_OF_BOUNDS",
                expected="0 <= confidence <= 100",
                actual=f"confidence = {confidence}",
                severity="ERROR",
            )

    probs = [p for p in [prob_short, prob_neutral, prob_long] if p is not None]
    if len(probs) == 3:
        for i, p in enumerate(probs):
            if math.isnan(p) or math.isinf(p):
                return ValidationFailure(
                    position_id=position["id"],
                    rule_violated="PROBABILITY_INVALID",
                    expected="probabilities are finite numbers",
                    actual=f"prob = {p}",
                    severity="ERROR",
                )

        prob_sum = sum(probs)
        if abs(prob_sum - 1.0) > 0.01:
            return ValidationFailure(
                position_id=position["id"],
                rule_violated="PROBABILITY_SUM_INVALID",
                expected="sum(probabilities) ≈ 1.0",
                actual=f"sum = {prob_sum}",
                severity="WARNING",
            )

    realized_pnl = position.get("realized_pnl")
    if realized_pnl is not None and (math.isnan(realized_pnl) or math.isinf(realized_pnl)):
        return ValidationFailure(
            position_id=position["id"],
            rule_violated="REALIZED_PNL_INVALID",
            expected="realized_pnl is finite number",
            actual=f"realized_pnl = {realized_pnl}",
            severity="ERROR",
        )

    return None


ALL_RULES = [
    rule_mae_non_positive,
    rule_mfe_non_negative,
    rule_mae_timestamp_exists,
    rule_mfe_timestamp_exists,
    rule_opened_before_closed,
    rule_hold_time_positive,
    rule_profit_capture_ratio_bounds,
    rule_trailing_consistency,
    rule_break_even_consistency,
    rule_execution_classification_valid,
    rule_exit_reason_valid,
    rule_no_impossible_values,
]
