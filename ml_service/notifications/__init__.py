"""Notifications package for MoroQuant.

Currently provides Telegram signal alerts. Additional channels (e.g. Discord,
webhooks) can be added here.
"""

from .telegram_notifier import (
    format_signal_message,
    is_configured,
    send_signal_alert,
    send_telegram_message,
)

__all__ = [
    "format_signal_message",
    "is_configured",
    "send_signal_alert",
    "send_telegram_message",
]
