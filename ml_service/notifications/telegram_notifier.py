"""Telegram notification module for MoroQuant signals.

Sends a formatted Markdown alert to a Telegram chat whenever a new ML
trading signal is generated and persisted.

Design principles (production-safe):
    * All public entry points are wrapped in try/except.
    * A missing configuration or a Telegram API failure must NEVER propagate
      to the caller. Signal generation always continues.
    * ``send_signal_alert`` returns a bool so callers can log the outcome
      without needing to handle exceptions.

Configuration (environment variables):
    TELEGRAM_BOT_TOKEN  - Bot API token issued by @BotFather
    TELEGRAM_CHAT_ID    - Target chat/channel id (numeric for users/groups,
                          or ``@channelname`` for public channels)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

# Load .env if python-dotenv is available so local dev "just works".
# Optional dependency: failure to load .env is non-fatal.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # dotenv not installed or .env missing -> rely on the real environment.
    pass

from utils.logger import get_logger

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"
TELEGRAM_SEND_MESSAGE_TIMEOUT = 10  # seconds


class TelegramConfigError(RuntimeError):
    """Raised internally when Telegram is not fully configured.

    This is deliberately NOT raised out of public functions; it is caught
    and converted into a logged WARNING + ``False`` return value so the
    scheduler is never interrupted.
    """


def _get_bot_token() -> Optional[str]:
    """Return the Telegram bot token from the environment, or None."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return token or None


def _get_chat_id() -> Optional[str]:
    """Return the Telegram chat id from the environment, or None."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return chat_id or None


def is_configured() -> bool:
    """Return True iff both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set."""
    return bool(_get_bot_token() and _get_chat_id())


def _require_config() -> tuple[str, str]:
    """Return (bot_token, chat_id), raising TelegramConfigError if unset."""
    token = _get_bot_token()
    chat_id = _get_chat_id()
    if not token or not chat_id:
        missing = [
            name
            for name, value in (
                ("TELEGRAM_BOT_TOKEN", token),
                ("TELEGRAM_CHAT_ID", chat_id),
            )
            if not value
        ]
        raise TelegramConfigError(
            "Telegram not configured: missing " + ", ".join(missing)
        )
    return token, chat_id


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------

def _fmt_price(value: Any) -> str:
    """Format a price-like value for display, tolerating None / bad input."""
    try:
        if value is None:
            return "N/A"
        f = float(value)
        # More precision for low-priced assets, matches predictor convention.
        return f"{f:.4f}" if f < 1.0 else f"{f:.2f}"
    except (TypeError, ValueError):
        return str(value) if value is not None else "N/A"


def _fmt_prob(value: Any) -> str:
    """Format a probability (0..1) for display."""
    try:
        return f"{float(value):.2f}" if value is not None else "N/A"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_direction(direction: Any) -> str:
    """Normalize a direction string to upper-case display form."""
    if not direction:
        return "N/A"
    return str(direction).upper()


def _fmt_regime(regime: Any) -> str:
    """Capitalize a regime label, tolerating None."""
    if not regime:
        return "Unknown"
    return str(regime).capitalize()


def _escape_markdown(text: str) -> str:
    """Escape characters that have special meaning in Telegram Markdown.

    Telegram's MarkdownV1 mode treats ``_``, ``*``, ``[``, ``]`` as markup.
    Our message intentionally avoids those characters in dynamic content,
    so this is a defensive escape for free-form fields (model_version,
    regime, etc.).
    """
    for char in ("_", "*", "[", "]", "`"):
        text = text.replace(char, f"\\{char}")
    return text


def format_signal_message(signal: Dict) -> str:
    """Build the Telegram Markdown message for a signal dict.

    Args:
        signal: Signal dictionary produced by ``predictor.generate_signal``
            (or a row rehydrated from the database). Missing keys are
            rendered as ``N/A`` so a partial dict never breaks formatting.

    Returns:
        Markdown-formatted string suitable for Telegram's ``sendMessage``.
    """
    symbol = _escape_markdown(str(signal.get("symbol", "UNKNOWN")))
    timeframe = str(signal.get("timeframe", "N/A"))

    direction = _fmt_direction(signal.get("direction"))
    confidence = signal.get("confidence")
    confidence_str = (
        f"{int(round(float(confidence)))}%"
        if confidence is not None
        else "N/A"
    )

    mtf = str(signal.get("mtf_alignment", "N/A")).upper()
    regime = _escape_markdown(_fmt_regime(signal.get("regime")))

    # Entry price may be stored under 'price' (fresh signal) or
    # 'entry_price' (DB row). Prefer 'price', fall back to 'entry_price'.
    entry = signal.get("price")
    if entry is None:
        entry = signal.get("entry_price")

    take_profit = signal.get("take_profit")
    stop_loss = signal.get("stop_loss")

    raw_prob = signal.get("raw_probability_max")
    calibrated_prob = signal.get("calibrated_probability_max")

    model_version = _escape_markdown(str(signal.get("model_version", "N/A")))

    generated_at = signal.get("generated_at")
    if generated_at:
        # Normalize ISO timestamp to a readable form ending in UTC.
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            generated_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            generated_str = str(generated_at)
    else:
        generated_str = "N/A"

    message = (
        "🚨 *MOROQUANT SIGNAL*\n"
        "\n"
        f"Symbol: {symbol}\n"
        f"Timeframe: {timeframe}\n"
        "\n"
        f"Direction: {direction}\n"
        f"Confidence: {confidence_str}\n"
        "\n"
        f"MTF Alignment: {mtf}\n"
        f"Regime: {regime}\n"
        "\n"
        f"Entry: {_fmt_price(entry)}\n"
        f"Take Profit: {_fmt_price(take_profit)}\n"
        f"Stop Loss: {_fmt_price(stop_loss)}\n"
        "\n"
        f"Raw Prob: {_fmt_prob(raw_prob)}\n"
        f"Calibrated Prob: {_fmt_prob(calibrated_prob)}\n"
        "\n"
        "Model Version:\n"
        f"{model_version}\n"
        "\n"
        f"Generated:\n{generated_str}"
    )
    return message


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def send_telegram_message(text: str) -> bool:
    """Send an arbitrary Markdown message to the configured Telegram chat.

    Returns:
        True if Telegram accepted the message, False otherwise. Never raises.
    """
    try:
        token, chat_id = _require_config()
    except TelegramConfigError as e:
        logger.warning(f"Telegram not configured, skipping alert: {e}")
        return False
    except Exception as e:  # defensive: never propagate to caller
        logger.warning(f"Telegram config check failed, skipping alert: {e}")
        return False

    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=TELEGRAM_SEND_MESSAGE_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram send failed (network error): {e}")
        return False
    except Exception as e:
        logger.error(f"Telegram send failed (unexpected error): {e}")
        return False

    if response.status_code == 200:
        return True

    # Non-200: try to surface Telegram's error description for diagnostics.
    description = "unknown"
    try:
        body = response.json()
        description = body.get("description", response.text[:200])
    except (ValueError, requests.exceptions.JSONDecodeError):
        description = response.text[:200]

    logger.error(
        f"Telegram send failed (HTTP {response.status_code}): {description}"
    )
    return False


def send_signal_alert(signal: Dict) -> bool:
    """Send a formatted signal alert to Telegram.

    This is the primary entry point used by ``scheduler.py`` after a signal
    is generated and persisted. It is guaranteed not to raise: any failure
    (missing config, network error, malformed signal) is logged and False
    is returned, so signal generation is never interrupted.

    Args:
        signal: Signal dictionary from ``predictor.generate_signal``.

    Returns:
        True if the alert was delivered to Telegram, False otherwise.
    """
    try:
        if not isinstance(signal, dict):
            logger.warning(
                f"Telegram alert skipped: expected dict signal, got {type(signal).__name__}"
            )
            return False

        message = format_signal_message(signal)
        success = send_telegram_message(message)

        if success:
            logger.info(
                f"Telegram alert sent: {signal.get('symbol')} "
                f"{signal.get('timeframe')} {signal.get('direction')}"
            )
        # failure path already logged inside send_telegram_message
        return success
    except Exception as e:
        # Absolute last-resort guard: signal generation must never fail
        # because of notifications.
        logger.error(f"Telegram alert failed (unexpected): {e}")
        return False
