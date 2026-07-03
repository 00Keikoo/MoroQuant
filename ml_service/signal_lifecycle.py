"""Signal lifecycle engine — evaluates whether a signal is still active.

Status transitions:
    ACTIVE  → TP_HIT   (price hit take-profit)
    ACTIVE  → SL_HIT   (price hit stop-loss)
    ACTIVE  → EXPIRED  (valid_until passed)

Once a signal reaches a terminal state (TP_HIT, SL_HIT, EXPIRED) it
never reverts to ACTIVE.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ml_service.utils.logger import get_logger
from ml_service.data.database import get_database

logger = get_logger(__name__)

# Status constants
ACTIVE = "ACTIVE"
TP_HIT = "TP_HIT"
SL_HIT = "SL_HIT"
EXPIRED = "EXPIRED"

_TERMINAL_STATES = {TP_HIT, SL_HIT, EXPIRED}


def evaluate_signal_status(
    signal: Dict,
    current_price: Optional[float] = None,
    now: Optional[datetime] = None,
) -> Tuple[str, str]:
    """Evaluate the current status of a signal.

    Args:
        signal: Signal dict with keys: direction, take_profit, stop_loss,
                valid_until, signal_status.
        current_price: Live market price. If None and status is ACTIVE,
            returns ACTIVE (can't evaluate TP/SL without price).
        now: Override clock (for testing). Defaults to datetime.now().

    Returns:
        (status, reason) tuple.
            status  — ACTIVE, TP_HIT, SL_HIT, or EXPIRED
            reason  — human-readable explanation
    """
    if now is None:
        now = datetime.now()

    current_status = signal.get("signal_status", ACTIVE)

    # Never revert a terminal state
    if current_status in _TERMINAL_STATES:
        return current_status, f"terminal ({current_status})"

    direction = signal.get("direction", "neutral")
    tp = signal.get("take_profit")
    sl = signal.get("stop_loss")
    valid_until_str = signal.get("valid_until")

    # ── Price-based evaluation (only for directional signals) ─────
    if current_price is not None and tp is not None and sl is not None:
        if direction == "long":
            if current_price <= sl:
                return SL_HIT, f"price {current_price} <= stop_loss {sl}"
            if current_price >= tp:
                return TP_HIT, f"price {current_price} >= take_profit {tp}"

        elif direction == "short":
            if current_price >= sl:
                return SL_HIT, f"price {current_price} >= stop_loss {sl}"
            if current_price <= tp:
                return TP_HIT, f"price {current_price} <= take_profit {tp}"

    # ── Time-based expiry ─────────────────────────────────────────────
    if valid_until_str:
        try:
            valid_until = datetime.fromisoformat(valid_until_str)
            if now >= valid_until:
                return EXPIRED, f"expired at {valid_until_str}"
        except (ValueError, TypeError):
            logger.warning(f"Invalid valid_until format: {valid_until_str}")

    return ACTIVE, "within TP/SL bounds and not expired"


def bulk_update_signal_statuses(
    items: List[Dict],
) -> int:
    """Evaluate and persist status changes for multiple signals.

    Each item must contain:
        - signal: dict with signal fields (including 'signal_id')
        - current_price: float or None

    Returns:
        Number of status transitions persisted.
    """
    db = get_database()
    updated = 0

    with db.get_connection() as conn:
        cursor = conn.cursor()

        for item in items:
            signal = item.get("signal", {})
            current_price = item.get("current_price")
            signal_id = signal.get("signal_id")

            if not signal_id:
                continue

            new_status, reason = evaluate_signal_status(signal, current_price)
            old_status = signal.get("signal_status", ACTIVE)

            if new_status != old_status:
                cursor.execute(
                    """
                    UPDATE signals
                    SET signal_status = ?,
                        status_updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_status, signal_id),
                )
                updated += 1
                logger.info(
                    f"Signal {signal_id} ({signal.get('symbol')} {signal.get('timeframe')}): "
                    f"{old_status} → {new_status} ({reason})"
                )

        conn.commit()

    return updated
