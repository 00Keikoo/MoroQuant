#!/usr/bin/env python3
"""Verification script for signal lifecycle scheduler integration.

Demonstrates:
1. Expired signals (valid_until in past) → EXPIRED status
2. Active signals (valid_until in future) → remain ACTIVE
3. Legacy signals (valid_until IS NULL) → remain unchanged
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from ml_service.data.database import get_database
from ml_service.signal_lifecycle import bulk_update_signal_statuses
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()


def setup_test_signals():
    """Create test signals with different valid_until states."""
    db = get_database()

    now = datetime.now()
    past_time = (now - timedelta(hours=2)).isoformat()
    future_time = (now + timedelta(hours=2)).isoformat()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Clean up any existing test signals
        cursor.execute("DELETE FROM signals WHERE symbol = 'TEST_VERIFY'")

        # Test case 1: Expired signal (valid_until in past)
        cursor.execute(
            """
            INSERT INTO signals (
                symbol, timeframe, timestamp, direction, confidence,
                signal_status, valid_until, take_profit, stop_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ('TEST_VERIFY', '1h', int(now.timestamp() * 1000), 'long', 75,
             'ACTIVE', past_time, 50000.0, 45000.0)
        )
        expired_id = cursor.lastrowid

        # Test case 2: Future signal (valid_until in future)
        cursor.execute(
            """
            INSERT INTO signals (
                symbol, timeframe, timestamp, direction, confidence,
                signal_status, valid_until, take_profit, stop_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ('TEST_VERIFY', '4h', int(now.timestamp() * 1000), 'short', 80,
             'ACTIVE', future_time, 45000.0, 50000.0)
        )
        future_id = cursor.lastrowid

        # Test case 3: Legacy signal (valid_until IS NULL)
        cursor.execute(
            """
            INSERT INTO signals (
                symbol, timeframe, timestamp, direction, confidence,
                signal_status, valid_until, take_profit, stop_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ('TEST_VERIFY', '1d', int(now.timestamp() * 1000), 'long', 70,
             'ACTIVE', None, 50000.0, 45000.0)
        )
        legacy_id = cursor.lastrowid

        conn.commit()

    logger.info(f"Created test signals: expired={expired_id}, future={future_id}, legacy={legacy_id}")
    return expired_id, future_id, legacy_id


def verify_lifecycle():
    """Run signal lifecycle evaluation and verify results."""
    db = get_database()

    logger.info("=" * 80)
    logger.info("Signal Lifecycle Verification")
    logger.info("=" * 80)

    # Query ACTIVE signals (same logic as scheduler job)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, symbol, timeframe, direction, signal_status,
                   take_profit, stop_loss, valid_until
            FROM signals
            WHERE symbol = 'TEST_VERIFY'
              AND signal_status = 'ACTIVE'
              AND valid_until IS NOT NULL
            """
        )
        rows = cursor.fetchall()

    logger.info(f"Found {len(rows)} ACTIVE test signals with non-NULL valid_until")

    if not rows:
        logger.error("No test signals found for evaluation")
        return False

    # Build items for bulk update
    items = []
    for row in rows:
        signal = {
            'signal_id': row[0],
            'symbol': row[1],
            'timeframe': row[2],
            'direction': row[3],
            'signal_status': row[4],
            'take_profit': row[5],
            'stop_loss': row[6],
            'valid_until': row[7],
        }
        items.append({'signal': signal, 'current_price': None})

    # Evaluate lifecycle transitions
    updated = bulk_update_signal_statuses(items)
    logger.info(f"Lifecycle evaluation: {updated} status transitions")

    # Verify results
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT timeframe, signal_status, valid_until
            FROM signals
            WHERE symbol = 'TEST_VERIFY'
            ORDER BY timeframe
            """
        )
        results = cursor.fetchall()

    logger.info("\nVerification Results:")
    logger.info("-" * 80)

    success = True

    for row in results:
        timeframe, status, valid_until = row

        if timeframe == '1h':
            # Expired signal should be EXPIRED
            expected = 'EXPIRED'
            if status == expected:
                logger.info(f"✓ {timeframe}: {status} (valid_until={valid_until}) - PASS")
            else:
                logger.error(f"✗ {timeframe}: {status} (expected {expected}) - FAIL")
                success = False

        elif timeframe == '4h':
            # Future signal should remain ACTIVE
            expected = 'ACTIVE'
            if status == expected:
                logger.info(f"✓ {timeframe}: {status} (valid_until={valid_until}) - PASS")
            else:
                logger.error(f"✗ {timeframe}: {status} (expected {expected}) - FAIL")
                success = False

        elif timeframe == '1d':
            # Legacy signal should remain ACTIVE (not queried by scheduler)
            expected = 'ACTIVE'
            if status == expected and valid_until is None:
                logger.info(f"✓ {timeframe}: {status} (valid_until=NULL) - PASS")
            else:
                logger.error(f"✗ {timeframe}: {status} (valid_until={valid_until}) - FAIL")
                success = False

    logger.info("-" * 80)
    return success


def cleanup_test_signals():
    """Remove test signals."""
    db = get_database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM signals WHERE symbol = 'TEST_VERIFY'")
    logger.info("Test signals cleaned up")


if __name__ == '__main__':
    try:
        # Setup
        expired_id, future_id, legacy_id = setup_test_signals()

        # Verify
        success = verify_lifecycle()

        # Cleanup
        cleanup_test_signals()

        # Report
        logger.info("=" * 80)
        if success:
            logger.info("VERIFICATION PASSED: All test cases behaved correctly")
            sys.exit(0)
        else:
            logger.error("VERIFICATION FAILED: Some test cases did not behave as expected")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Verification script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
