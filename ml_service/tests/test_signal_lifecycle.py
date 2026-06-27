"""Unit tests for signal_lifecycle.evaluate_signal_status()."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure ml_service root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from signal_lifecycle import evaluate_signal_status, ACTIVE, TP_HIT, SL_HIT, EXPIRED


def make_signal(direction="long", tp=110.0, sl=90.0, valid_until=None, status=ACTIVE):
    """Build a minimal signal dict for testing."""
    return {
        "direction": direction,
        "take_profit": tp,
        "stop_loss": sl,
        "valid_until": valid_until,
        "signal_status": status,
    }


# ─── LONG scenarios ─────────────────────────────────────────────────

def test_long_active():
    status, reason = evaluate_signal_status(make_signal(direction="long"), current_price=100.0)
    assert status == ACTIVE, f"Expected ACTIVE, got {status}"
    print("✓ LONG active (price within TP/SL)")


def test_long_sl_hit():
    status, reason = evaluate_signal_status(
        make_signal(direction="long", tp=110.0, sl=95.0),
        current_price=94.5,
    )
    assert status == SL_HIT, f"Expected SL_HIT, got {status}"
    assert "94.5" in reason and "95" in reason
    print("✓ LONG SL hit (price <= stop_loss)")


def test_long_tp_hit():
    status, reason = evaluate_signal_status(
        make_signal(direction="long", tp=110.0, sl=90.0),
        current_price=110.5,
    )
    assert status == TP_HIT, f"Expected TP_HIT, got {status}"
    assert "110.5" in reason and "110" in reason
    print("✓ LONG TP hit (price >= take_profit)")


def test_long_expired():
    expired_at = (datetime.now() - timedelta(hours=1)).isoformat()
    status, reason = evaluate_signal_status(
        make_signal(direction="long", valid_until=expired_at),
        current_price=100.0,
    )
    assert status == EXPIRED, f"Expected EXPIRED, got {status}"
    print("✓ LONG expired (now >= valid_until)")


# ─── SHORT scenarios ────────────────────────────────────────────────

def test_short_active():
    # SHORT: TP below entry, SL above entry — price at entry should be ACTIVE
    status, reason = evaluate_signal_status(
        make_signal(direction="short", tp=90.0, sl=110.0),
        current_price=100.0,
    )
    assert status == ACTIVE, f"Expected ACTIVE, got {status}"
    print("✓ SHORT active (price within TP/SL)")


def test_short_sl_hit():
    # SHORT: stop_loss above entry, take_profit below entry
    status, reason = evaluate_signal_status(
        make_signal(direction="short", tp=90.0, sl=110.0),
        current_price=110.5,
    )
    assert status == SL_HIT, f"Expected SL_HIT, got {status}"
    assert "110.5" in reason
    print("✓ SHORT SL hit (price >= stop_loss)")


def test_short_tp_hit():
    status, reason = evaluate_signal_status(
        make_signal(direction="short", tp=90.0, sl=110.0),
        current_price=89.5,
    )
    assert status == TP_HIT, f"Expected TP_HIT, got {status}"
    assert "89.5" in reason
    print("✓ SHORT TP hit (price <= take_profit)")


def test_short_expired():
    expired_at = (datetime.now() - timedelta(hours=2)).isoformat()
    status, reason = evaluate_signal_status(
        make_signal(direction="short", tp=90.0, sl=110.0, valid_until=expired_at),
        current_price=100.0,
    )
    assert status == EXPIRED, f"Expected EXPIRED, got {status}"
    print("✓ SHORT expired (now >= valid_until)")


# ─── NEUTRAL scenarios ───────────────────────────────────────────────

def test_neutral_active():
    future = (datetime.now() + timedelta(hours=6)).isoformat()
    status, reason = evaluate_signal_status(
        make_signal(direction="neutral", valid_until=future),
        current_price=100.0,
    )
    assert status == ACTIVE, f"Expected ACTIVE, got {status}"
    print("✓ NEUTRAL active (within valid_until)")


def test_neutral_expired():
    expired_at = (datetime.now() - timedelta(minutes=30)).isoformat()
    status, reason = evaluate_signal_status(
        make_signal(direction="neutral", valid_until=expired_at),
        current_price=100.0,
    )
    assert status == EXPIRED, f"Expected EXPIRED, got {status}"
    print("✓ NEUTRAL expired")


# ─── Edge cases ────────────────────────────────────────────────────

def test_no_price_stays_active():
    """Without current_price, can't evaluate TP/SL — stays ACTIVE."""
    status, _ = evaluate_signal_status(make_signal(direction="long"))
    assert status == ACTIVE
    print("✓ No price → ACTIVE (graceful degradation)")


def test_terminal_never_reverts():
    """A TP_HIT signal should never go back to ACTIVE even if price reverts."""
    status, reason = evaluate_signal_status(
        make_signal(direction="long", status=TP_HIT),
        current_price=100.0,
    )
    assert status == TP_HIT, f"Terminal TP_HIT should not revert, got {status}"
    print("✓ Terminal state never reverts")


def test_expired_signal_no_revert():
    """An EXPIRED signal should stay EXPIRED even if price is back in range."""
    status, _ = evaluate_signal_status(
        make_signal(direction="long", status=EXPIRED),
        current_price=100.0,
    )
    assert status == EXPIRED
    print("✓ EXPIRED terminal state preserved")


def test_invalid_valid_until_graceful():
    """Malformed valid_until should not crash."""
    status, _ = evaluate_signal_status(
        make_signal(direction="long", valid_until="not-a-date"),
        current_price=100.0,
    )
    assert status == ACTIVE
    print("✓ Invalid valid_until → graceful ACTIVE")


def test_sl_before_tp_priority():
    """SL should trigger even if TP would also be hit (edge case)."""
    # For LONG, SL check comes first in the code — verify it triggers
    status, _ = evaluate_signal_status(
        make_signal(direction="long", tp=110.0, sl=95.0),
        current_price=93.0,
    )
    assert status == SL_HIT
    print("✓ SL priority over TP (LONG)")


# ─── Run all ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_long_active, test_long_sl_hit, test_long_tp_hit, test_long_expired,
        test_short_active, test_short_sl_hit, test_short_tp_hit, test_short_expired,
        test_neutral_active, test_neutral_expired,
        test_no_price_stays_active, test_terminal_never_reverts,
        test_expired_signal_no_revert, test_invalid_valid_until_graceful,
        test_sl_before_tp_priority,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
