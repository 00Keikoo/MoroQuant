"""Unit tests for the Telegram signal quality filter.

Verifies the behaviour of ``should_send_telegram_alert``:

1. confidence below the threshold is rejected (``low_confidence``)
2. MTF alignment of DISAGREE is rejected (``mtf_disagree``)
3. neutral-direction signals are rejected (``neutral_signal``)
4. a fully valid signal is accepted (``passed``)
5. missing or malformed fields are handled gracefully (no exception, reject)

The filter reads ``config.yaml`` in production, but these tests pin the
configuration to the documented defaults so they are deterministic and
do not depend on the operator's config file.
"""

import sys
from pathlib import Path

# Make ml_service importable (parent of tests/)
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest  # noqa: E402
from unittest.mock import patch  # noqa: E402

from ml_service.notifications.telegram_notifier import should_send_telegram_alert  # noqa: E402


# Documented default configuration (matches config.yaml defaults and the
# DEFAULT_* constants in telegram_notifier.py).
DEFAULT_CONFIG = {
    "min_confidence": 70,
    "require_mtf_agreement": True,
    "allow_neutral": False,
}


def _valid_signal(**overrides):
    """Return a baseline signal that passes all filters, with overrides."""
    sig = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "direction": "long",
        "confidence": 81,
        "mtf_alignment": "AGREE",
    }
    sig.update(overrides)
    return sig


class TelegramFilterTests(unittest.TestCase):
    """Filter rule coverage."""

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_low_confidence_rejected(self, _mock_cfg):
        # Confidence 49 < 70, otherwise valid -> low_confidence.
        signal = _valid_signal(confidence=49)
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "low_confidence")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_confidence_boundary_inclusive(self, _mock_cfg):
        # Exactly 70 should pass (>= comparison).
        signal = _valid_signal(confidence=70)
        ok, reason = should_send_telegram_alert(signal)
        self.assertTrue(ok)
        self.assertEqual(reason, "passed")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_mtf_disagree_rejected(self, _mock_cfg):
        # High confidence, but MTF DISAGREE -> mtf_disagree.
        signal = _valid_signal(confidence=86, mtf_alignment="DISAGREE")
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "mtf_disagree")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_mtf_neutral_rejected(self, _mock_cfg):
        # NEUTRAL is not AGREE, so it must be rejected when agreement required.
        signal = _valid_signal(confidence=80, mtf_alignment="NEUTRAL")
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "mtf_disagree")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_neutral_direction_rejected(self, _mock_cfg):
        signal = _valid_signal(direction="neutral", confidence=90, mtf_alignment="AGREE")
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "neutral_signal")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_valid_signal_accepted(self, _mock_cfg):
        # The success-criteria example: ETHUSDT 1h confidence=86 mtf=AGREE long.
        signal = _valid_signal(
            symbol="ETHUSDT", direction="long", confidence=86, mtf_alignment="AGREE"
        )
        ok, reason = should_send_telegram_alert(signal)
        self.assertTrue(ok)
        self.assertEqual(reason, "passed")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_valid_short_signal_accepted(self, _mock_cfg):
        # Short direction is just as valid as long.
        signal = _valid_signal(direction="short", confidence=75, mtf_alignment="AGREE")
        ok, reason = should_send_telegram_alert(signal)
        self.assertTrue(ok)
        self.assertEqual(reason, "passed")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_multiple_failures_reports_first_relevant(self, _mock_cfg):
        # The success-criteria "no message" example: confidence=49, mtf=DISAGREE.
        # Direction is long (non-neutral), so neutral filter passes; MTF is
        # checked next and must be the reported reason.
        signal = _valid_signal(confidence=49, mtf_alignment="DISAGREE")
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "mtf_disagree")


class TelegramFilterMissingFieldsTests(unittest.TestCase):
    """Robustness: missing or malformed fields must never raise."""

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_missing_confidence_rejected(self, _mock_cfg):
        signal = _valid_signal()
        del signal["confidence"]
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "low_confidence")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_missing_mtf_rejected(self, _mock_cfg):
        signal = _valid_signal()
        del signal["mtf_alignment"]
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "mtf_disagree")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_missing_direction_rejected(self, _mock_cfg):
        signal = _valid_signal()
        del signal["direction"]
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "neutral_signal")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_empty_dict_rejected(self, _mock_cfg):
        ok, reason = should_send_telegram_alert({})
        self.assertFalse(ok)
        self.assertEqual(reason, "neutral_signal")

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_non_dict_input_rejected(self, _mock_cfg):
        # Wrong type must not crash.
        ok, reason = should_send_telegram_alert(None)
        self.assertFalse(ok)
        ok2, reason2 = should_send_telegram_alert("not a dict")
        self.assertFalse(ok2)

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        return_value=DEFAULT_CONFIG,
    )
    def test_bad_confidence_type_rejected(self, _mock_cfg):
        # Non-numeric confidence must not crash; rejected as low_confidence.
        signal = _valid_signal(confidence="not-a-number")
        ok, reason = should_send_telegram_alert(signal)
        self.assertFalse(ok)
        self.assertEqual(reason, "low_confidence")


class TelegramFilterConfigOverrideTests(unittest.TestCase):
    """Operator-tuned configuration is honoured."""

    def test_allow_neutral_true_accepts_neutral(self):
        cfg = {**DEFAULT_CONFIG, "allow_neutral": True}
        with patch(
            "notifications.telegram_notifier._load_telegram_filter_config",
            return_value=cfg,
        ):
            signal = _valid_signal(direction="neutral", confidence=90, mtf_alignment="AGREE")
            ok, reason = should_send_telegram_alert(signal)
            self.assertTrue(ok)
            self.assertEqual(reason, "passed")

    def test_require_mtf_agreement_false_skips_mtf_check(self):
        cfg = {**DEFAULT_CONFIG, "require_mtf_agreement": False}
        with patch(
            "notifications.telegram_notifier._load_telegram_filter_config",
            return_value=cfg,
        ):
            signal = _valid_signal(confidence=80, mtf_alignment="DISAGREE")
            ok, reason = should_send_telegram_alert(signal)
            self.assertTrue(ok)
            self.assertEqual(reason, "passed")

    def test_custom_min_confidence_applied(self):
        cfg = {**DEFAULT_CONFIG, "min_confidence": 85}
        with patch(
            "notifications.telegram_notifier._load_telegram_filter_config",
            return_value=cfg,
        ):
            # 80 would pass the default (70) but not the raised threshold (85).
            signal = _valid_signal(confidence=80)
            ok, reason = should_send_telegram_alert(signal)
            self.assertFalse(ok)
            self.assertEqual(reason, "low_confidence")


class TelegramFilterNeverRaisesTest(unittest.TestCase):
    """Defensive: the public function must never propagate an exception."""

    @patch(
        "notifications.telegram_notifier._load_telegram_filter_config",
        side_effect=RuntimeError("simulated config catastrophe"),
    )
    def test_filter_swallows_internal_error(self, _mock_cfg):
        # Even if the config loader explodes, the filter must return a tuple
        # and never raise, so the scheduler is never interrupted.
        signal = _valid_signal()
        try:
            ok, reason = should_send_telegram_alert(signal)
        except Exception as e:  # pragma: no cover - test asserts the opposite
            self.fail(f"should_send_telegram_alert raised: {e!r}")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
