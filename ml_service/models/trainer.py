"""ML model training pipeline with walk-forward validation."""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, List
import pickle

import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import f1_score, classification_report

from ..utils.logger import get_logger
from ..utils.config import get_config, get_forward_periods
from ..features.price_action import add_price_action_features
from ..features.indicators import add_all_indicators
from ..features.regime import add_regime_features
from ..features.funding_rate import add_funding_rate_features

logger = get_logger()


def create_target_variable(
    df: pd.DataFrame,
    forward_periods: int = None,
    long_threshold: float = 0.005,
    short_threshold: float = -0.005,
) -> pd.DataFrame:
    """
    Create target variable: forward return classification.

    CRITICAL: This uses FUTURE data, so must be shifted correctly.
    Target at row N = return from N to N+forward_periods.

    Args:
        df: DataFrame with close prices
        forward_periods: Number of periods ahead to calculate return
        long_threshold: Threshold for long signal (e.g., 0.005 = 0.5%)
        short_threshold: Threshold for short signal (e.g., -0.005 = -0.5%)

    Returns:
        DataFrame with target column (0=short, 1=neutral, 2=long)
    """
    if forward_periods is None:
        forward_periods = get_forward_periods()

    df = df.copy()

    future_close = df['close'].shift(-forward_periods)
    forward_return = (future_close - df['close']) / df['close']

    df['target'] = 1  # neutral
    df.loc[forward_return > long_threshold, 'target'] = 2  # long
    df.loc[forward_return < short_threshold, 'target'] = 0  # short

    df = df[:-forward_periods]

    return df


def prepare_features(
    df: pd.DataFrame,
    symbol: str,
    btc_df: pd.DataFrame = None,
    eth_df: pd.DataFrame = None,
    spy_df: pd.DataFrame = None,
    dominance_df: pd.DataFrame = None,
    ema_periods: list = None,
) -> pd.DataFrame:
    """
    Combine all feature engineering modules.

    Args:
        df: Raw OHLCV DataFrame
        symbol: Trading symbol (for funding rate features)
        btc_df: Optional BTCUSDT DataFrame for BTC correlation
        eth_df: Optional ETHUSDT DataFrame for USDT dominance features
        spy_df: Optional ES_proxy DataFrame for risk-on/off correlation
        dominance_df: Optional market dominance data from CoinGecko
        ema_periods: List of EMA periods (auto-adjusted if None)

    Returns:
        DataFrame with all features added
    """
    # Auto-adjust EMA periods based on available data
    if ema_periods is None:
        data_size = len(df)
        if data_size < 250:
            ema_periods = [9, 21, 50, 100]  # Shorter periods for limited data
        else:
            ema_periods = [9, 21, 50, 200]  # Standard periods

    df = add_price_action_features(df, swing_lookback=10, sr_window=50)
    df = add_all_indicators(df, ema_periods=ema_periods)
    df = add_regime_features(df, btc_df=btc_df, eth_df=eth_df, spy_df=spy_df, dominance_df=dominance_df)
    df = add_funding_rate_features(df, symbol=symbol)

    return df


def get_feature_columns(df: pd.DataFrame = None, ema_periods: list = None) -> List[str]:
    """
    Define explicit feature list (no raw OHLCV or timestamp).

    Excludes features with high NaN rates:
    - nearest_support/nearest_resistance (warmup period)
    - vwap/price_to_vwap (requires DatetimeIndex)
    - btc_es_correlation (timestamp alignment issues)

    Args:
        df: Optional DataFrame to detect available columns
        ema_periods: List of EMA periods used (auto-detected from df if None)

    Returns:
        List of feature column names
    """
    # Auto-detect EMA periods from dataframe columns if not provided
    if ema_periods is None and df is not None:
        ema_periods = []
        for col in df.columns:
            if col.startswith('ema_') and not col.endswith(('_slope', '_direction')):
                try:
                    period = int(col.split('_')[1])
                    ema_periods.append(period)
                except (ValueError, IndexError):
                    # Skip columns like ema_alignment_score
                    continue
        ema_periods = sorted(set(ema_periods))

    if ema_periods is None:
        ema_periods = [9, 21, 50, 200]  # Default fallback

    features = [
        # Price action
        'swing_high', 'swing_low', 'trend',
        'bullish_engulfing', 'bearish_engulfing', 'doji', 'hammer', 'shooting_star',
    ]

    # Add EMA features dynamically
    for period in ema_periods:
        features.extend([
            f'ema_{period}', f'ema_{period}_slope', f'ema_{period}_direction'
        ])

    features.extend([
        # Momentum
        'rsi', 'macd', 'macd_signal', 'macd_histogram',

        # Volatility
        'atr', 'bb_upper', 'bb_middle', 'bb_lower', 'bb_bandwidth', 'bb_percent',

        # Volume
        'volume_ratio',

        # Volume Profile
        'poc_distance', 'vah_distance', 'val_distance', 'price_in_value_area', 'volume_nodes',

        # Regime
        'adx', 'ema_alignment_score',

        # Cross-pair Correlation
        'btc_correlation', 'spy_correlation',

        # USDT Dominance (risk-off detection)
        'btc_dominance_proxy', 'usdt_flight_signal', 'risk_off_regime',
        'usdt_dominance', 'usdt_dominance_1h_change',

        # Funding Rate (crypto-specific)
        'funding_rate', 'funding_rate_ma', 'funding_extreme', 'funding_sentiment',
    ])

    return features


def walk_forward_validation(
    df: pd.DataFrame,
    feature_cols: List[str],
    min_train_size: int = 400,
    test_size: int = 50,
    step_size: int = 50,
    xgb_params: Dict = None,
    lgb_params: Dict = None,
    forward_periods: int = 0,
    purge: bool = False,
) -> Tuple[List[Dict], pd.DataFrame]:
    """
    Perform walk-forward validation.

    Args:
        df: DataFrame with features and target
        feature_cols: List of feature column names
        min_train_size: Minimum training set size
        test_size: Test set size
        step_size: Step size for rolling window
        xgb_params: Optional custom XGBoost hyperparameters
        lgb_params: Optional custom LightGBM hyperparameters
        forward_periods: Label horizon H. Used for purge/embargo when purge=True.
        purge: If True, drop H rows between train and test (purge) and skip H
            rows after each test window before the next fold begins (embargo).
            Both prevent label-overlap leakage from forward-return targets.

    Returns:
        Tuple of (fold_results, feature_importance_df)
    """
    df_clean = df[feature_cols + ['target']].dropna()

    logger.info(f"Clean dataset: {len(df_clean)} rows after dropping NaN")

    fold_results = []
    all_feature_importance = []

    start_idx = min_train_size
    fold_num = 0

    xgb_default = {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'objective': 'multi:softmax',
        'num_class': 3,
        'random_state': 42,
    }
    xgb_config = {**xgb_default, **(xgb_params or {})}

    lgb_default = {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'objective': 'multiclass',
        'num_class': 3,
        'random_state': 42,
        'verbose': -1,
    }
    lgb_config = {**lgb_default, **(lgb_params or {})}

    purge_size = forward_periods if purge else 0
    embargo_size = forward_periods if purge else 0

    while start_idx + test_size <= len(df_clean):
        fold_num += 1

        train_end = start_idx - purge_size
        test_start = start_idx
        test_end = start_idx + test_size

        if train_end < 1:
            logger.warning(f"Fold {fold_num}: train_end={train_end} after purge — skipping")
            start_idx += step_size + embargo_size
            continue

        X_train = df_clean[feature_cols].iloc[:train_end]
        y_train = df_clean['target'].iloc[:train_end]

        X_test = df_clean[feature_cols].iloc[test_start:test_end]
        y_test = df_clean['target'].iloc[test_start:test_end]

        logger.info(
            f"Fold {fold_num}: train={len(X_train)}, test={len(X_test)}, "
            f"purge={purge_size}, embargo={embargo_size}"
        )

        xgb_model = xgb.XGBClassifier(**xgb_config)
        xgb_model.fit(X_train, y_train)
        xgb_pred = xgb_model.predict(X_test)
        xgb_f1 = f1_score(y_test, xgb_pred, average='weighted')

        lgb_model = lgb.LGBMClassifier(**lgb_config)
        lgb_model.fit(X_train, y_train)
        lgb_pred = lgb_model.predict(X_test)
        lgb_f1 = f1_score(y_test, lgb_pred, average='weighted')

        if xgb_f1 >= lgb_f1:
            best_model = xgb_model
            best_pred = xgb_pred
            best_f1 = xgb_f1
            model_type = 'xgboost'
        else:
            best_model = lgb_model
            best_pred = lgb_pred
            best_f1 = lgb_f1
            model_type = 'lightgbm'

        f1_per_class = f1_score(y_test, best_pred, average=None, labels=[0, 1, 2], zero_division=0)

        fold_results.append({
            'fold': fold_num,
            'model_type': model_type,
            'f1_weighted': best_f1,
            'f1_short': f1_per_class[0] if len(f1_per_class) > 0 else 0.0,
            'f1_neutral': f1_per_class[1] if len(f1_per_class) > 1 else 0.0,
            'f1_long': f1_per_class[2] if len(f1_per_class) > 2 else 0.0,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'purge_size': purge_size,
            'embargo_size': embargo_size,
        })

        if model_type == 'xgboost':
            importance = best_model.feature_importances_
        else:
            importance = best_model.feature_importances_

        all_feature_importance.append(importance)

        start_idx += step_size + embargo_size

    avg_importance = np.mean(all_feature_importance, axis=0)
    feature_importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': avg_importance
    }).sort_values('importance', ascending=False)

    return fold_results, feature_importance_df


def train_final_model(
    df: pd.DataFrame,
    feature_cols: List[str],
    model_type: str = 'xgboost',
    custom_params: Dict = None,
) -> Tuple[object, Dict]:
    """
    Train final model on all available data.

    Args:
        df: DataFrame with features and target
        feature_cols: List of feature column names
        model_type: 'xgboost' or 'lightgbm'
        custom_params: Optional custom hyperparameters (from tuning)

    Returns:
        Tuple of (trained_model, metadata)
    """
    df_clean = df[feature_cols + ['target']].dropna()

    X = df_clean[feature_cols]
    y = df_clean['target']

    logger.info(f"Training final {model_type} model on {len(X)} samples")

    if model_type == 'xgboost':
        default_params = {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'objective': 'multi:softmax',
            'num_class': 3,
            'random_state': 42,
        }
        if custom_params:
            params = {**default_params, **custom_params}
            logger.info(f"Using tuned hyperparameters for XGBoost")
        else:
            params = default_params
        model = xgb.XGBClassifier(**params)
    else:
        default_params = {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'objective': 'multiclass',
            'num_class': 3,
            'random_state': 42,
            'verbose': -1,
        }
        if custom_params:
            params = {**default_params, **custom_params}
            logger.info(f"Using tuned hyperparameters for LightGBM")
        else:
            params = default_params
        model = lgb.LGBMClassifier(**params)

    model.fit(X, y)

    metadata = {
        'model_type': model_type,
        'feature_cols': feature_cols,
        'n_samples': len(X),
        'class_distribution': y.value_counts().to_dict(),
        'trained_at': datetime.now().isoformat(),
        'hyperparameters': params if custom_params else 'default',
    }

    return model, metadata


def save_model(
    model: object,
    metadata: Dict,
    symbol: str,
    timeframe: str,
) -> str:
    """
    Save trained model to storage/models/.

    Args:
        model: Trained model object
        metadata: Model metadata
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Path to saved model file
    """
    models_dir = Path(__file__).parent.parent / "storage" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timeframe}_{metadata['model_type']}_{timestamp}.pkl"
    filepath = models_dir / filename

    model_package = {
        'model': model,
        'metadata': metadata,
    }

    with open(filepath, 'wb') as f:
        pickle.dump(model_package, f)

    logger.info(f"Model saved to {filepath}")

    return str(filepath)


def train_model(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    btc_df: pd.DataFrame = None,
    eth_df: pd.DataFrame = None,
    spy_df: pd.DataFrame = None,
    dominance_df: pd.DataFrame = None,
    forward_periods: int = None,
    long_threshold: float = 0.005,
    short_threshold: float = -0.005,
) -> Dict:
    """
    Complete training pipeline.

    Args:
        df: Raw OHLCV DataFrame
        symbol: Trading symbol
        timeframe: Timeframe
        btc_df: Optional BTCUSDT DataFrame for BTC correlation
        eth_df: Optional ETHUSDT DataFrame for USDT dominance features
        spy_df: Optional ES_proxy DataFrame for risk-on/off correlation
        dominance_df: Optional market dominance data from CoinGecko
        forward_periods: Forward periods for target
        long_threshold: Long signal threshold
        short_threshold: Short signal threshold

    Returns:
        Training results dictionary
    """
    from .tuner import load_tuned_params

    if forward_periods is None:
        forward_periods = get_forward_periods()

    logger.info(f"Starting training for {symbol} {timeframe} (forward_periods={forward_periods})")

    tuned_config = load_tuned_params(symbol, timeframe)
    if tuned_config:
        logger.info(f"Found tuned hyperparameters for {symbol} {timeframe}")
        logger.info(f"Model type: {tuned_config['model_type']}, F1: {tuned_config['best_f1']:.4f}")

    df = prepare_features(df, symbol=symbol, btc_df=btc_df, eth_df=eth_df, spy_df=spy_df, dominance_df=dominance_df)

    df = create_target_variable(
        df,
        forward_periods=forward_periods,
        long_threshold=long_threshold,
        short_threshold=short_threshold,
    )

    feature_cols = get_feature_columns(df)

    df_clean = df[feature_cols + ['target']].dropna()
    clean_size = len(df_clean)

    if clean_size < 100:
        min_train_size = int(clean_size * 0.6)
        test_size = int(clean_size * 0.15)
        step_size = test_size
    elif clean_size < 300:
        min_train_size = int(clean_size * 0.7)
        test_size = int(clean_size * 0.15)
        step_size = test_size
    else:
        min_train_size = 400
        test_size = 50
        step_size = 50

    xgb_params = None
    lgb_params = None
    if tuned_config:
        if tuned_config['model_type'] == 'xgboost':
            xgb_params = tuned_config['best_params']
        else:
            lgb_params = tuned_config['best_params']

    fold_results, feature_importance = walk_forward_validation(
        df, feature_cols,
        min_train_size=min_train_size,
        test_size=test_size,
        step_size=step_size,
        xgb_params=xgb_params,
        lgb_params=lgb_params,
        forward_periods=forward_periods,
        purge=True,
    )

    if len(fold_results) == 0:
        raise ValueError(f"Insufficient data for training: {clean_size} clean rows, need at least {min_train_size + test_size}")

    avg_f1_short = np.mean([r['f1_short'] for r in fold_results])
    avg_f1_neutral = np.mean([r['f1_neutral'] for r in fold_results])
    avg_f1_long = np.mean([r['f1_long'] for r in fold_results])
    avg_f1_weighted = np.mean([r['f1_weighted'] for r in fold_results])

    logger.info(f"Walk-forward validation complete: {len(fold_results)} folds")
    logger.info(f"Avg F1 - Short: {avg_f1_short:.3f}, Neutral: {avg_f1_neutral:.3f}, Long: {avg_f1_long:.3f}")

    best_model_type = fold_results[-1]['model_type']

    custom_params = None
    if tuned_config and tuned_config['model_type'] == best_model_type:
        custom_params = tuned_config['best_params']

    final_model, metadata = train_final_model(df, feature_cols, model_type=best_model_type, custom_params=custom_params)

    model_path = save_model(final_model, metadata, symbol, timeframe)

    results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'n_folds': len(fold_results),
        'avg_f1_short': avg_f1_short,
        'avg_f1_neutral': avg_f1_neutral,
        'avg_f1_long': avg_f1_long,
        'avg_f1_weighted': avg_f1_weighted,
        'fold_results': fold_results,
        'feature_importance': feature_importance,
        'model_path': model_path,
        'model_type': best_model_type,
        'used_tuned_params': custom_params is not None,
    }

    return results
