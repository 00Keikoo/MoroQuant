"""Technical Indicator Calculator - Sprint 3.9B-3B

Adapter layer connecting FeatureCalculator interface to ml_service.features.indicators.
Maintains ADR-024 compliance with deterministic, pure-functional calculation.
"""

import pandas as pd
import numpy as np
from typing import Tuple
from ml_service.research.strategy.features.calculator.interfaces import FeatureCalculator
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.features.indicators import add_all_indicators


class TechnicalIndicatorCalculator(FeatureCalculator):
    """Technical indicator calculator using pandas-ta via add_all_indicators.

    Converts FeatureContext window to DataFrame, calculates indicators,
    and returns feature tuple. Pure function with no external dependencies.
    """

    def __init__(
        self,
        ema_periods: Tuple[int, ...] = (9, 21, 50, 200),
        rsi_period: int = 14,
        macd_params: Tuple[int, int, int] = (12, 26, 9),
        atr_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_period: int = 20,
    ):
        """Initialize calculator with indicator parameters.

        Args:
            ema_periods: EMA periods to calculate
            rsi_period: RSI period
            macd_params: MACD (fast, slow, signal) parameters
            atr_period: ATR period
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation
            volume_period: Volume ratio period
        """
        self.ema_periods = ema_periods
        self.rsi_period = rsi_period
        self.macd_params = macd_params
        self.atr_period = atr_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.volume_period = volume_period

    def calculate(self, context: FeatureContext) -> Tuple[Tuple[str, float], ...]:
        """Calculate technical indicators from context.

        Converts MarketSnapshot window to OHLCV DataFrame, applies indicators,
        and extracts latest row as feature tuple.

        Args:
            context: Immutable feature context with market window

        Returns:
            Tuple of (feature_name, feature_value) pairs from latest snapshot
        """
        if not context.window:
            return tuple()

        df = self._convert_to_dataframe(context.window)

        if df.empty or len(df) < 2:
            return tuple()

        df = add_all_indicators(
            df,
            ema_periods=list(self.ema_periods),
            rsi_period=self.rsi_period,
            macd_params=self.macd_params,
            atr_period=self.atr_period,
            bb_period=self.bb_period,
            bb_std=self.bb_std,
            volume_period=self.volume_period,
        )

        return self._extract_features(df)

    def _convert_to_dataframe(self, window: Tuple) -> pd.DataFrame:
        """Convert MarketSnapshot window to OHLCV DataFrame.

        Uses mid_price as close, derives high/low from bid/ask if available,
        otherwise uses mid_price for all OHLC values.

        Args:
            window: Tuple of MarketSnapshot objects

        Returns:
            DataFrame with timestamp index and OHLCV columns
        """
        records = []
        for snapshot in window:
            high = snapshot.ask if snapshot.ask is not None else snapshot.mid_price
            low = snapshot.bid if snapshot.bid is not None else snapshot.mid_price

            if high < low:
                high, low = low, high

            records.append({
                'timestamp': snapshot.timestamp,
                'open': snapshot.mid_price,
                'high': high,
                'low': low,
                'close': snapshot.mid_price,
                'volume': snapshot.volume if snapshot.volume is not None else 0.0,
            })

        df = pd.DataFrame(records)
        df = df.set_index('timestamp')
        df = df.sort_index()

        return df

    def _extract_features(self, df: pd.DataFrame) -> Tuple[Tuple[str, float], ...]:
        """Extract latest row features as tuple.

        Filters out NaN values and returns only finite numeric features.

        Args:
            df: DataFrame with calculated indicators

        Returns:
            Tuple of (feature_name, feature_value) pairs
        """
        if df.empty:
            return tuple()

        last_row = df.iloc[-1]

        features = []
        for col_name, value in last_row.items():
            if col_name in ('open', 'high', 'low', 'close', 'volume'):
                continue

            if pd.notna(value) and np.isfinite(value):
                features.append((col_name, float(value)))

        return tuple(features)
