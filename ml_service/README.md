# ML Trading Intelligence System

A self-learning machine learning trading system that generates real-time trading signals for cryptocurrencies and traditional market instruments using XGBoost and LightGBM models.

## Tech Stack

- **Machine Learning**: XGBoost, LightGBM, scikit-learn
- **Data Processing**: pandas, numpy, pandas-ta
- **Data Sources**: Binance API (crypto), yfinance (traditional markets)
- **API Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **CLI**: Click

## Features

- Multi-timeframe analysis (1m, 5m, 15m, 1h, 4h, 1d)
- Advanced feature engineering (60+ technical indicators)
- Market regime detection (trending/ranging, high/low volatility)
- Walk-forward validation for model training
- RESTful API for signal generation
- Automatic model retraining and persistence

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd ml_service
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

Copy the example config and add your API keys:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and replace placeholders:
- `YOUR_BINANCE_API_KEY_HERE` - Get from [Binance API](https://www.binance.com/en/my/settings/api-management)
- `YOUR_BINANCE_API_SECRET_HERE` - Same as above
- `YOUR_FMP_API_KEY` (optional) - For economic calendar from [FMP](https://financialmodelingprep.com/)

**Note**: Binance API keys are optional for public market data access.

### 4. Initialize Database

The database is automatically created on first run.

## CLI Commands Reference

### Data Management

```bash
# Fetch historical data for a symbol
python cli.py fetch --symbol BTCUSDT --timeframe 1h --days 90

# Fetch data for all configured symbols
python cli.py fetch-all --timeframe 1h --days 90
```

### Feature Engineering

```bash
# Generate features for a symbol
python cli.py features --symbol BTCUSDT --timeframe 1h

# Generate features for all symbols
python cli.py features-all --timeframe 1h
```

### Model Training

```bash
# Train model for a specific symbol and timeframe
python cli.py train --symbol BTCUSDT --timeframe 1h

# Train models for all symbols at a timeframe
python cli.py train-all --timeframe 1h

# Train with custom model type
python cli.py train --symbol ETHUSDT --timeframe 4h --model-type lightgbm
```

### Signal Generation

```bash
# Generate signal for a symbol
python cli.py signal --symbol BTCUSDT --timeframe 1h

# Generate signals for all symbols
python cli.py signal-all --timeframe 1h
```

### API Server

```bash
# Start the FastAPI server
python cli.py serve

# Server runs on http://127.0.0.1:8000
# API docs available at http://127.0.0.1:8000/docs
```

## Architecture Overview

### Data Flow

```
1. Data Ingestion
   ├─ Binance API → Crypto OHLCV data
   └─ yfinance → Traditional market data (SPY, QQQ, GLD, etc.)

2. Feature Engineering
   ├─ Price Action: swings, support/resistance
   ├─ Technical Indicators: EMA, RSI, MACD, Bollinger Bands, ATR
   └─ Market Regime: volatility state, trend strength

3. Model Training
   ├─ Target: forward returns (10 candles ahead)
   ├─ Validation: walk-forward cross-validation
   └─ Models: XGBoost/LightGBM with hyperparameter optimization

4. Signal Generation
   ├─ Predicted return → Direction (LONG/SHORT/NEUTRAL)
   ├─ Confidence score (0-1)
   └─ Feature importance for explainability
```

### Directory Structure

```
ml_service/
├── api/              # FastAPI routes and schemas
├── cli/              # CLI commands
├── data/             # Data fetching and storage
├── features/         # Feature engineering modules
├── models/           # Model training and prediction
├── storage/          # SQLite database and trained models (gitignored)
│   ├── database.db
│   ├── models/
│   └── logs/
├── utils/            # Helper utilities
├── config.yaml       # Configuration (gitignored - contains API keys)
├── config.example.yaml
└── requirements.txt
```

### API Endpoints

- `GET /health` - Health check
- `GET /symbols` - List available symbols with model info
- `GET /signal/{symbol}/{timeframe}` - Generate trading signal
- `POST /train/{symbol}/{timeframe}` - Trigger model retraining

## Model Details

### Features (60+ indicators)

- **Price Action**: swing highs/lows, support/resistance levels, price position
- **Momentum**: RSI, ROC, Stochastic
- **Trend**: EMA crossovers, MACD, ADX
- **Volatility**: ATR, Bollinger Bands
- **Volume**: Volume ratio, VWAP
- **Regime**: volatility classification, trend strength

### Target Variable

Forward returns calculated as: `(price[t+10] - price[t]) / price[t]`

Signals are classified as:
- **LONG**: predicted return > 0.5%
- **SHORT**: predicted return < -0.5%
- **NEUTRAL**: predicted return between -0.5% and 0.5%

### Model Validation

Walk-forward validation with 80/20 train/test split ensures models are tested on unseen future data, preventing lookahead bias.

## Performance Notes

- **Data Requirements**: Minimum 500 candles for reliable training
- **1h Timeframe Limitations**: Some traditional market proxies (ES_proxy, NQ_proxy) have limited 1h data availability
- **Retraining**: Models should be retrained periodically (weekly recommended) as market conditions evolve

## Disclaimer

This system is for **educational purposes only**. It is not financial advice. Trading involves substantial risk of loss. Always do your own research and never risk more than you can afford to lose.
