"""Execution Pattern Detectors.

Implements 11 deterministic pattern detectors as defined in the research specification.
Each detector identifies a specific execution failure mode.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from scipy import stats

from .execution_metrics import TradeData, compute_profit_capture_ratio, compute_profit_leakage


@dataclass
class PatternDetection:
    """Single pattern detection result."""

    pattern_name: str
    detected: bool
    trade_ids: List[int]
    severity: str
    description: str
    count: int


def detect_trailing_too_early(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 1: Trailing Too Early.

    MFE >= 2 × Intended Target AND PCR < 0.30 AND Exit Reason = 'Trailing Stop'
    """
    detected_trades = []

    for trade in trades:
        if trade.take_profit is None:
            continue

        intended_target_pct = abs(trade.take_profit - trade.entry_price) / trade.entry_price
        pcr = compute_profit_capture_ratio(trade)

        if (
            trade.mfe >= 2 * intended_target_pct
            and pcr < 0.30
            and trade.final_exit_reason in ("EXPIRED", "MANUAL_CLOSE")
        ):
            detected_trades.append(trade.id)

    return PatternDetection(
        pattern_name="TRAILING_TOO_EARLY",
        detected=len(detected_trades) > 0,
        trade_ids=detected_trades,
        severity="HIGH",
        description="Trailing stop activated too early, giving back >70% of MFE",
        count=len(detected_trades),
    )


def detect_trailing_too_late(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 2: Trailing Too Late.

    MFE >= 1.5 × Intended Target AND PL > 0.8 × MFE AND Exit Reason = 'Stop Loss' (at a loss)
    """
    detected_trades = []

    for trade in trades:
        if trade.take_profit is None:
            continue

        intended_target_pct = abs(trade.take_profit - trade.entry_price) / trade.entry_price
        pl = compute_profit_leakage(trade)

        if (
            trade.mfe >= 1.5 * intended_target_pct
            and pl > 0.8 * trade.mfe
            and trade.final_exit_reason == "SL_HIT"
            and trade.realized_pnl_pct < 0
        ):
            detected_trades.append(trade.id)

    return PatternDetection(
        pattern_name="TRAILING_TOO_LATE",
        detected=len(detected_trades) > 0,
        trade_ids=detected_trades,
        severity="HIGH",
        description="Trailing stop not activated, gave back >80% of MFE before SL hit",
        count=len(detected_trades),
    )


def detect_sl_too_tight(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 3: Stop-Loss Too Tight.

    |MAE| >= |Stop| AND Exit Reason = 'Stop Loss' AND MFE_post_exit >= Target

    Note: Requires post-exit trajectory data, which is not currently available.
    This implementation detects trades that hit SL when MAE matched stop distance.
    """
    detected_trades = []

    for trade in trades:
        if trade.stop_loss is None:
            continue

        stop_distance_pct = abs(trade.stop_loss - trade.entry_price) / trade.entry_price
        mae_abs = abs(trade.mae)

        if (
            mae_abs >= stop_distance_pct * 0.95
            and trade.final_exit_reason == "SL_HIT"
        ):
            detected_trades.append(trade.id)

    return PatternDetection(
        pattern_name="SL_TOO_TIGHT",
        detected=len(detected_trades) > 0,
        trade_ids=detected_trades,
        severity="MEDIUM",
        description="Stop-loss too tight, stopped out by noise before favorable move",
        count=len(detected_trades),
    )


def detect_sl_too_wide(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 4: Stop-Loss Too Wide.

    MAE_losses > 2.5 × MFE_wins AND Exit Reason = 'Stop Loss'
    """
    losses = [t for t in trades if t.realized_pnl_pct < 0 and t.final_exit_reason == "SL_HIT"]
    wins = [t for t in trades if t.realized_pnl_pct > 0]

    if not losses or not wins:
        return PatternDetection(
            pattern_name="SL_TOO_WIDE",
            detected=False,
            trade_ids=[],
            severity="HIGH",
            description="Stop-loss too wide, average loss exceeds 2.5x average win",
            count=0,
        )

    avg_mae_losses = np.mean([abs(t.mae) for t in losses])
    avg_mfe_wins = np.mean([t.mfe for t in wins])

    detected = avg_mae_losses > 2.5 * avg_mfe_wins
    detected_trades = [t.id for t in losses] if detected else []

    return PatternDetection(
        pattern_name="SL_TOO_WIDE",
        detected=detected,
        trade_ids=detected_trades,
        severity="HIGH",
        description=f"Stop-loss too wide, avg loss MAE ({avg_mae_losses:.3f}) > 2.5x avg win MFE ({avg_mfe_wins:.3f})",
        count=len(detected_trades),
    )


def detect_tp_too_close(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 5: Take-Profit Too Close.

    Exit Reason = 'Take Profit' AND MFE_post_exit >= 2 × P_realized

    Note: Requires post-exit trajectory data. Current implementation uses MFE during trade.
    """
    detected_trades = []

    for trade in trades:
        if trade.final_exit_reason != "TP_HIT":
            continue

        if trade.mfe >= 2 * abs(trade.realized_pnl_pct):
            detected_trades.append(trade.id)

    return PatternDetection(
        pattern_name="TP_TOO_CLOSE",
        detected=len(detected_trades) > 0,
        trade_ids=detected_trades,
        severity="MEDIUM",
        description="Take-profit too close, MFE exceeded realized profit by 2x",
        count=len(detected_trades),
    )


def detect_tp_too_far(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 6: Take-Profit Too Far.

    MFE >= 0.9 × Target AND P_realized <= 0.0 AND Exit Reason = 'Stop Loss'
    """
    detected_trades = []

    for trade in trades:
        if trade.take_profit is None:
            continue

        target_distance_pct = abs(trade.take_profit - trade.entry_price) / trade.entry_price

        if (
            trade.mfe >= 0.9 * target_distance_pct
            and trade.realized_pnl_pct <= 0.0
            and trade.final_exit_reason == "SL_HIT"
        ):
            detected_trades.append(trade.id)

    return PatternDetection(
        pattern_name="TP_TOO_FAR",
        detected=len(detected_trades) > 0,
        trade_ids=detected_trades,
        severity="HIGH",
        description="Take-profit too far, reached 90% of target but reversed to SL",
        count=len(detected_trades),
    )


def detect_severe_profit_leakage(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 7: Severe Profit Leakage.

    PCR < 0.35 AND PL > 1.5 × P_realized
    """
    pcr_list = [compute_profit_capture_ratio(t) for t in trades]
    pl_list = [compute_profit_leakage(t) for t in trades]
    realized_list = [t.realized_pnl_pct for t in trades]

    avg_pcr = np.mean(pcr_list) if pcr_list else 0.0
    avg_pl = np.mean(pl_list) if pl_list else 0.0
    avg_realized = np.mean(realized_list) if realized_list else 0.0

    detected = avg_pcr < 0.35 and avg_pl > 1.5 * avg_realized
    detected_trades = [t.id for t in trades] if detected else []

    return PatternDetection(
        pattern_name="SEVERE_PROFIT_LEAKAGE",
        detected=detected,
        trade_ids=detected_trades,
        severity="CRITICAL",
        description=f"Severe profit leakage: avg PCR {avg_pcr:.2f} < 0.35, avg PL {avg_pl:.3f} > 1.5x realized {avg_realized:.3f}",
        count=len(detected_trades) if detected else 0,
    )


def detect_fat_tail_losses(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 8: Fat-Tail Losses.

    Kurtosis(P_realized) > 4.0 AND Skewness(P_realized) < -1.5
    """
    if len(trades) < 10:
        return PatternDetection(
            pattern_name="FAT_TAIL_LOSSES",
            detected=False,
            trade_ids=[],
            severity="HIGH",
            description="Insufficient data to detect fat-tail losses",
            count=0,
        )

    returns = [t.realized_pnl_pct for t in trades]
    kurtosis = stats.kurtosis(returns, fisher=True)
    skewness = stats.skew(returns)

    detected = kurtosis > 4.0 and skewness < -1.5
    detected_trades = [t.id for t in trades] if detected else []

    return PatternDetection(
        pattern_name="FAT_TAIL_LOSSES",
        detected=detected,
        trade_ids=detected_trades,
        severity="HIGH",
        description=f"Fat-tail losses detected: kurtosis {kurtosis:.2f} > 4.0, skewness {skewness:.2f} < -1.5",
        count=len(detected_trades) if detected else 0,
    )


def detect_regime_failure(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 9: Regime Failure.

    EV_regime < 0.0 AND Win Rate_regime < 0.30
    """
    from collections import defaultdict

    regime_stats = defaultdict(lambda: {"returns": [], "wins": 0, "total": 0})

    for trade in trades:
        regime = trade.regime or "UNKNOWN"
        regime_stats[regime]["returns"].append(trade.realized_pnl_pct)
        regime_stats[regime]["total"] += 1
        if trade.realized_pnl_pct > 0:
            regime_stats[regime]["wins"] += 1

    failed_regimes = []
    detected_trades = []

    for regime, stats in regime_stats.items():
        if stats["total"] < 5:
            continue

        ev = np.mean(stats["returns"])
        win_rate = stats["wins"] / stats["total"]

        if ev < 0.0 and win_rate < 0.30:
            failed_regimes.append(regime)
            detected_trades.extend([t.id for t in trades if (t.regime or "UNKNOWN") == regime])

    return PatternDetection(
        pattern_name="REGIME_FAILURE",
        detected=len(failed_regimes) > 0,
        trade_ids=detected_trades,
        severity="CRITICAL",
        description=f"Regime failure detected in: {', '.join(failed_regimes)}",
        count=len(detected_trades),
    )


def detect_confidence_failure(
    trades: List[TradeData],
) -> PatternDetection:
    """Pattern 10: Confidence Failure.

    ρ(Confidence, P_realized) <= 0.0 (Spearman correlation)
    """
    trades_with_confidence = [t for t in trades if t.confidence is not None]

    if len(trades_with_confidence) < 10:
        return PatternDetection(
            pattern_name="CONFIDENCE_FAILURE",
            detected=False,
            trade_ids=[],
            severity="HIGH",
            description="Insufficient data to detect confidence failure",
            count=0,
        )

    confidence_scores = [t.confidence for t in trades_with_confidence]
    returns = [t.realized_pnl_pct for t in trades_with_confidence]

    correlation, p_value = stats.spearmanr(confidence_scores, returns)

    detected = correlation <= 0.0
    detected_trades = [t.id for t in trades_with_confidence] if detected else []

    return PatternDetection(
        pattern_name="CONFIDENCE_FAILURE",
        detected=detected,
        trade_ids=detected_trades,
        severity="CRITICAL",
        description=f"Confidence failure: Spearman ρ = {correlation:.3f} <= 0.0 (p={p_value:.3f})",
        count=len(detected_trades) if detected else 0,
    )


def detect_execution_drift(
    trades: List[TradeData],
    window_size: int = 50,
) -> PatternDetection:
    """Pattern 11: Execution Drift.

    EE_t < EE_t-1 - 1.96 × SD(EE_t-1)

    Note: Requires time-series tracking of EE. Current implementation uses windowed comparison.
    """
    if len(trades) < window_size * 2:
        return PatternDetection(
            pattern_name="EXECUTION_DRIFT",
            detected=False,
            trade_ids=[],
            severity="MEDIUM",
            description="Insufficient data to detect execution drift",
            count=0,
        )

    from .execution_metrics import compute_execution_efficiency

    ee_series = [compute_execution_efficiency(t) for t in trades]

    ee_prev = ee_series[:window_size]
    ee_current = ee_series[window_size : window_size * 2]

    ee_prev_mean = np.mean(ee_prev)
    ee_prev_std = np.std(ee_prev)
    ee_current_mean = np.mean(ee_current)

    threshold = ee_prev_mean - 1.96 * ee_prev_std
    detected = ee_current_mean < threshold

    detected_trades = [trades[i].id for i in range(window_size, window_size * 2)] if detected else []

    return PatternDetection(
        pattern_name="EXECUTION_DRIFT",
        detected=detected,
        trade_ids=detected_trades,
        severity="MEDIUM",
        description=f"Execution drift detected: EE dropped from {ee_prev_mean:.3f} to {ee_current_mean:.3f} (threshold {threshold:.3f})",
        count=len(detected_trades),
    )


def detect_all_patterns(trades: List[TradeData]) -> List[PatternDetection]:
    """Run all pattern detectors and return results."""
    return [
        detect_trailing_too_early(trades),
        detect_trailing_too_late(trades),
        detect_sl_too_tight(trades),
        detect_sl_too_wide(trades),
        detect_tp_too_close(trades),
        detect_tp_too_far(trades),
        detect_severe_profit_leakage(trades),
        detect_fat_tail_losses(trades),
        detect_regime_failure(trades),
        detect_confidence_failure(trades),
        detect_execution_drift(trades),
    ]
