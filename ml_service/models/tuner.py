"""Hyperparameter tuning for XGBoost and LightGBM using Optuna."""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import f1_score

from ..utils.logger import get_logger

logger = get_logger()


def _objective_xgboost(
    trial: optuna.Trial,
    df_clean: pd.DataFrame,
    feature_cols: List[str],
    min_train_size: int,
    test_size: int,
    step_size: int,
) -> float:
    """Optuna objective function for XGBoost."""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 8),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0.0, 1.0),
        'objective': 'multi:softmax',
        'num_class': 3,
        'random_state': 42,
    }

    fold_f1_scores = []
    start_idx = min_train_size

    while start_idx + test_size <= len(df_clean):
        train_end = start_idx
        test_start = start_idx
        test_end = start_idx + test_size

        X_train = df_clean[feature_cols].iloc[:train_end]
        y_train = df_clean['target'].iloc[:train_end]
        X_test = df_clean[feature_cols].iloc[test_start:test_end]
        y_test = df_clean['target'].iloc[test_start:test_end]

        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, verbose=False)
        y_pred = model.predict(X_test)

        f1 = f1_score(y_test, y_pred, average='weighted')
        fold_f1_scores.append(f1)

        start_idx += step_size

    return np.mean(fold_f1_scores)


def _objective_lightgbm(
    trial: optuna.Trial,
    df_clean: pd.DataFrame,
    feature_cols: List[str],
    min_train_size: int,
    test_size: int,
    step_size: int,
) -> float:
    """Optuna objective function for LightGBM."""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 8),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 20, 100),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
        'objective': 'multiclass',
        'num_class': 3,
        'random_state': 42,
        'verbose': -1,
    }

    fold_f1_scores = []
    start_idx = min_train_size

    while start_idx + test_size <= len(df_clean):
        train_end = start_idx
        test_start = start_idx
        test_end = start_idx + test_size

        X_train = df_clean[feature_cols].iloc[:train_end]
        y_train = df_clean['target'].iloc[:train_end]
        X_test = df_clean[feature_cols].iloc[test_start:test_end]
        y_test = df_clean['target'].iloc[test_start:test_end]

        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        f1 = f1_score(y_test, y_pred, average='weighted')
        fold_f1_scores.append(f1)

        start_idx += step_size

    return np.mean(fold_f1_scores)


def tune_hyperparameters(
    df: pd.DataFrame,
    feature_cols: List[str],
    model_type: str,
    n_trials: int = 50,
    min_train_size: int = 400,
    test_size: int = 50,
    step_size: int = 50,
) -> Dict:
    """
    Tune hyperparameters using Optuna Bayesian optimization.

    Args:
        df: DataFrame with features and target
        feature_cols: List of feature column names
        model_type: 'xgboost' or 'lightgbm'
        n_trials: Number of optimization trials
        min_train_size: Minimum training set size
        test_size: Test set size for walk-forward validation
        step_size: Step size for walk-forward validation

    Returns:
        Dictionary with best params, best score, and study info
    """
    df_clean = df[feature_cols + ['target']].dropna()

    logger.info(f"Starting hyperparameter tuning for {model_type}")
    logger.info(f"Trials: {n_trials}, Clean dataset: {len(df_clean)} rows")

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(direction='maximize')

    if model_type == 'xgboost':
        objective_fn = lambda trial: _objective_xgboost(
            trial, df_clean, feature_cols, min_train_size, test_size, step_size
        )
    elif model_type == 'lightgbm':
        objective_fn = lambda trial: _objective_lightgbm(
            trial, df_clean, feature_cols, min_train_size, test_size, step_size
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    start_time = time.time()
    study.optimize(objective_fn, n_trials=n_trials, show_progress_bar=True)
    elapsed_time = time.time() - start_time

    best_params = study.best_params
    best_score = study.best_value

    logger.info(f"Tuning complete: Best F1 = {best_score:.4f}")

    return {
        'model_type': model_type,
        'best_params': best_params,
        'best_f1': best_score,
        'n_trials': n_trials,
        'elapsed_seconds': elapsed_time,
    }


def save_tuned_params(
    params: Dict,
    symbol: str,
    timeframe: str,
) -> str:
    """Save tuned parameters to storage/tuned_params/."""
    storage_dir = Path(__file__).parent.parent / "storage" / "tuned_params"
    storage_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{symbol}_{timeframe}.json"
    filepath = storage_dir / filename

    with open(filepath, 'w') as f:
        json.dump(params, f, indent=2)

    logger.info(f"Tuned params saved to {filepath}")
    return str(filepath)


def load_tuned_params(symbol: str, timeframe: str) -> Optional[Dict]:
    """Load tuned parameters from storage/tuned_params/."""
    storage_dir = Path(__file__).parent.parent / "storage" / "tuned_params"
    filepath = storage_dir / f"{symbol}_{timeframe}.json"

    if not filepath.exists():
        return None

    with open(filepath, 'r') as f:
        params = json.load(f)

    return params


def get_baseline_f1(
    df: pd.DataFrame,
    feature_cols: List[str],
    model_type: str,
    min_train_size: int = 400,
    test_size: int = 50,
    step_size: int = 50,
) -> float:
    """Calculate baseline F1 score with default hyperparameters."""
    df_clean = df[feature_cols + ['target']].dropna()

    if model_type == 'xgboost':
        default_params = {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'objective': 'multi:softmax',
            'num_class': 3,
            'random_state': 42,
        }
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

    fold_f1_scores = []
    start_idx = min_train_size

    while start_idx + test_size <= len(df_clean):
        train_end = start_idx
        test_start = start_idx
        test_end = start_idx + test_size

        X_train = df_clean[feature_cols].iloc[:train_end]
        y_train = df_clean['target'].iloc[:train_end]
        X_test = df_clean[feature_cols].iloc[test_start:test_end]
        y_test = df_clean['target'].iloc[test_start:test_end]

        if model_type == 'xgboost':
            model = xgb.XGBClassifier(**default_params)
            model.fit(X_train, y_train, verbose=False)
        else:
            model = lgb.LGBMClassifier(**default_params)
            model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        f1 = f1_score(y_test, y_pred, average='weighted')
        fold_f1_scores.append(f1)

        start_idx += step_size

    return np.mean(fold_f1_scores)
