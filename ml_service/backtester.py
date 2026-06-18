"""Walk-forward backtesting engine for ML trading signals."""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
import pickle

from utils.logger import get_logger
from utils.config import get_forward_periods
from data.database import get_database
from models.trainer import prepare_features
from models.predictor import load_latest_model

logger = get_logger()


class BacktestEngine:
    """Walk-forward backtesting with no lookahead bias."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        initial_capital: float = 10000.0,
        fee_rate: float = 0.0004,
        max_hold_candles: int = None,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.max_hold_candles = max_hold_candles if max_hold_candles is not None else get_forward_periods()

        self.capital = initial_capital
        self.position = None
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []

        self.model_package = None

    def load_model(self) -> bool:
        """Load trained model for the symbol/timeframe."""
        self.model_package = load_latest_model(self.symbol, self.timeframe)

        if self.model_package is None:
            logger.error(f"No trained model found for {self.symbol} {self.timeframe}")
            return False

        logger.info(f"Loaded model: {self.model_package['metadata']['model_type']}")
        return True

    def load_data(self) -> pd.DataFrame:
        """Load historical OHLCV data from database."""
        db = get_database()

        with db.get_connection() as conn:
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn, params=(self.symbol, self.timeframe))

        if df.empty:
            logger.error(f"No data found for {self.symbol} {self.timeframe}")
            return None

        logger.info(f"Loaded {len(df)} candles for backtesting")
        return df

    def predict_signal(self, df: pd.DataFrame, current_idx: int) -> Optional[str]:
        """
        Predict signal for a specific candle using only data up to that point.

        Walk-forward approach: features at index N use only data from 0 to N.
        """
        if self.model_package is None:
            return None

        model = self.model_package['model']
        feature_cols = self.model_package['metadata']['feature_cols']

        df_slice = df.iloc[:current_idx + 1].copy()

        df_features = prepare_features(df_slice, symbol=self.symbol)

        missing_cols = [c for c in feature_cols if c not in df_features.columns]
        if missing_cols:
            return 'neutral'

        df_clean = df_features[feature_cols].dropna()

        if df_clean.empty:
            return None

        X_latest = df_clean.iloc[[-1]]

        if isinstance(model, dict) and 'xgb' in model and 'lgb' in model:
            xgb_proba = model['xgb'].predict_proba(X_latest)[0]
            lgb_proba = model['lgb'].predict_proba(X_latest)[0]
            prediction_proba = (xgb_proba + lgb_proba) / 2
            prediction = int(np.argmax(prediction_proba))
        else:
            prediction = model.predict(X_latest)[0]

        direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
        return direction_map[prediction]

    def execute_trade(
        self,
        action: str,
        price: float,
        timestamp: int,
        candle_idx: int,
    ) -> None:
        """Execute a trade (open or close position)."""
        if action == 'open_long':
            fee = self.capital * self.fee_rate
            self.position = {
                'type': 'long',
                'entry_price': price,
                'entry_timestamp': timestamp,
                'entry_idx': candle_idx,
                'capital': self.capital - fee,
            }
            logger.debug(f"LONG opened at {price:.2f} (idx {candle_idx})")

        elif action == 'open_short':
            fee = self.capital * self.fee_rate
            self.position = {
                'type': 'short',
                'entry_price': price,
                'entry_timestamp': timestamp,
                'entry_idx': candle_idx,
                'capital': self.capital - fee,
            }
            logger.debug(f"SHORT opened at {price:.2f} (idx {candle_idx})")

        elif action == 'close':
            if self.position is None:
                return

            entry_price = self.position['entry_price']
            position_capital = self.position['capital']

            if self.position['type'] == 'long':
                pnl_pct = (price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - price) / entry_price

            pnl = position_capital * pnl_pct
            fee = (position_capital + pnl) * self.fee_rate
            final_pnl = pnl - fee

            self.capital = position_capital + final_pnl

            trade = {
                'type': self.position['type'],
                'entry_price': entry_price,
                'entry_timestamp': self.position['entry_timestamp'],
                'entry_idx': self.position['entry_idx'],
                'exit_price': price,
                'exit_timestamp': timestamp,
                'exit_idx': candle_idx,
                'pnl': final_pnl,
                'pnl_pct': (final_pnl / position_capital) * 100,
                'hold_candles': candle_idx - self.position['entry_idx'],
            }

            self.trades.append(trade)
            self.position = None

            logger.debug(
                f"{trade['type'].upper()} closed at {price:.2f}, "
                f"PnL: ${final_pnl:.2f} ({trade['pnl_pct']:.2f}%)"
            )

    def run(self) -> Dict:
        """Run the backtest with vectorized feature computation."""
        logger.info(f"Starting backtest for {self.symbol} {self.timeframe}")

        if not self.load_model():
            return None

        df = self.load_data()
        if df is None or df.empty:
            return None

        warmup = 250
        if len(df) < warmup:
            logger.error(f"Insufficient data: need at least {warmup} candles")
            return None

        logger.info("Computing features for all candles (vectorized)...")
        df_features = prepare_features(df, symbol=self.symbol)

        model = self.model_package['model']
        feature_cols = self.model_package['metadata']['feature_cols']

        missing_cols = [c for c in feature_cols if c not in df_features.columns]
        if missing_cols:
            logger.error(f"Missing feature columns: {missing_cols}")
            return None

        df_features_clean = df_features[feature_cols].copy()

        logger.info("Generating predictions (batch)...")
        if isinstance(model, dict) and 'xgb' in model and 'lgb' in model:
            valid_mask = df_features_clean.notna().all(axis=1)
            predictions = np.full(len(df_features_clean), 1)

            if valid_mask.any():
                X_valid = df_features_clean[valid_mask]
                xgb_proba = model['xgb'].predict_proba(X_valid)
                lgb_proba = model['lgb'].predict_proba(X_valid)
                ensemble_proba = (xgb_proba + lgb_proba) / 2
                predictions[valid_mask] = np.argmax(ensemble_proba, axis=1)
        else:
            valid_mask = df_features_clean.notna().all(axis=1)
            predictions = np.full(len(df_features_clean), 1)

            if valid_mask.any():
                X_valid = df_features_clean[valid_mask]
                predictions[valid_mask] = model.predict(X_valid)

        direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
        signals = [direction_map.get(p, 'neutral') for p in predictions]

        logger.info(f"Simulating trades for {len(df) - warmup} candles...")
        for i in range(warmup, len(df)):
            row = df.iloc[i]
            signal = signals[i]

            self.equity_curve.append({
                'timestamp': int(row['timestamp']),
                'equity': self.capital,
                'signal': signal,
            })

            if self.position is not None:
                hold_duration = i - self.position['entry_idx']

                if self.position['type'] == 'long' and signal == 'short':
                    self.execute_trade('close', row['close'], row['timestamp'], i)
                elif self.position['type'] == 'short' and signal == 'long':
                    self.execute_trade('close', row['close'], row['timestamp'], i)
                elif hold_duration >= self.max_hold_candles:
                    self.execute_trade('close', row['close'], row['timestamp'], i)

            else:
                if signal == 'long':
                    self.execute_trade('open_long', row['close'], row['timestamp'], i)
                elif signal == 'short':
                    self.execute_trade('open_short', row['close'], row['timestamp'], i)

        if self.position is not None:
            last_row = df.iloc[-1]
            self.execute_trade('close', last_row['close'], last_row['timestamp'], len(df) - 1)

        metrics = self.calculate_metrics()

        results = {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
        }

        return results

    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics."""
        if not self.trades:
            return {
                'total_return_pct': 0,
                'win_rate_pct': 0,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'total_trades': 0,
                'avg_profit_per_trade': 0,
            }

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]

        win_rate_pct = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0

        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        equity_series = [e['equity'] for e in self.equity_curve]
        peak = equity_series[0]
        max_drawdown = 0
        for equity in equity_series:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_pct = max_drawdown * 100

        returns = [t['pnl_pct'] for t in self.trades]
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        avg_profit_per_trade = sum(t['pnl'] for t in self.trades) / len(self.trades)

        return {
            'total_return_pct': round(total_return_pct, 2),
            'win_rate_pct': round(win_rate_pct, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_trades': len(self.trades),
            'avg_profit_per_trade': round(avg_profit_per_trade, 2),
        }


def run_backtest(symbol: str, timeframe: str) -> Optional[Dict]:
    """Run backtest for a single symbol/timeframe."""
    engine = BacktestEngine(
        symbol=symbol,
        timeframe=timeframe,
        initial_capital=10000.0,
        fee_rate=0.0004,
    )

    results = engine.run()

    if results is None:
        return None

    storage_dir = Path(__file__).parent / "storage" / "backtest"
    storage_dir.mkdir(parents=True, exist_ok=True)

    equity_file = storage_dir / f"{symbol}_{timeframe}_equity.json"
    with open(equity_file, 'w') as f:
        json.dump(results['equity_curve'], f, indent=2)

    trades_file = storage_dir / f"{symbol}_{timeframe}_trades.csv"
    if results['trades']:
        trades_df = pd.DataFrame(results['trades'])
        trades_df.to_csv(trades_file, index=False)

    logger.info(f"Backtest results saved to {storage_dir}")

    return results


def print_backtest_summary(results: Dict) -> None:
    """Print backtest summary to terminal."""
    print("\n" + "=" * 80)
    print(f"BACKTEST RESULTS: {results['symbol']} {results['timeframe']}")
    print("=" * 80)

    metrics = results['metrics']

    print(f"\nPerformance Metrics:")
    print(f"  Total Return:        {metrics['total_return_pct']:>8.2f}%")
    print(f"  Win Rate:            {metrics['win_rate_pct']:>8.2f}%")
    print(f"  Profit Factor:       {metrics['profit_factor']:>8.2f}")
    print(f"  Max Drawdown:        {metrics['max_drawdown_pct']:>8.2f}%")
    print(f"  Sharpe Ratio:        {metrics['sharpe_ratio']:>8.2f}")
    print(f"  Total Trades:        {metrics['total_trades']:>8}")
    print(f"  Avg Profit/Trade:    ${metrics['avg_profit_per_trade']:>7.2f}")

    print("\n" + "=" * 80 + "\n")
