"""Configuration loader for ML trading system."""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class BinanceConfig:
    enabled: bool
    api_key: str
    api_secret: str
    symbols: List[str]


@dataclass
class YFinanceConfig:
    enabled: bool
    symbols: List[str]


@dataclass
class DataSourcesConfig:
    binance: BinanceConfig
    yfinance: YFinanceConfig


@dataclass
class ModelConfig:
    type: str
    target: str
    forward_periods: int
    train_test_split: float
    validation_method: str
    xgboost_params: Dict[str, Any]
    lightgbm_params: Dict[str, Any]


@dataclass
class Config:
    data_sources: DataSourcesConfig
    timeframes: List[str]
    features: Dict[str, Any]
    model: ModelConfig
    backtest: Dict[str, Any]
    api: Dict[str, Any]
    logging: Dict[str, Any]
    economic_calendar: Dict[str, Any]


def load_config(config_path: str = None) -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml file (defaults to config.yaml in ml_service directory)

    Returns:
        Config object with all settings
    """
    if config_path is None:
        # Try to find config.yaml relative to this file's location
        config_dir = Path(__file__).parent.parent
        config_path = config_dir / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    binance_cfg = BinanceConfig(
        enabled=raw_config["data_sources"]["binance"]["enabled"],
        api_key=raw_config["data_sources"]["binance"]["api_key"],
        api_secret=raw_config["data_sources"]["binance"]["api_secret"],
        symbols=raw_config["data_sources"]["binance"]["symbols"],
    )

    yfinance_cfg = YFinanceConfig(
        enabled=raw_config["data_sources"]["yfinance"]["enabled"],
        symbols=raw_config["data_sources"]["yfinance"]["symbols"],
    )

    data_sources = DataSourcesConfig(
        binance=binance_cfg,
        yfinance=yfinance_cfg,
    )

    model_cfg = ModelConfig(
        type=raw_config["model"]["type"],
        target=raw_config["model"]["target"],
        forward_periods=raw_config["model"]["forward_periods"],
        train_test_split=raw_config["model"]["train_test_split"],
        validation_method=raw_config["model"]["validation_method"],
        xgboost_params=raw_config["model"]["xgboost_params"],
        lightgbm_params=raw_config["model"]["lightgbm_params"],
    )

    return Config(
        data_sources=data_sources,
        timeframes=raw_config["timeframes"],
        features=raw_config["features"],
        model=model_cfg,
        backtest=raw_config["backtest"],
        api=raw_config["api"],
        logging=raw_config["logging"],
        economic_calendar=raw_config["economic_calendar"],
    )


def get_config() -> Config:
    """Get cached config instance."""
    if not hasattr(get_config, "_config"):
        get_config._config = load_config()
    return get_config._config


def get_forward_periods() -> int:
    """Single source of truth for the label / prediction horizon H.

    Every consumer (label generation, walk-forward purge/embargo, TP/SL
    optimizer max-hold, backtester max-hold, predictor signal validity)
    MUST go through this function. Hard-coded horizons elsewhere are bugs.

    Logs the active value and source path the first time it is called so
    drift between code and config is visible at startup.
    """
    cfg = get_config()
    value = int(cfg.model.forward_periods)

    if not getattr(get_forward_periods, "_announced", False):
        try:
            from .logger import get_logger
            source = Path(__file__).parent.parent / "config.yaml"
            get_logger().info(
                f"[horizon] forward_periods={value} (source: {source})"
            )
        except Exception:
            pass
        get_forward_periods._announced = True

    return value
