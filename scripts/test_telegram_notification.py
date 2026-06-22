#!/usr/bin/env python3
"""Health-check script for the MoroQuant Telegram signal alert.

Sends a representative *sample* signal through the same code path the
scheduler uses, so you can verify end-to-end that:

  1. TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are correctly configured.
  2. The Telegram Bot API accepts the message.
  3. The Markdown formatting renders as expected in the Telegram client.

The script NEVER crashes:
  * If Telegram is not configured, it prints a clear WARNING and exits 0
    (so it can be used in smoke-test pipelines without failing CI).
  * If the send fails, it prints the Telegram API error and exits 0.

Usage:
    python scripts/test_telegram_notification.py

Run from the repo root. The script adds ``ml_service`` to sys.path so the
``notifications`` package and its ``utils.logger`` dependency resolve.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make ml_service importable regardless of the current working directory.
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent / "ml_service"
sys.path.insert(0, str(ML_SERVICE_DIR))

from notifications.telegram_notifier import (  # noqa: E402  (after sys.path tweak)
    is_configured,
    send_signal_alert,
)
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


# A sample signal shaped exactly like the dict returned by
# predictor.generate_signal(). Uses the field names that format_signal_message
# reads; DB-style keys (entry_price) are also honoured.
SAMPLE_SIGNAL = {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "direction": "long",
    "confidence": 78,
    "mtf_alignment": "AGREE",
    "regime": "trending",
    "price": 102450.0,
    "take_profit": 105800.0,
    "stop_loss": 100900.0,
    "raw_probability_max": 0.69,
    "calibrated_probability_max": 0.74,
    "model_version": "BTCUSDT_1h_xgboost_20260621_071847.pkl",
    "generated_at": "2026-06-22T18:00:00",
}


def main() -> int:
    logger.info("Sending sample Telegram signal alert...")

    if not is_configured():
        logger.warning(
            "Telegram is not configured. Set TELEGRAM_BOT_TOKEN and "
            "TELEGRAM_CHAT_ID in your environment or .env file. "
            "See TELEGRAM_SETUP.md for instructions."
        )
        print(
            "\nSample alert was NOT delivered: Telegram is not configured.\n"
            "This is expected in environments without a bot token. Exiting 0."
        )
        return 0

    success = send_signal_alert(SAMPLE_SIGNAL)

    if success:
        print("\nSample alert delivered successfully. Check your Telegram chat.")
    else:
        print(
            "\nSample alert was NOT delivered. "
            "Review the ERROR/WARNING lines above for details (common causes: "
            "wrong chat_id, bot not added to the chat, revoked token)."
        )

    # Intentionally always exit 0: this is a health check, not a gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
