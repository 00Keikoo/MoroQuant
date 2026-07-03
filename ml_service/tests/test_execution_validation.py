"""Unit tests for Execution Validation Suite.

Tests all validation rules with deterministic fixtures.
"""

import math
import unittest
from datetime import datetime

from ml_service.validation.execution_rules import (
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
)
from ml_service.validation.execution_validator import validate_position


class TestMAERule(unittest.TestCase):
    """Test Rule 1: MAE <= 0"""

    def test_mae_valid_negative(self):
        position = {"id": 1, "mae": -0.05}
        self.assertIsNone(rule_mae_non_positive(position))

    def test_mae_valid_zero(self):
        position = {"id": 1, "mae": 0.0}
        self.assertIsNone(rule_mae_non_positive(position))

    def test_mae_invalid_positive(self):
        position = {"id": 1, "mae": 0.05}
        failure = rule_mae_non_positive(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "MAE_NON_POSITIVE")
        self.assertEqual(failure.severity, "ERROR")

    def test_mae_null(self):
        position = {"id": 1, "mae": None}
        self.assertIsNone(rule_mae_non_positive(position))


class TestMFERule(unittest.TestCase):
    """Test Rule 2: MFE >= 0"""

    def test_mfe_valid_positive(self):
        position = {"id": 1, "mfe": 0.05}
        self.assertIsNone(rule_mfe_non_negative(position))

    def test_mfe_valid_zero(self):
        position = {"id": 1, "mfe": 0.0}
        self.assertIsNone(rule_mfe_non_negative(position))

    def test_mfe_invalid_negative(self):
        position = {"id": 1, "mfe": -0.05}
        failure = rule_mfe_non_negative(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "MFE_NON_NEGATIVE")
        self.assertEqual(failure.severity, "ERROR")

    def test_mfe_null(self):
        position = {"id": 1, "mfe": None}
        self.assertIsNone(rule_mfe_non_negative(position))


class TestMAETimestampRule(unittest.TestCase):
    """Test Rule 3: MAE timestamp exists if MAE changed"""

    def test_mae_changed_with_timestamp(self):
        position = {
            "id": 1,
            "mae": -0.05,
            "mae_timestamp": "2024-01-01 10:00:00",
        }
        self.assertIsNone(rule_mae_timestamp_exists(position))

    def test_mae_changed_without_timestamp(self):
        position = {"id": 1, "mae": -0.05, "mae_timestamp": None}
        failure = rule_mae_timestamp_exists(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "MAE_TIMESTAMP_MISSING")
        self.assertEqual(failure.severity, "WARNING")

    def test_mae_zero_no_timestamp(self):
        position = {"id": 1, "mae": 0.0, "mae_timestamp": None}
        self.assertIsNone(rule_mae_timestamp_exists(position))

    def test_mae_null(self):
        position = {"id": 1, "mae": None, "mae_timestamp": None}
        self.assertIsNone(rule_mae_timestamp_exists(position))


class TestMFETimestampRule(unittest.TestCase):
    """Test Rule 4: MFE timestamp exists if MFE changed"""

    def test_mfe_changed_with_timestamp(self):
        position = {
            "id": 1,
            "mfe": 0.05,
            "mfe_timestamp": "2024-01-01 10:00:00",
        }
        self.assertIsNone(rule_mfe_timestamp_exists(position))

    def test_mfe_changed_without_timestamp(self):
        position = {"id": 1, "mfe": 0.05, "mfe_timestamp": None}
        failure = rule_mfe_timestamp_exists(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "MFE_TIMESTAMP_MISSING")
        self.assertEqual(failure.severity, "WARNING")

    def test_mfe_zero_no_timestamp(self):
        position = {"id": 1, "mfe": 0.0, "mfe_timestamp": None}
        self.assertIsNone(rule_mfe_timestamp_exists(position))


class TestTimestampOrderingRule(unittest.TestCase):
    """Test Rule 5: opened_at < closed_at"""

    def test_valid_ordering(self):
        position = {
            "id": 1,
            "opened_at": "2024-01-01 10:00:00",
            "closed_at": "2024-01-01 11:00:00",
        }
        self.assertIsNone(rule_opened_before_closed(position))

    def test_invalid_same_time(self):
        position = {
            "id": 1,
            "opened_at": "2024-01-01 10:00:00",
            "closed_at": "2024-01-01 10:00:00",
        }
        failure = rule_opened_before_closed(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "OPENED_BEFORE_CLOSED")

    def test_invalid_reverse_order(self):
        position = {
            "id": 1,
            "opened_at": "2024-01-01 11:00:00",
            "closed_at": "2024-01-01 10:00:00",
        }
        failure = rule_opened_before_closed(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "OPENED_BEFORE_CLOSED")

    def test_invalid_timestamp_format(self):
        position = {
            "id": 1,
            "opened_at": "invalid",
            "closed_at": "2024-01-01 10:00:00",
        }
        failure = rule_opened_before_closed(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "TIMESTAMP_PARSE_ERROR")


class TestHoldTimeRule(unittest.TestCase):
    """Test Rule 6: Hold time > 0"""

    def test_valid_hold_time(self):
        position = {
            "id": 1,
            "opened_at": "2024-01-01 10:00:00",
            "closed_at": "2024-01-01 11:00:00",
        }
        self.assertIsNone(rule_hold_time_positive(position))

    def test_zero_hold_time(self):
        position = {
            "id": 1,
            "opened_at": "2024-01-01 10:00:00",
            "closed_at": "2024-01-01 10:00:00",
        }
        failure = rule_hold_time_positive(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "HOLD_TIME_POSITIVE")


class TestProfitCaptureRatioRule(unittest.TestCase):
    """Test Rule 7: 0 <= PCR <= 1, if MFE == 0 then PCR must be NULL or 0"""

    def test_valid_pcr_mid_range(self):
        position = {"id": 1, "profit_capture_ratio": 0.5, "mfe": 0.05}
        self.assertIsNone(rule_profit_capture_ratio_bounds(position))

    def test_valid_pcr_zero(self):
        position = {"id": 1, "profit_capture_ratio": 0.0, "mfe": 0.0}
        self.assertIsNone(rule_profit_capture_ratio_bounds(position))

    def test_valid_pcr_one(self):
        position = {"id": 1, "profit_capture_ratio": 1.0, "mfe": 0.05}
        self.assertIsNone(rule_profit_capture_ratio_bounds(position))

    def test_invalid_pcr_negative(self):
        position = {"id": 1, "profit_capture_ratio": -0.1, "mfe": 0.05}
        failure = rule_profit_capture_ratio_bounds(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PCR_OUT_OF_BOUNDS")

    def test_invalid_pcr_above_one(self):
        position = {"id": 1, "profit_capture_ratio": 1.5, "mfe": 0.05}
        failure = rule_profit_capture_ratio_bounds(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PCR_OUT_OF_BOUNDS")

    def test_invalid_pcr_nan(self):
        position = {"id": 1, "profit_capture_ratio": float("nan"), "mfe": 0.05}
        failure = rule_profit_capture_ratio_bounds(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PCR_INVALID_VALUE")

    def test_invalid_pcr_inf(self):
        position = {"id": 1, "profit_capture_ratio": float("inf"), "mfe": 0.05}
        failure = rule_profit_capture_ratio_bounds(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PCR_INVALID_VALUE")

    def test_invalid_divide_by_zero(self):
        position = {"id": 1, "profit_capture_ratio": 0.5, "mfe": 0.0}
        failure = rule_profit_capture_ratio_bounds(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PCR_DIVIDE_BY_ZERO")


class TestTrailingConsistencyRule(unittest.TestCase):
    """Test Rule 8: if trailing_stop_activated == 1 then sl_move_count >= 1"""

    def test_valid_trailing_with_moves(self):
        position = {"id": 1, "trailing_stop_activated": 1, "sl_move_count": 3}
        self.assertIsNone(rule_trailing_consistency(position))

    def test_invalid_trailing_no_moves(self):
        position = {"id": 1, "trailing_stop_activated": 1, "sl_move_count": 0}
        failure = rule_trailing_consistency(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "TRAILING_INCONSISTENCY")

    def test_invalid_trailing_null_moves(self):
        position = {"id": 1, "trailing_stop_activated": 1, "sl_move_count": None}
        failure = rule_trailing_consistency(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "TRAILING_INCONSISTENCY")

    def test_no_trailing_no_validation(self):
        position = {"id": 1, "trailing_stop_activated": 0, "sl_move_count": 0}
        self.assertIsNone(rule_trailing_consistency(position))


class TestBreakEvenConsistencyRule(unittest.TestCase):
    """Test Rule 9: if break_even_triggered == 1 then sl_move_count >= 1"""

    def test_valid_break_even_with_moves(self):
        position = {"id": 1, "break_even_triggered": 1, "sl_move_count": 1}
        self.assertIsNone(rule_break_even_consistency(position))

    def test_invalid_break_even_no_moves(self):
        position = {"id": 1, "break_even_triggered": 1, "sl_move_count": 0}
        failure = rule_break_even_consistency(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "BREAK_EVEN_INCONSISTENCY")
        self.assertEqual(failure.severity, "WARNING")

    def test_no_break_even_no_validation(self):
        position = {"id": 1, "break_even_triggered": 0, "sl_move_count": 0}
        self.assertIsNone(rule_break_even_consistency(position))


class TestExecutionClassificationRule(unittest.TestCase):
    """Test Rule 10: Execution classification must be valid"""

    def test_valid_classification_model_correct_execution_correct(self):
        position = {
            "id": 1,
            "mae": -0.01,
            "mfe": 0.05,
            "profit_capture_ratio": 0.8,
            "realized_pnl": 50.0,
            "direction": "LONG",
            "confidence": 85,
        }
        self.assertIsNone(rule_execution_classification_valid(position))

    def test_valid_classification_model_weak(self):
        position = {
            "id": 1,
            "mae": -0.01,
            "mfe": 0.01,
            "profit_capture_ratio": 0.2,
            "realized_pnl": -10.0,
            "direction": "LONG",
            "confidence": 60,
        }
        self.assertIsNone(rule_execution_classification_valid(position))

    def test_valid_classification_unknown(self):
        position = {
            "id": 1,
            "mae": None,
            "mfe": None,
            "profit_capture_ratio": None,
            "realized_pnl": None,
            "direction": "LONG",
            "confidence": None,
        }
        self.assertIsNone(rule_execution_classification_valid(position))


class TestExitReasonRule(unittest.TestCase):
    """Test Rule 11: Exit reason must belong to known enum"""

    def test_valid_exit_tp_hit(self):
        position = {"id": 1, "final_exit_reason": "TP_HIT"}
        self.assertIsNone(rule_exit_reason_valid(position))

    def test_valid_exit_sl_hit(self):
        position = {"id": 1, "final_exit_reason": "SL_HIT"}
        self.assertIsNone(rule_exit_reason_valid(position))

    def test_valid_exit_expired(self):
        position = {"id": 1, "final_exit_reason": "EXPIRED"}
        self.assertIsNone(rule_exit_reason_valid(position))

    def test_valid_exit_manual_close(self):
        position = {"id": 1, "final_exit_reason": "MANUAL_CLOSE"}
        self.assertIsNone(rule_exit_reason_valid(position))

    def test_invalid_exit_reason(self):
        position = {"id": 1, "final_exit_reason": "INVALID_REASON"}
        failure = rule_exit_reason_valid(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "INVALID_EXIT_REASON")

    def test_null_exit_reason(self):
        position = {"id": 1, "final_exit_reason": None}
        self.assertIsNone(rule_exit_reason_valid(position))


class TestNoImpossibleValuesRule(unittest.TestCase):
    """Test Rule 12: No impossible values"""

    def test_valid_confidence(self):
        position = {"id": 1, "confidence": 75}
        self.assertIsNone(rule_no_impossible_values(position))

    def test_invalid_confidence_negative(self):
        position = {"id": 1, "confidence": -10}
        failure = rule_no_impossible_values(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "CONFIDENCE_OUT_OF_BOUNDS")

    def test_invalid_confidence_above_100(self):
        position = {"id": 1, "confidence": 150}
        failure = rule_no_impossible_values(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "CONFIDENCE_OUT_OF_BOUNDS")

    def test_invalid_confidence_nan(self):
        position = {"id": 1, "confidence": float("nan")}
        failure = rule_no_impossible_values(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "CONFIDENCE_INVALID")

    def test_valid_probabilities(self):
        position = {
            "id": 1,
            "prob_short": 0.2,
            "prob_neutral": 0.3,
            "prob_long": 0.5,
        }
        self.assertIsNone(rule_no_impossible_values(position))

    def test_invalid_probability_nan(self):
        position = {
            "id": 1,
            "prob_short": float("nan"),
            "prob_neutral": 0.3,
            "prob_long": 0.5,
        }
        failure = rule_no_impossible_values(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PROBABILITY_INVALID")

    def test_invalid_probability_sum(self):
        position = {
            "id": 1,
            "prob_short": 0.5,
            "prob_neutral": 0.3,
            "prob_long": 0.5,
        }
        failure = rule_no_impossible_values(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "PROBABILITY_SUM_INVALID")
        self.assertEqual(failure.severity, "WARNING")

    def test_invalid_realized_pnl_nan(self):
        position = {"id": 1, "realized_pnl": float("nan")}
        failure = rule_no_impossible_values(position)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule_violated, "REALIZED_PNL_INVALID")


class TestIntegratedValidation(unittest.TestCase):
    """Test full position validation with multiple rules"""

    def test_perfect_winning_trade(self):
        position = {
            "id": 1,
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 50000.0,
            "current_price": 51000.0,
            "size_usdt": 1000.0,
            "qty": 0.02,
            "stop_loss": 49500.0,
            "take_profit": 51000.0,
            "signal_id": 1,
            "status": "TP_HIT",
            "realized_pnl": 50.0,
            "opened_at": "2024-01-01 10:00:00",
            "closed_at": "2024-01-01 11:00:00",
            "mae": -0.01,
            "mfe": 0.05,
            "mae_timestamp": "2024-01-01 10:15:00",
            "mfe_timestamp": "2024-01-01 10:50:00",
            "eqs": 85,
            "profit_capture_ratio": 0.8,
            "final_exit_reason": "TP_HIT",
            "trailing_stop_enabled": 1,
            "trailing_stop_activated": 1,
            "sl_move_count": 3,
            "break_even_triggered": 1,
            "confidence": 85,
            "regime": "BULL",
            "timeframe": "1h",
            "prob_short": 0.1,
            "prob_neutral": 0.2,
            "prob_long": 0.7,
            "execution_edge": 0.05,
            "skip_reason": None,
        }
        failures = validate_position(position)
        self.assertEqual(len(failures), 0)

    def test_multiple_failures(self):
        position = {
            "id": 2,
            "mae": 0.05,
            "mfe": -0.02,
            "profit_capture_ratio": 1.5,
            "opened_at": "2024-01-01 11:00:00",
            "closed_at": "2024-01-01 10:00:00",
            "confidence": 150,
            "final_exit_reason": "INVALID",
            "trailing_stop_activated": 1,
            "sl_move_count": 0,
            "direction": "LONG",
            "realized_pnl": 0.0,
        }
        failures = validate_position(position)
        self.assertGreater(len(failures), 0)
        violated_rules = {f.rule_violated for f in failures}
        self.assertIn("MAE_NON_POSITIVE", violated_rules)
        self.assertIn("MFE_NON_NEGATIVE", violated_rules)
        self.assertIn("PCR_OUT_OF_BOUNDS", violated_rules)
        self.assertIn("OPENED_BEFORE_CLOSED", violated_rules)
        self.assertIn("CONFIDENCE_OUT_OF_BOUNDS", violated_rules)
        self.assertIn("INVALID_EXIT_REASON", violated_rules)
        self.assertIn("TRAILING_INCONSISTENCY", violated_rules)


if __name__ == "__main__":
    unittest.main()
