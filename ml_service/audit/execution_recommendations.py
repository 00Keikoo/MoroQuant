"""Execution Recommendation Engine.

Implements 5 deterministic recommendation rules as defined in the research specification.
Each rule generates operational recommendations based on detected patterns.
"""

from dataclasses import dataclass
from typing import List

import numpy as np
from scipy import stats

from .execution_metrics import ExecutionMetrics, TradeData
from .execution_patterns import PatternDetection


@dataclass
class Recommendation:
    """Single recommendation."""

    rule_name: str
    action: str
    priority: str
    rationale: str
    condition_met: bool


def rule_optimize_trailing_stop(
    metrics: ExecutionMetrics,
    trades: List[TradeData],
    patterns: List[PatternDetection],
) -> Recommendation:
    """Rule 1: Optimize Trailing Stop Distance.

    Condition: Ratio(MC/EW) >= 0.25 AND PL >= 0.5 × MFE
    Recommendation: TIGHTEN_TRAILING_STOP_TRIGGER
    """
    total_trades = metrics.total_trades
    if total_trades == 0:
        return Recommendation(
            rule_name="OPTIMIZE_TRAILING_STOP",
            action="NO_ACTION",
            priority="LOW",
            rationale="Insufficient trades",
            condition_met=False,
        )

    ratio_mc_ew = metrics.mc_ew_count / total_trades
    avg_mfe = metrics.avg_mfe

    condition_met = ratio_mc_ew >= 0.25 and metrics.avg_pl >= 0.5 * avg_mfe

    if condition_met:
        return Recommendation(
            rule_name="OPTIMIZE_TRAILING_STOP",
            action="TIGHTEN_TRAILING_STOP_TRIGGER",
            priority="HIGH",
            rationale=f"Model correct but execution weak ({ratio_mc_ew:.1%}), giving back {metrics.avg_pl:.2%} of {avg_mfe:.2%} MFE",
            condition_met=True,
        )

    return Recommendation(
        rule_name="OPTIMIZE_TRAILING_STOP",
        action="NO_ACTION",
        priority="LOW",
        rationale="Trailing stop performance acceptable",
        condition_met=False,
    )


def rule_adjust_take_profit(
    metrics: ExecutionMetrics,
    trades: List[TradeData],
    patterns: List[PatternDetection],
) -> Recommendation:
    """Rule 2: Adjust Take-Profit Target.

    Condition: Ratio(MC/EW) >= 0.30 AND TP Too Far Count >= 0.40 × N
    Recommendation: LOWER_TAKE_PROFIT_LIMIT
    """
    total_trades = metrics.total_trades
    if total_trades == 0:
        return Recommendation(
            rule_name="ADJUST_TAKE_PROFIT",
            action="NO_ACTION",
            priority="LOW",
            rationale="Insufficient trades",
            condition_met=False,
        )

    ratio_mc_ew = metrics.mc_ew_count / total_trades

    tp_too_far_pattern = next((p for p in patterns if p.pattern_name == "TP_TOO_FAR"), None)
    tp_too_far_count = tp_too_far_pattern.count if tp_too_far_pattern else 0

    condition_met = ratio_mc_ew >= 0.30 and tp_too_far_count >= 0.40 * total_trades

    if condition_met:
        return Recommendation(
            rule_name="ADJUST_TAKE_PROFIT",
            action="LOWER_TAKE_PROFIT_LIMIT",
            priority="HIGH",
            rationale=f"Price frequently approaches target ({tp_too_far_count}/{total_trades} trades) but reverses to SL",
            condition_met=True,
        )

    return Recommendation(
        rule_name="ADJUST_TAKE_PROFIT",
        action="NO_ACTION",
        priority="LOW",
        rationale="Take-profit target appropriate",
        condition_met=False,
    )


def rule_calibrate_stop_loss(
    metrics: ExecutionMetrics,
    trades: List[TradeData],
    patterns: List[PatternDetection],
) -> Recommendation:
    """Rule 3: Calibrate Stop-Loss Limits.

    Condition: SL Too Tight Count >= 0.30 × N AND MAE ≈ Stop Loss Distance
    Recommendation: WIDEN_STOP_LOSS_AND_SCALE_SIZING
    """
    total_trades = metrics.total_trades
    if total_trades == 0:
        return Recommendation(
            rule_name="CALIBRATE_STOP_LOSS",
            action="NO_ACTION",
            priority="LOW",
            rationale="Insufficient trades",
            condition_met=False,
        )

    sl_too_tight_pattern = next((p for p in patterns if p.pattern_name == "SL_TOO_TIGHT"), None)
    sl_too_tight_count = sl_too_tight_pattern.count if sl_too_tight_pattern else 0

    stop_distances = []
    for trade in trades:
        if trade.stop_loss is not None:
            stop_distance_pct = abs(trade.stop_loss - trade.entry_price) / trade.entry_price
            stop_distances.append(stop_distance_pct)

    avg_stop_distance = np.mean(stop_distances) if stop_distances else 0.0
    mae_approx_stop = abs(abs(metrics.avg_mae) - avg_stop_distance) < 0.01

    condition_met = sl_too_tight_count >= 0.30 * total_trades and mae_approx_stop

    if condition_met:
        return Recommendation(
            rule_name="CALIBRATE_STOP_LOSS",
            action="WIDEN_STOP_LOSS_AND_SCALE_SIZING",
            priority="CRITICAL",
            rationale=f"Stopped out by noise ({sl_too_tight_count}/{total_trades} trades), MAE {metrics.avg_mae:.2%} ≈ stop {avg_stop_distance:.2%}",
            condition_met=True,
        )

    return Recommendation(
        rule_name="CALIBRATE_STOP_LOSS",
        action="NO_ACTION",
        priority="LOW",
        rationale="Stop-loss calibration appropriate",
        condition_met=False,
    )


def rule_address_execution_slippage(
    metrics: ExecutionMetrics,
    trades: List[TradeData],
    patterns: List[PatternDetection],
) -> Recommendation:
    """Rule 4: Address Execution Slippage.

    Condition: Ratio(MW/EW) >= 0.15 AND Mean Slippage >= 0.0020 (20 bps)
    Recommendation: TRANSITION_TO_LIMIT_ORDERS
    """
    total_trades = metrics.total_trades
    if total_trades == 0:
        return Recommendation(
            rule_name="ADDRESS_EXECUTION_SLIPPAGE",
            action="NO_ACTION",
            priority="LOW",
            rationale="Insufficient trades",
            condition_met=False,
        )

    ratio_mw_ew = metrics.mw_ew_count / total_trades

    slippages = []
    for trade in trades:
        expected_mae = 0.0
        if trade.stop_loss is not None:
            expected_mae = -abs(trade.stop_loss - trade.entry_price) / trade.entry_price

        slippage = trade.mae - expected_mae if expected_mae != 0 else 0.0
        slippages.append(abs(slippage))

    mean_slippage = np.mean(slippages) if slippages else 0.0

    condition_met = ratio_mw_ew >= 0.15 and mean_slippage >= 0.0020

    if condition_met:
        return Recommendation(
            rule_name="ADDRESS_EXECUTION_SLIPPAGE",
            action="TRANSITION_TO_LIMIT_ORDERS",
            priority="HIGH",
            rationale=f"High slippage ({mean_slippage:.2%}) degrading MW/EW trades ({ratio_mw_ew:.1%})",
            condition_met=True,
        )

    return Recommendation(
        rule_name="ADDRESS_EXECUTION_SLIPPAGE",
        action="NO_ACTION",
        priority="LOW",
        rationale="Execution slippage acceptable",
        condition_met=False,
    )


def rule_apply_confidence_gate(
    metrics: ExecutionMetrics,
    trades: List[TradeData],
    patterns: List[PatternDetection],
) -> Recommendation:
    """Rule 5: Apply Dynamic Sizing based on Confidence.

    Condition: ρ(Confidence, P_realized) >= 0.30 AND EV_Low_Confidence < 0.0
    Recommendation: APPLY_CONFIDENCE_VOLUME_GATE
    """
    trades_with_confidence = [t for t in trades if t.confidence is not None]

    if len(trades_with_confidence) < 10:
        return Recommendation(
            rule_name="APPLY_CONFIDENCE_GATE",
            action="NO_ACTION",
            priority="LOW",
            rationale="Insufficient confidence data",
            condition_met=False,
        )

    confidence_scores = [t.confidence for t in trades_with_confidence]
    returns = [t.realized_pnl_pct for t in trades_with_confidence]

    correlation, _ = stats.spearmanr(confidence_scores, returns)

    median_confidence = np.median(confidence_scores)
    low_conf_trades = [t for t in trades_with_confidence if t.confidence < median_confidence]
    ev_low_confidence = np.mean([t.realized_pnl_pct for t in low_conf_trades]) if low_conf_trades else 0.0

    condition_met = correlation >= 0.30 and ev_low_confidence < 0.0

    if condition_met:
        return Recommendation(
            rule_name="APPLY_CONFIDENCE_GATE",
            action="APPLY_CONFIDENCE_VOLUME_GATE",
            priority="CRITICAL",
            rationale=f"Confidence correlates with success (ρ={correlation:.2f}), low-confidence EV={ev_low_confidence:.2%}",
            condition_met=True,
        )

    return Recommendation(
        rule_name="APPLY_CONFIDENCE_GATE",
        action="NO_ACTION",
        priority="LOW",
        rationale="Confidence signal not predictive",
        condition_met=False,
    )


def generate_all_recommendations(
    metrics: ExecutionMetrics,
    trades: List[TradeData],
    patterns: List[PatternDetection],
) -> List[Recommendation]:
    """Generate all recommendations."""
    return [
        rule_optimize_trailing_stop(metrics, trades, patterns),
        rule_adjust_take_profit(metrics, trades, patterns),
        rule_calibrate_stop_loss(metrics, trades, patterns),
        rule_address_execution_slippage(metrics, trades, patterns),
        rule_apply_confidence_gate(metrics, trades, patterns),
    ]
