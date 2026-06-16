#!/usr/bin/env python3
"""Dataset retention audit - track row loss through feature engineering pipeline.

Tracks row count after every feature engineering step to identify data loss causes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

from ml_service.data.database import get_database
from ml_service.features.price_action import (
    identify_swing_points,
    detect_trend_structure,
    find_support_resistance,
    detect_engulfing,
    detect_doji,
    detect_hammer,
    detect_shooting_star,
)
from ml_service.features.indicators import (
    add_ema_indicators,
    add_rsi,
    add_macd,
    add_atr,
    add_bollinger_bands,
    add_vwap,
    add_volume_ratio,
    add_ema_alignment_score,
    add_volume_profile,
    add_order_flow_features,
)
from ml_service.features.regime import (
    classify_volatility_regime,
    classify_trend_regime,
    create_market_phase,
    add_cross_pair_correlation,
    add_usdt_dominance_features,
)
from ml_service.features.funding_rate import add_funding_rate_features
from ml_service.models.trainer import create_target_variable, get_feature_columns
from ml_service.utils.config import get_forward_periods
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()


class RetentionTracker:
    def __init__(self):
        self.steps: List[Dict] = []
        self.current_rows = 0

    def track(self, step_name: str, df: pd.DataFrame, before_rows: int = None):
        if before_rows is None:
            before_rows = self.current_rows

        after_rows = len(df)
        lost = before_rows - after_rows
        loss_pct = (lost / before_rows * 100) if before_rows > 0 else 0

        self.steps.append({
            'step': step_name,
            'rows_before': before_rows,
            'rows_after': after_rows,
            'rows_lost': lost,
            'loss_pct': loss_pct,
            'nan_columns': df.isna().sum().to_dict(),
            'total_nans': df.isna().sum().sum(),
        })

        self.current_rows = after_rows
        return df


def load_data(symbol: str, timeframe: str, limit: int = 2000):
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))

    if df.empty:
        return None

    return df.sort_values('timestamp').reset_index(drop=True)


def audit_pipeline(symbol: str, timeframe: str):
    tracker = RetentionTracker()

    logger.info(f"Starting retention audit for {symbol} {timeframe}")

    # Load raw data
    df = load_data(symbol, timeframe, limit=2000)
    if df is None:
        logger.error(f"Failed to load data for {symbol} {timeframe}")
        return None

    initial_rows = len(df)
    tracker.current_rows = initial_rows
    tracker.track("0. Raw OHLCV data", df, before_rows=initial_rows)

    # Price Action Features
    df = identify_swing_points(df, lookback=10)
    tracker.track("1. Swing points (lookback=10)", df)

    df = detect_trend_structure(df)
    tracker.track("2. Trend structure", df)

    df = find_support_resistance(df, window=50)
    tracker.track("3. Support/Resistance (window=50)", df)

    df = detect_engulfing(df)
    tracker.track("4. Engulfing patterns", df)

    df = detect_doji(df)
    tracker.track("5. Doji patterns", df)

    df = detect_hammer(df)
    tracker.track("6. Hammer patterns", df)

    df = detect_shooting_star(df)
    tracker.track("7. Shooting star patterns", df)

    # Technical Indicators
    df = add_ema_indicators(df, periods=[9, 21, 50, 200])
    tracker.track("8. EMA indicators (9,21,50,200)", df)

    df = add_rsi(df, period=14)
    tracker.track("9. RSI (period=14)", df)

    df = add_macd(df, fast=12, slow=26, signal=9)
    tracker.track("10. MACD (12,26,9)", df)

    df = add_atr(df, period=14)
    tracker.track("11. ATR (period=14)", df)

    df = add_bollinger_bands(df, period=20, std=2.0)
    tracker.track("12. Bollinger Bands (20,2.0)", df)

    df = add_vwap(df)
    tracker.track("13. VWAP", df)

    df = add_volume_ratio(df, period=20)
    tracker.track("14. Volume ratio (period=20)", df)

    df = add_ema_alignment_score(df, periods=[9, 21, 50, 200])
    tracker.track("15. EMA alignment score", df)

    df = add_volume_profile(df, window=50, price_buckets=20)
    tracker.track("16. Volume profile (window=50)", df)

    df = add_order_flow_features(df, delta_ma_period=10, cumulative_delta_window=20)
    tracker.track("17. Order flow features", df)

    # Regime Features
    df = classify_volatility_regime(df, atr_window=50)
    tracker.track("18. Volatility regime (atr_window=50)", df)

    df = classify_trend_regime(df, adx_period=14)
    tracker.track("19. Trend regime (adx=14)", df)

    df = create_market_phase(df)
    tracker.track("20. Market phase", df)

    # Correlation features (without external data for audit)
    df = add_cross_pair_correlation(df, btc_df=None, spy_df=None, window=20)
    tracker.track("21. Cross-pair correlation (window=20)", df)

    # USDT dominance features (without external data)
    df = add_usdt_dominance_features(df, btc_df=None, eth_df=None, dominance_df=None, window=24)
    tracker.track("22. USDT dominance features (window=24)", df)

    # Funding rate features
    df = add_funding_rate_features(df, symbol=symbol, ma_period=8)
    tracker.track("23. Funding rate features (ma=8)", df)

    # Target generation
    H = get_forward_periods()
    df = create_target_variable(df, forward_periods=H, long_threshold=0.005, short_threshold=-0.005)
    tracker.track(f"24. Target variable (H={H})", df)

    # Feature column selection + dropna
    feature_cols = get_feature_columns(df)
    before_dropna = len(df)
    df_clean = df[feature_cols + ['target']].dropna()
    tracker.track("25. Feature selection + dropna", df_clean, before_rows=before_dropna)

    return tracker


def print_report(tracker: RetentionTracker, symbol: str, timeframe: str):
    print()
    print("=" * 120)
    print(f"DATASET RETENTION AUDIT: {symbol} {timeframe}")
    print("=" * 120)
    print()

    # Main table
    header = ['Step', 'Rows Before', 'Rows After', 'Rows Lost', 'Loss %']
    widths = [50, 12, 12, 12, 10]

    def fmt_row(values):
        return '  '.join(str(v).ljust(w) if i == 0 else str(v).rjust(w)
                        for i, (v, w) in enumerate(zip(values, widths)))

    print(fmt_row(header))
    print('-' * sum(widths) + '-' * (len(widths) - 1) * 2)

    for step in tracker.steps:
        print(fmt_row([
            step['step'],
            step['rows_before'],
            step['rows_after'],
            step['rows_lost'],
            f"{step['loss_pct']:.2f}%"
        ]))

    # Summary
    initial = tracker.steps[0]['rows_before']
    final = tracker.steps[-1]['rows_after']
    total_lost = initial - final
    total_loss_pct = (total_lost / initial * 100) if initial > 0 else 0

    print()
    print("=" * 120)
    print(f"SUMMARY: {initial} → {final} rows ({total_lost} lost, {total_loss_pct:.2f}% total loss)")
    print("=" * 120)
    print()

    # Top causes analysis
    print("TOP 5 CAUSES OF DATA LOSS")
    print("=" * 120)
    print()

    losses = [(s['step'], s['rows_lost'], s['loss_pct']) for s in tracker.steps if s['rows_lost'] > 0]
    losses.sort(key=lambda x: x[1], reverse=True)

    for i, (step, lost, pct) in enumerate(losses[:5], 1):
        print(f"{i}. {step}")
        print(f"   Lost: {lost} rows ({pct:.2f}%)")
        print()

    # NaN analysis for worst offenders
    print()
    print("NaN ANALYSIS FOR TOP LOSS STEPS")
    print("=" * 120)
    print()

    for step_name, _, _ in losses[:5]:
        step_data = next(s for s in tracker.steps if s['step'] == step_name)
        nan_cols = {k: v for k, v in step_data['nan_columns'].items() if v > 0}

        if nan_cols or step_data['total_nans'] > 0:
            print(f"{step_name}:")
            print(f"  Total NaN values: {step_data['total_nans']}")
            if nan_cols:
                print(f"  Columns with NaN:")
                for col, count in sorted(nan_cols.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"    {col}: {count}")
            print()

    # Recommendations
    print()
    print("RECOMMENDATIONS")
    print("=" * 120)
    print()

    recommendations = []

    # Analyze causes
    for step_name, lost, pct in losses:
        if 'EMA' in step_name and 'period=200' in step_name.lower():
            recommendations.append({
                'issue': 'EMA-200 warmup period (200 bars)',
                'impact': f'{lost} rows ({pct:.2f}%)',
                'fix': 'Reduce max EMA period to 100 or use adaptive periods based on data size',
                'priority': 'HIGH'
            })

        elif 'Volume profile' in step_name and 'window=50' in step_name:
            recommendations.append({
                'issue': 'Volume profile lookback window (50 bars)',
                'impact': f'{lost} rows ({pct:.2f}%)',
                'fix': 'Reduce window to 30 or make adaptive; consider excluding if low value',
                'priority': 'MEDIUM'
            })

        elif 'Support/Resistance' in step_name:
            recommendations.append({
                'issue': 'S/R detection warmup (50 bars)',
                'impact': f'{lost} rows ({pct:.2f}%)',
                'fix': 'Reduce window to 30; S/R is excluded from training anyway',
                'priority': 'LOW'
            })

        elif 'Volatility regime' in step_name and 'atr_window=50' in step_name:
            recommendations.append({
                'issue': 'Volatility regime rolling mean (50 bars)',
                'impact': f'{lost} rows ({pct:.2f}%)',
                'fix': 'Reduce atr_window to 30',
                'priority': 'MEDIUM'
            })

        elif 'Target variable' in step_name:
            H = get_forward_periods()
            recommendations.append({
                'issue': f'Target generation drops last H={H} rows',
                'impact': f'{lost} rows ({pct:.2f}%)',
                'fix': 'Unavoidable (labels need future data); consider if H=12 is optimal',
                'priority': 'LOW'
            })

        elif 'dropna' in step_name.lower():
            recommendations.append({
                'issue': 'Final dropna removes all rows with any NaN in selected features',
                'impact': f'{lost} rows ({pct:.2f}%)',
                'fix': 'Cumulative effect of all prior NaN-producing steps; address root causes above',
                'priority': 'HIGH'
            })

    # Deduplicate and print
    seen = set()
    unique_recs = []
    for rec in recommendations:
        if rec['issue'] not in seen:
            seen.add(rec['issue'])
            unique_recs.append(rec)

    for i, rec in enumerate(unique_recs[:5], 1):
        print(f"{i}. [{rec['priority']}] {rec['issue']}")
        print(f"   Impact: {rec['impact']}")
        print(f"   Fix: {rec['fix']}")
        print()


def main():
    symbol = 'BTCUSDT'
    timeframe = '1h'

    tracker = audit_pipeline(symbol, timeframe)

    if tracker:
        print_report(tracker, symbol, timeframe)


if __name__ == '__main__':
    main()
