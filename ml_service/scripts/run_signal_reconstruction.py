#!/usr/bin/env python3
"""Run legacy signal reconstruction and generate performance report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_service.analytics.signal_reconstruction import SignalReconstructor
from ml_service.utils.logger import get_logger

logger = get_logger()


def main():
    """Execute reconstruction process."""
    logger.info("=" * 60)
    logger.info("LEGACY SIGNAL RECONSTRUCTION - ESTIMATED PERFORMANCE")
    logger.info("=" * 60)

    reconstructor = SignalReconstructor()

    logger.info("Starting reconstruction of legacy signals...")
    stats = reconstructor.reconstruct_all_legacy_signals()

    logger.info("\n" + "=" * 60)
    logger.info("RECONSTRUCTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total signals processed: {stats['total']}")
    logger.info(f"Successfully reconstructed: {stats['reconstructed']}")
    logger.info(f"Skipped (neutral): {stats['skipped_neutral']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info("")
    logger.info("ESTIMATED OUTCOMES:")
    logger.info(f"  Wins: {stats['wins']}")
    logger.info(f"  Losses: {stats['losses']}")
    logger.info(f"  Timeouts: {stats['timeouts']}")

    if stats['reconstructed'] > 0:
        win_rate = (stats['wins'] / stats['reconstructed']) * 100
        logger.info(f"\nESTIMATED WIN RATE: {win_rate:.1f}%")

    logger.info("\nNOTE: All metrics are ESTIMATED based on historical OHLCV data")
    logger.info("      and standard TP/SL multipliers. Not actual performance.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
