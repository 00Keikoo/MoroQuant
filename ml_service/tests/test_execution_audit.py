"""Unit tests for Execution Audit Framework.

Tests verify implementation matches research specification exactly.
"""

import pytest
from datetime import datetime

from audit.execution_metrics import (
    TradeData,
    compute_profit_capture_ratio,
    compute_profit_leakage,
    compute_execution_quality_score,
    compute_execution_efficiency,
    classify_trade,
    compute_all_metrics,
)
from audit.execution_patterns import (
    detect_trailing_too_early,
    detect_trailing_too_late,
    detect_sl_too_tight,
    detect_sl_too_wide,
    detect_tp_too_close,
    detect_tp_too_far,
    detect_severe_profit_leakage,
)
from audit.execution_recommendations import (
    rule_optimize_trailing_stop,
    rule_adjust_take_profit,
    rule_calibrate_stop_loss,
)


def create_test_trade(
    id: int = 1,
    entry_price: float = 100.0,
    exit_price: float = 105.0,
    direction: str = "LONG",
    mae: float = -0.02,
    mfe: float = 0.05,
    stop_loss: float = 98.0,
    take_profit: float = 110.0,
    final_exit_reason: str = "TP_HIT",
    confidence: int = 80,
    regime: str = "BULLISH",
) -> TradeData:
    """Create test trade with defaults."""
    realized_pnl_pct = (exit_price - entry_price) / entry_price
    return TradeData(
        id=id,
        entry_price=entry_price,
        exit_price=exit_price,
        direction=direction,
        realized_pnl_pct=realized_pnl_pct,
        mae=mae,
        mfe=mfe,
        mae_timestamp="2024-01-01 10:05:00",
        mfe_timestamp="2024-01-01 10:15:00",
        entry_time="2024-01-01 10:00:00",
        exit_time="2024-01-01 11:00:00",
        stop_loss=stop_loss,
        take_profit=take_profit,
        final_exit_reason=final_exit_reason,
        confidence=confidence,
        regime=regime,
        size_usdt=1000.0,
    )


class TestProfitCaptureRatio:
    """Test PCR formula: PCR = max(0, min(1, P_realized / MFE)) if MFE > 0 else 0."""

    def test_perfect_capture(self):
        """PCR = 1.0 when realized = MFE."""
        trade = create_test_trade(mfe=0.05, exit_price=105.0)
        pcr = compute_profit_capture_ratio(trade)
        assert pcr == 1.0

    def test_partial_capture(self):
        """PCR = 0.5 when realized = 0.5 × MFE."""
        trade = create_test_trade(mfe=0.10, exit_price=105.0)
        pcr = compute_profit_capture_ratio(trade)
        assert pcr == pytest.approx(0.5, abs=0.01)

    def test_zero_mfe(self):
        """PCR = 0.0 when MFE = 0."""
        trade = create_test_trade(mfe=0.0, exit_price=100.0)
        pcr = compute_profit_capture_ratio(trade)
        assert pcr == 0.0

    def test_negative_mfe(self):
        """PCR = 0.0 when MFE < 0."""
        trade = create_test_trade(mfe=-0.02, exit_price=98.0)
        pcr = compute_profit_capture_ratio(trade)
        assert pcr == 0.0


class TestProfitLeakage:
    """Test PL formula: PL = MFE - max(0, P_realized)."""

    def test_positive_realized(self):
        """PL = MFE - P_realized when realized > 0."""
        trade = create_test_trade(mfe=0.10, exit_price=105.0)
        pl = compute_profit_leakage(trade)
        expected = 0.10 - 0.05
        assert pl == pytest.approx(expected, abs=0.001)

    def test_negative_realized(self):
        """PL = MFE when realized < 0."""
        trade = create_test_trade(mfe=0.05, exit_price=98.0)
        pl = compute_profit_leakage(trade)
        assert pl == pytest.approx(0.05, abs=0.001)


class TestExecutionQualityScore:
    """Test EQS formula: EQS = PCR × (1 - |MAE| / (|MAE| + MFE + ε))."""

    def test_perfect_execution(self):
        """EQS close to PCR when MAE small."""
        trade = create_test_trade(mae=-0.01, mfe=0.10, exit_price=110.0)
        pcr = 1.0
        eqs = compute_execution_quality_score(trade, pcr)
        assert eqs > 0.9

    def test_poor_drawdown_management(self):
        """EQS reduced when |MAE| large."""
        trade = create_test_trade(mae=-0.10, mfe=0.10, exit_price=105.0)
        pcr = 0.5
        eqs = compute_execution_quality_score(trade, pcr)
        assert eqs < 0.3


class TestExecutionEfficiency:
    """Test EE formula: EE = P_realized / (MFE - MAE + ε)."""

    def test_positive_efficiency(self):
        """EE > 0 when realized positive."""
        trade = create_test_trade(mae=-0.02, mfe=0.10, exit_price=105.0)
        ee = compute_execution_efficiency(trade)
        expected = 0.05 / (0.10 - (-0.02))
        assert ee == pytest.approx(expected, abs=0.01)


class TestModelExecutionClassification:
    """Test M/E classification matrix."""

    def test_mc_ec(self):
        """MC/EC: MFE >= θ_signal AND PCR >= θ_pcr."""
        trade = create_test_trade(mfe=0.03, exit_price=103.0)
        cls = classify_trade(trade, theta_signal=0.01, theta_pcr=0.5)
        assert cls == "MC/EC"

    def test_mc_ew(self):
        """MC/EW: MFE >= θ_signal AND PCR < θ_pcr."""
        trade = create_test_trade(mfe=0.10, exit_price=102.0)
        cls = classify_trade(trade, theta_signal=0.01, theta_pcr=0.5)
        assert cls == "MC/EW"

    def test_mw_ec(self):
        """MW/EC: MFE < θ_signal AND stopped out cleanly."""
        trade = create_test_trade(mfe=0.005, exit_price=98.0, mae=-0.02)
        trade.realized_pnl_pct = trade.mae
        cls = classify_trade(trade, theta_signal=0.01, theta_pcr=0.5)
        assert cls == "MW/EC"

    def test_mw_ew(self):
        """MW/EW: MFE < θ_signal AND poor execution."""
        trade = create_test_trade(mfe=0.005, exit_price=97.5, mae=-0.03)
        cls = classify_trade(trade, theta_signal=0.01, theta_pcr=0.5)
        assert cls == "MW/EW"


class TestPatternDetectors:
    """Test pattern detection rules."""

    def test_trailing_too_early(self):
        """Detect: MFE >= 2 × Target AND PCR < 0.30."""
        trade = create_test_trade(
            mfe=0.20,
            exit_price=103.0,
            take_profit=110.0,
            final_exit_reason="EXPIRED",
        )
        pattern = detect_trailing_too_early([trade])
        assert pattern.detected

    def test_trailing_too_late(self):
        """Detect: MFE >= 1.5 × Target AND PL > 0.8 × MFE AND SL hit."""
        trade = create_test_trade(
            mfe=0.16,
            exit_price=98.0,
            take_profit=110.0,
            final_exit_reason="SL_HIT",
        )
        pattern = detect_trailing_too_late([trade])
        assert pattern.detected

    def test_sl_too_tight(self):
        """Detect: |MAE| >= |Stop| AND SL hit."""
        trade = create_test_trade(
            mae=-0.02,
            stop_loss=98.0,
            final_exit_reason="SL_HIT",
        )
        pattern = detect_sl_too_tight([trade])
        assert pattern.detected

    def test_tp_too_close(self):
        """Detect: TP hit AND MFE >= 2 × P_realized."""
        trade = create_test_trade(
            mfe=0.10,
            exit_price=102.0,
            final_exit_reason="TP_HIT",
        )
        pattern = detect_tp_too_close([trade])
        assert pattern.detected

    def test_tp_too_far(self):
        """Detect: MFE >= 0.9 × Target AND P_realized <= 0 AND SL hit."""
        trade = create_test_trade(
            mfe=0.095,
            exit_price=98.0,
            take_profit=110.0,
            final_exit_reason="SL_HIT",
        )
        pattern = detect_tp_too_far([trade])
        assert pattern.detected


class TestRecommendationRules:
    """Test recommendation rules."""

    def test_optimize_trailing_stop(self):
        """Rule 1: MC/EW >= 0.25 AND PL >= 0.5 × MFE."""
        trades = [
            create_test_trade(id=i, mfe=0.10, exit_price=102.0)
            for i in range(1, 5)
        ]
        metrics = compute_all_metrics(trades)
        rec = rule_optimize_trailing_stop(metrics, trades, [])
        assert rec.condition_met

    def test_calibrate_stop_loss(self):
        """Rule 3: SL Too Tight >= 0.30 × N."""
        trades = [
            create_test_trade(
                id=i,
                mae=-0.02,
                stop_loss=98.0,
                final_exit_reason="SL_HIT",
            )
            for i in range(1, 5)
        ]
        metrics = compute_all_metrics(trades)
        patterns = [detect_sl_too_tight(trades)]
        rec = rule_calibrate_stop_loss(metrics, trades, patterns)
        assert rec.condition_met


class TestMetricsAggregation:
    """Test aggregate metrics computation."""

    def test_compute_all_metrics(self):
        """Verify all metrics computed."""
        trades = [
            create_test_trade(id=1, mfe=0.05, exit_price=105.0),
            create_test_trade(id=2, mfe=0.03, exit_price=103.0),
            create_test_trade(id=3, mfe=0.01, exit_price=98.0),
        ]
        metrics = compute_all_metrics(trades)

        assert metrics.total_trades == 3
        assert metrics.avg_mfe > 0
        assert metrics.avg_mae < 0
        assert 0 <= metrics.avg_pcr <= 1
        assert metrics.mc_ec_count + metrics.mc_ew_count + metrics.mw_ec_count + metrics.mw_ew_count == 3
