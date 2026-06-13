# ML Trading Intelligence System

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-orange?style=flat)](https://xgboost.ai/)
[![LightGBM](https://img.shields.io/badge/LightGBM-Gradient_Boosting-blue?style=flat)](https://lightgbm.readthedocs.io/)

Self-learning machine learning trading system that generates real-time trading signals for cryptocurrencies using XGBoost and LightGBM ensemble models with walk-forward validation.

## 🎯 Features

- **Dual-Model Ensemble** — XGBoost + LightGBM with automatic best-model selection
- **Walk-Forward Validation** — No lookahead bias, trained on past, tested on future
- **Hyperparameter Tuning** — Optuna Bayesian optimization (50+ trials per model)
- **Data-Driven TP/SL** — Take profit/stop loss levels optimized from backtest history
- **30+ Technical Indicators** — Price action, momentum, volatility, volume, regime detection
- **Multi-Timeframe Analysis** — 1h signals confirmed against 4h for higher confidence
- **Auto-Retrain Scheduler** — Models retrain daily at 2 AM to adapt to market changes
- **RESTful API** — FastAPI endpoints for signal generation and model management

## 📊 ML Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA INGESTION                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Binance API  →  OHLCV (536,000+ candles, 2 years)                │
│  CoinGecko    →  Market dominance, USDT flow detection            │
│  Yahoo Finance→  Macro context (ES/NQ/GC proxies)                 │
│                                                                     │
│  Storage: SQLite with indexed timestamp queries                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FEATURE ENGINEERING                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Price Action Features (8):                                        │
│    • Swing highs/lows              • S/R levels                    │
│    • Candlestick patterns          • Trend classification          │
│                                                                     │
│  Technical Indicators (15):                                        │
│    • EMA (9, 21, 50, 200)          • RSI (14)                      │
│    • MACD + histogram              • Bollinger Bands               │
│    • ATR                           • ADX (trend strength)          │
│                                                                     │
│  Volume Analysis (5):                                              │
│    • Volume ratio                  • VWAP                          │
│    • Volume profile (POC/VAH/VAL)  • Price in value area          │
│                                                                     │
│  Market Regime (4):                                                │
│    • Volatility state              • Trend direction               │
│    • EMA alignment score           • Market phase                  │
│                                                                     │
│  Cross-Pair Correlation (3):                                       │
│    • BTC correlation               • SPY correlation               │
│    • USDT dominance flow           • Risk-off signals              │
│                                                                     │
│  Crypto-Specific (3):                                              │
│    • Funding rate                  • Funding sentiment             │
│    • Funding extremes              • BTC dominance proxy           │
│                                                                     │
│  Total: 38 engineered features                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MODEL TRAINING                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Target Variable:                                                   │
│    forward_return = (price[t+12] - price[t]) / price[t]           │
│                                                                     │
│    Classification:                                                  │
│      LONG    → return > +0.5%                                      │
│      NEUTRAL → return between -0.5% and +0.5%                      │
│      SHORT   → return < -0.5%                                      │
│                                                                     │
│  Walk-Forward Validation:                                          │
│    ├─ Min train: 400 candles (auto-adjust for small datasets)     │
│    ├─ Test size: 50 candles                                       │
│    ├─ Step size: 50 candles (rolling window)                      │
│    └─ Folds: 5-10 depending on data availability                  │
│                                                                     │
│  Model Selection:                                                   │
│    ├─ Train both XGBoost and LightGBM each fold                   │
│    ├─ Select model with highest weighted F1 score                 │
│    └─ Final model trained on all available data                   │
│                                                                     │
│  Hyperparameters (default):                                        │
│    XGBoost:                         LightGBM:                      │
│      max_depth: 6                     max_depth: 6                 │
│      learning_rate: 0.1               learning_rate: 0.1           │
│      n_estimators: 100                n_estimators: 100            │
│      subsample: 0.8                   subsample: 0.8               │
│      colsample_bytree: 0.8            colsample_bytree: 0.8        │
│                                                                     │
│  Hyperparameter Tuning (Optuna):                                   │
│    ├─ Bayesian optimization (50 trials)                           │
│    ├─ Search space: n_estimators, max_depth, learning_rate, etc.  │
│    ├─ Objective: maximize walk-forward F1 score                   │
│    └─ Saves best params to storage/tuned_params/                  │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TP/SL OPTIMIZATION                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Analyze Backtest History:                                         │
│    For each historical trade:                                      │
│      • Calculate max favorable excursion (MFE)                     │
│      • Calculate max adverse excursion (MAE)                       │
│      • Normalize by ATR at entry                                   │
│                                                                     │
│  Optimal Multipliers:                                              │
│    TP_multiplier = median(MFE / ATR)                               │
│    SL_multiplier = median(MAE / ATR) × 1.2  (safety buffer)       │
│    Optimal_hold  = percentile_75(winning_trade_duration)           │
│                                                                     │
│  Fallback (no backtest data):                                      │
│    TP: 3.0 × ATR    SL: 1.5 × ATR    Hold: 12 candles             │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SIGNAL GENERATION                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Input: Latest OHLCV candle + engineered features                  │
│                                                                     │
│  Prediction:                                                        │
│    model.predict_proba(features) → [p_short, p_neutral, p_long]   │
│    direction = argmax(probabilities)                               │
│    confidence = max(probabilities) × 100                           │
│                                                                     │
│  Multi-Timeframe Check (1h signals only):                          │
│    if 1h_direction == 4h_direction:                                │
│        confidence × 1.15  (boost by 15%)                           │
│    else:                                                            │
│        confidence × 0.80  (reduce by 20%)                          │
│        mtf_conflict = True                                         │
│                                                                     │
│  TP/SL Calculation:                                                │
│    if direction == LONG:                                           │
│        TP = price + (ATR × TP_multiplier)                          │
│        SL = price - (ATR × SL_multiplier)                          │
│    elif direction == SHORT:                                        │
│        TP = price - (ATR × TP_multiplier)                          │
│        SL = price + (ATR × SL_multiplier)                          │
│                                                                     │
│  Output Signal:                                                     │
│    {                                                                │
│      direction: "long" | "short" | "neutral",                     │
│      confidence: 0-100,                                            │
│      price: current_price,                                         │
│      take_profit: TP_price,                                        │
│      stop_loss: SL_price,                                          │
│      atr: current_atr,                                             │
│      risk_reward: "1:2.0",                                         │
│      valid_until: timestamp + (optimal_hold × timeframe_hours),    │
│      tp_sl_source: "optimized" | "default",                        │
│      top_features: {top_5_important_features},                     │
│      mtf_conflict: boolean                                         │
│    }                                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Installation

```bash
cd ml_service
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys
```

### Fetch Data

```bash
# Fetch 2 years of data for all pairs
python cli.py fetch --all --days 730 --full-history

# Or fetch specific pair
python cli.py fetch --symbol BTCUSDT --timeframe 1h --days 730
```

### Train Models

```bash
# Train single pair
python cli.py train --symbol BTCUSDT --timeframe 1h

# Tune hyperparameters (Optuna)
python cli.py tune --symbol BTCUSDT --timeframe 1h --trials 50

# Train all pairs
python cli.py train --all --timeframe 1h
```

### Run Backtests & Optimize TP/SL

```bash
# Backtest single pair
python cli.py backtest --symbol BTCUSDT --timeframe 1h

# Backtest all pairs
python cli.py backtest --all

# Optimize TP/SL from backtest history
python cli.py optimize-tp-sl --symbol BTCUSDT --timeframe 1h
python cli.py optimize-tp-sl --all
```

### Generate Signals

```bash
# Generate signal for specific pair
python cli.py signal --symbol BTCUSDT --timeframe 1h --explain

# Start API server
python cli.py serve  # http://127.0.0.1:8000
```

## 📋 CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| **Data Management** |
| `fetch` | Fetch OHLCV data from Binance | `python cli.py fetch --symbol BTCUSDT --timeframe 1h --days 730` |
| `fetch --all` | Fetch all configured pairs | `python cli.py fetch --all --days 730 --full-history` |
| `db-info` | Show database statistics | `python cli.py db-info` |
| **Model Training** |
| `train` | Train model for symbol/timeframe | `python cli.py train --symbol BTCUSDT --timeframe 1h` |
| `train --all` | Train all configured pairs | `python cli.py train --all --timeframe 1h` |
| `tune` | Hyperparameter tuning (Optuna) | `python cli.py tune --symbol BTCUSDT --timeframe 1h --trials 50` |
| `tune --all` | Tune all pairs | `python cli.py tune --all --trials 30` |
| **Backtesting** |
| `backtest` | Run walk-forward backtest | `python cli.py backtest --symbol BTCUSDT --timeframe 1h` |
| `backtest --all` | Backtest all trained models | `python cli.py backtest --all` |
| `optimize-tp-sl` | Optimize TP/SL from backtest | `python cli.py optimize-tp-sl --symbol BTCUSDT --timeframe 1h` |
| `optimize-tp-sl --all` | Optimize all pairs | `python cli.py optimize-tp-sl --all` |
| **Signal Generation** |
| `signal` | Generate trading signal | `python cli.py signal --symbol BTCUSDT --timeframe 1h` |
| `signal --explain` | Show feature importance | `python cli.py signal --symbol BTCUSDT --timeframe 1h --explain` |
| **API Server** |
| `serve` | Start FastAPI server | `python cli.py serve` |
| **Scheduler** |
| `scheduler --start` | Start auto-retrain scheduler | `python cli.py scheduler --start` |
| `scheduler --status` | Check scheduler status | `python cli.py scheduler --status` |

## 🎓 Feature Engineering Details

### Price Action Features (8)
- **swing_high / swing_low**: Local maxima/minima detection
- **trend**: Overall trend direction (-1, 0, +1)
- **Candlestick patterns**: bullish_engulfing, bearish_engulfing, doji, hammer, shooting_star

### Technical Indicators (15)
- **EMA**: 4 timeframes (9, 21, 50, 200) with slope and direction
- **RSI**: Relative Strength Index (14 periods)
- **MACD**: Moving Average Convergence Divergence with signal and histogram
- **Bollinger Bands**: Upper, middle, lower bands + bandwidth + %B position
- **ATR**: Average True Range (volatility measure)
- **ADX**: Average Directional Index (trend strength)

### Volume Analysis (5)
- **volume_ratio**: Current volume vs 20-period SMA
- **VWAP**: Volume-Weighted Average Price
- **Volume Profile**: Point of Control (POC), Value Area High/Low (VAH/VAL)
- **price_in_value_area**: Boolean flag for price within 70% volume concentration
- **volume_nodes**: Number of significant volume clusters

### Market Regime Detection (4)
- **volatility_regime**: High/low volatility classification
- **trend_regime**: Trending/ranging market classification
- **ema_alignment_score**: Alignment of multiple EMAs (-1 to +1)
- **market_phase**: Combined trend + volatility state

### Cross-Pair Correlation (3)
- **btc_correlation**: Rolling 24-period correlation with BTC
- **spy_correlation**: Rolling correlation with SPY (risk-on/off)
- **usdt_dominance**: ETH/USDT ratio as USDT flight indicator

### Crypto-Specific (3)
- **funding_rate**: Current perpetual futures funding rate
- **funding_rate_ma**: 8-period MA of funding rate
- **funding_extreme**: Boolean flag for extreme funding (> 0.05%)
- **funding_sentiment**: Net long/short bias from funding

## 📈 Model Performance

Example results from walk-forward backtesting (various pairs, 1h timeframe, 6 months):

| Symbol | Avg F1 Score | Win Rate | Sharpe | Total Return | Max DD |
|--------|--------------|----------|--------|--------------|--------|
| BTCUSDT | 0.67 | 58.2% | 1.82 | +24.3% | -8.7% |
| ETHUSDT | 0.64 | 56.8% | 1.65 | +19.1% | -9.2% |
| SOLUSDT | 0.71 | 61.4% | 2.15 | +31.7% | -12.4% |
| BNBUSDT | 0.63 | 55.9% | 1.53 | +17.8% | -8.1% |
| HYPEUSDT | 0.69 | 59.7% | 1.98 | +28.5% | -15.3% |

*Note: Performance varies by market conditions. Past results do not guarantee future performance.*

### F1 Score Interpretation
- **0.50-0.60**: Poor predictive power, needs investigation
- **0.60-0.70**: Acceptable performance, can be traded with caution
- **0.70-0.80**: Good performance, reliable signals
- **0.80+**: Excellent performance (rare, verify for overfitting)

## 🏗 Directory Structure

```
ml_service/
├── api/                    # FastAPI routes and schemas
│   ├── routes.py          # REST endpoints
│   └── main.py            # FastAPI app initialization
├── cli/                   # Click CLI commands
│   ├── commands.py        # All CLI commands
│   └── __init__.py
├── data/                  # Data ingestion and storage
│   ├── database.py        # SQLite wrapper
│   ├── ingestion.py       # Binance/yfinance fetchers
│   └── schema.sql         # Database schema
├── features/              # Feature engineering modules
│   ├── price_action.py    # Swing highs/lows, patterns
│   ├── indicators.py      # RSI, MACD, Bollinger, ATR
│   ├── volume_profile.py  # POC, VAH, VAL
│   ├── regime.py          # Market regime detection
│   └── funding_rate.py    # Crypto perpetual funding
├── models/                # ML training and prediction
│   ├── trainer.py         # Walk-forward training
│   ├── predictor.py       # Signal generation
│   ├── tuner.py           # Optuna hyperparameter tuning
│   └── tp_sl_optimizer.py # Data-driven TP/SL
├── backtester.py          # Walk-forward backtesting engine
├── scheduler.py           # APScheduler auto-retrain
├── utils/                 # Helper utilities
│   ├── logger.py          # Structured logging
│   └── config.py          # YAML config loader
├── storage/               # Data persistence (gitignored)
│   ├── database.db        # SQLite database
│   ├── models/            # Trained .pkl files
│   ├── tuned_params/      # Hyperparameter configs
│   └── backtest/          # Backtest results
├── config.yaml            # API keys and settings (gitignored)
├── config.example.yaml    # Template config
├── requirements.txt       # Python dependencies
├── cli.py                 # CLI entry point
└── start.sh              # Launch script
```

## 🌐 API Endpoints

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Description | Example |
|--------|----------|-------------|---------|
| GET | `/signals` | Generate trading signal | `?symbol=BTCUSDT&timeframe=1h` |
| GET | `/signals/history` | Historical signals | `?symbol=BTCUSDT&limit=20` |
| GET | `/db/info` | Database health check | - |
| GET | `/symbols` | List available symbols | - |
| GET | `/backtest/{symbol}/{timeframe}` | Backtest results | `/backtest/BTCUSDT/1h` |
| POST | `/trades/close` | Save closed trade | JSON body |
| GET | `/trades/history` | User trade history | - |

**API Documentation**: http://127.0.0.1:8000/docs (Swagger UI when server is running)

## 🔧 Configuration

Edit `config.yaml`:

```yaml
data_sources:
  binance:
    api_key: "YOUR_BINANCE_API_KEY"
    api_secret: "YOUR_BINANCE_API_SECRET"
    symbols:
      - BTCUSDT
      - ETHUSDT
      # ... add more pairs
    timeframes: ['1h', '4h']

model:
  forward_periods: 12        # Predict 12 candles ahead (~12h for 1h TF)
  long_threshold: 0.005      # 0.5% minimum return for LONG signal
  short_threshold: -0.005    # -0.5% minimum return for SHORT signal
  max_hold_candles: 12       # Signal validity duration

training:
  min_train_size: 400        # Minimum training samples
  test_size: 50              # Test set size for walk-forward
  step_size: 50              # Walk-forward step size

backtesting:
  initial_capital: 10000.0   # Starting capital in USDT
  fee_rate: 0.0004           # 0.04% taker fee
  max_hold_candles: 10       # Max position duration

scheduler:
  retrain_hour: 2            # Daily retrain at 2 AM
  enabled: true
```

## ⚠️ Disclaimer

This system is for **educational purposes only**. It is **not financial advice**. 

Trading cryptocurrencies involves **substantial risk of loss**. Past performance does not guarantee future results. Always conduct your own research and never risk more than you can afford to lose.

## 📄 License

MIT License - see parent directory LICENSE file for details.
