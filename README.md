# MoroQuant Trading
> Self-learning ML trading intelligence system for crypto futures

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-orange?style=flat)](https://xgboost.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Overview

Full-stack trading dashboard with machine learning signal generation. Built with Next.js + Python FastAPI + XGBoost/LightGBM ensemble models. Features real-time signal generation, data-driven TP/SL optimization, and walk-forward backtesting across 11 cryptocurrency pairs.

![Dashboard Preview](docs/dashboard-preview.png)

## ✨ Features

### Machine Learning
- **XGBoost/LightGBM Ensemble** — Dual-model prediction with walk-forward validation
- **30+ Technical Features** — Price action, indicators, volume profile, funding rate, regime classification
- **Data-driven TP/SL** — Take profit/stop loss levels optimized from backtest history using Optuna
- **Multi-timeframe Confirmation** — 1h signals validated against 4h for higher confidence
- **Hyperparameter Tuning** — Bayesian optimization with 50+ trials per model
- **Auto-retrain Scheduler** — Models retrain daily with fresh market data

### Trading Intelligence
- **11 Crypto Pairs** — BTC, ETH, BNB, SOL, HYPE, ADA, XRP, LINK, LTC, ZEC, SUI
- **Live Dashboard** — Real-time prices via Binance WebSocket, signal cards with confidence scores
- **Backtesting Engine** — Walk-forward validation with performance metrics (Sharpe, win rate, drawdown)
- **Trade Tracker** — Track open positions with real-time PnL calculations
- **Signal History** — Historical signal performance and accuracy tracking

### Data Infrastructure
- **2 Years Historical Data** — 536,000+ OHLCV candles across all pairs
- **Multi-source Integration** — Binance Futures API, Yahoo Finance, CoinGecko market data
- **Efficient Storage** — SQLite with indexed queries, model persistence, incremental updates
- **Feature Engineering Pipeline** — 60+ technical indicators including custom volume profile and regime detection

## 🛠 Tech Stack

**Frontend**
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- Recharts (equity curves)
- Zustand (state management)

**Backend**
- Python 3.10+
- FastAPI (REST API)
- XGBoost & LightGBM
- pandas, numpy, scikit-learn
- pandas-ta (technical analysis)
- Optuna (hyperparameter optimization)

**Data Sources**
- Binance Futures API (crypto OHLCV)
- Yahoo Finance (macro context)
- CoinGecko (market dominance)

**Infrastructure**
- SQLite (time-series data)
- Click (CLI framework)
- APScheduler (auto-retrain)
- WebSockets (real-time prices)

## 📁 Project Structure

```
trade-dashboard/
├── app/                    # Next.js pages (App Router)
│   ├── trading/           # ML signals dashboard
│   ├── backtest/          # Backtest results & equity curves
│   └── trades/            # Live trade tracker
├── components/             # React components
│   ├── trading/           # Signal cards, grid, analysis
│   └── layout/            # Sidebar, navigation
├── ml_service/             # Python ML backend
│   ├── data/              # Data ingestion & database
│   ├── features/          # Feature engineering (30+ indicators)
│   ├── models/            # ML training, prediction, tuning
│   │   ├── trainer.py     # Walk-forward validation
│   │   ├── predictor.py   # Signal generation
│   │   ├── tuner.py       # Optuna hyperparameter tuning
│   │   └── tp_sl_optimizer.py  # Data-driven TP/SL
│   ├── api/               # FastAPI routes
│   ├── backtester.py      # Walk-forward backtesting
│   ├── scheduler.py       # Auto-retrain scheduler
│   └── cli.py             # CLI commands
├── lib/                   # TypeScript utilities & API clients
└── storage/               # SQLite DB, trained models (gitignored)
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- VPN (for Binance API access in restricted regions)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/trade-dashboard
cd trade-dashboard

# Install frontend dependencies
npm install

# Setup ML backend
cd ml_service
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure API keys
cp config.example.yaml config.yaml
# Edit config.yaml with your Binance API credentials
```

### Running the Application

**Option 1: Start everything with one command**
```bash
./start-all.sh
```

**Option 2: Start services manually**
```bash
# Terminal 1 - ML Backend
cd ml_service
./start.sh

# Terminal 2 - Frontend
npm run dev
```

Access the dashboard at http://localhost:3000

### Initial Setup: Fetch Data & Train Models

```bash
cd ml_service
source venv/bin/activate

# Fetch 2 years of historical data for all pairs
python cli.py fetch --all --days 730 --full-history

# Train models for 1h timeframe
python cli.py train --symbol BTCUSDT --timeframe 1h

# Or train all pairs at once
for symbol in BTCUSDT ETHUSDT BNBUSDT SOLUSDT HYPEUSDT ADAUSDT XRPUSDT LINKUSDT LTCUSDT ZECUSDT SUIUSDT; do
  python cli.py train --symbol $symbol --timeframe 1h
done

# Run backtests to optimize TP/SL levels
python cli.py backtest --all
python cli.py optimize-tp-sl --all

# Generate signals
python cli.py signal --symbol BTCUSDT --timeframe 1h
```

## 📊 ML Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION                          │
├─────────────────────────────────────────────────────────────────┤
│  Binance API  →  OHLCV (536k+ candles, 2 years history)        │
│  CoinGecko    →  Market dominance, USDT flow                   │
│  Yahoo Finance→  Macro context (SPY, GLD, VIX proxies)         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FEATURE ENGINEERING                          │
├─────────────────────────────────────────────────────────────────┤
│  • Price Action:  Swing highs/lows, S/R levels                 │
│  • Indicators:    EMA(9,21,50,200), RSI, MACD, Bollinger       │
│  • Volume:        Volume ratio, profile, VWAP, POC             │
│  • Regime:        ADX, volatility state, trend strength        │
│  • Cross-pair:    BTC correlation, funding rate sentiment      │
│  • Dominance:     USDT flow, risk-off signals                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL TRAINING                               │
├─────────────────────────────────────────────────────────────────┤
│  Walk-forward Validation:                                       │
│    ├─ Min train: 400 candles, test: 50 candles                │
│    ├─ Step size: 50 candles (no lookahead bias)               │
│    └─ Target: 12-candle forward return (±0.5% threshold)      │
│                                                                 │
│  Models: XGBoost vs LightGBM (best F1 selected)               │
│  Hyperparameters: Optuna Bayesian optimization (50 trials)     │
│  TP/SL Optimization: Max favorable/adverse from backtest       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL GENERATION                            │
├─────────────────────────────────────────────────────────────────┤
│  Prediction → Direction (LONG/SHORT/NEUTRAL)                    │
│  Confidence: Model probability (0-100%)                         │
│  TP/SL: ATR-based, optimized from backtest (1:2 R/R)          │
│  MTF Check: 1h signal vs 4h confirmation (±15% confidence)     │
│  Valid: Next 12 candles (~12h for 1h timeframe)               │
└─────────────────────────────────────────────────────────────────┘
```

## 📈 Performance

Example metrics from walk-forward backtesting (BTCUSDT 1h, 6 months):

| Metric | Value |
|--------|-------|
| Total Return | +24.3% |
| Win Rate | 58.2% |
| Sharpe Ratio | 1.82 |
| Max Drawdown | -8.7% |
| Total Trades | 245 |
| Avg F1 Score | 0.67 |

*Performance varies by pair and market conditions. Past performance does not guarantee future results.*

## 🔧 CLI Commands Reference

```bash
# Data Management
python cli.py fetch --symbol BTCUSDT --timeframe 1h --days 730
python cli.py fetch --all  # Fetch all configured pairs
python cli.py db-info      # Show database statistics

# Model Training
python cli.py train --symbol BTCUSDT --timeframe 1h
python cli.py tune --symbol BTCUSDT --timeframe 1h --trials 50
python cli.py tune --all --trials 30  # Faster tuning for all pairs

# Backtesting & Optimization
python cli.py backtest --symbol BTCUSDT --timeframe 1h
python cli.py backtest --all
python cli.py optimize-tp-sl --symbol BTCUSDT --timeframe 1h
python cli.py optimize-tp-sl --all

# Signal Generation
python cli.py signal --symbol BTCUSDT --timeframe 1h --explain

# API Server
python cli.py serve  # Start FastAPI server on http://127.0.0.1:8000

# Scheduler
python cli.py scheduler --start   # Start auto-retrain (runs daily)
python cli.py scheduler --status  # Check scheduler status
```

## 🌐 API Endpoints

- `GET /signals?symbol=BTCUSDT&timeframe=1h` — Generate trading signal
- `GET /signals/history?symbol=BTCUSDT&limit=20` — Historical signals
- `GET /db/info` — Database health check
- `GET /symbols` — List available symbols with data counts
- `GET /backtest/{symbol}/{timeframe}` — Backtest results & equity curve
- `POST /trades/close` — Save closed trade
- `GET /trades/history` — User trade history with PnL summary

Full API documentation: http://127.0.0.1:8000/docs (when server is running)

## 🎓 Key Concepts

### Walk-Forward Validation
Prevents lookahead bias by training on historical data and testing on unseen future data. The model "walks forward" through time, retraining periodically.

### Multi-Timeframe Analysis
1h signals are cross-referenced with 4h timeframe. Agreement boosts confidence by +15%, conflict reduces by -20%.

### Data-Driven TP/SL
Instead of hardcoded ATR multipliers (e.g., 3×ATR for TP), the system analyzes actual backtest trade history to calculate:
- **TP multiplier**: median(max_favorable_excursion / ATR)
- **SL multiplier**: median(max_adverse_excursion / ATR) × 1.2 (safety buffer)

### Feature Importance
Each signal includes the top 5 features that contributed to the prediction, providing transparency into model decisions.

## 📝 Configuration

Edit `ml_service/config.yaml`:

```yaml
data_sources:
  binance:
    api_key: "YOUR_BINANCE_API_KEY"
    api_secret: "YOUR_BINANCE_API_SECRET"
    symbols: [BTCUSDT, ETHUSDT, ...]
    timeframes: ['1h', '4h']

model:
  forward_periods: 12        # Predict 12 candles ahead
  long_threshold: 0.005      # 0.5% minimum return for LONG
  short_threshold: -0.005    # -0.5% minimum return for SHORT
  max_hold_candles: 12       # Signal validity period

training:
  min_train_size: 400        # Minimum training samples
  test_size: 50              # Test set size
  step_size: 50              # Walk-forward step size
```

## 🐛 Troubleshooting

**Issue: "No data found for symbol"**
```bash
# Fetch data first
python cli.py fetch --symbol BTCUSDT --timeframe 1h --days 730
```

**Issue: "No trained model found"**
```bash
# Train the model
python cli.py train --symbol BTCUSDT --timeframe 1h
```

**Issue: Binance API errors**
- Ensure VPN is active if in a restricted region
- Verify API keys in config.yaml
- Check API key permissions (needs "Enable Reading" for public data)

**Issue: Frontend can't connect to backend**
```bash
# Check if ML service is running
curl http://127.0.0.1:8000/db/info

# If not, start it
cd ml_service && ./start.sh
```

## 🚧 Roadmap

- [ ] Real-time alerting (Telegram, Discord)
- [ ] Portfolio optimization (Kelly Criterion position sizing)
- [ ] Sentiment analysis from news/social media
- [ ] Options flow integration
- [ ] Multi-exchange support (Bybit, OKX)
- [ ] Reinforcement learning (DQN, PPO)

## 🤝 Contributing

Contributions are welcome! Please open an issue or PR for:
- Bug fixes
- New features
- Performance improvements
- Documentation enhancements

## ⚠️ Disclaimer

This system is for **educational purposes only**. It is **not financial advice**. 

Trading cryptocurrencies and derivatives involves **substantial risk of loss**. You may lose some or all of your investment. Past performance does not guarantee future results. Always do your own research and never risk more than you can afford to lose.

The developers are not responsible for any financial losses incurred from using this software.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- XGBoost & LightGBM teams for powerful gradient boosting frameworks
- Binance for comprehensive futures API
- pandas-ta for technical analysis indicators
- Optuna for hyperparameter optimization
- Next.js & FastAPI communities

---

**Built with ❤️ by MoroQuant Team**

⭐ Star this repo if you find it useful!
