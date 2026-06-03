"""Logging configuration for ML trading system."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str = "ml_trading",
    log_file: str = "storage/logs/ml_service.log",
    level: str = "INFO",
    max_bytes: int = 10485760,
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure logger with both file and console output.

    Args:
        name: Logger name
        log_file: Path to log file (relative to project root)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        max_bytes: Max size of log file before rotation (default 10MB)
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if logger.handlers:
        return logger

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "ml_trading") -> logging.Logger:
    """Get existing logger instance."""
    return logging.getLogger(name)
