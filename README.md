# ML Trading Dashboard

A full-stack trading intelligence platform combining a Next.js dashboard with a self-learning machine learning service for generating real-time trading signals.

## Architecture

This project consists of two main components:

### 1. Next.js Dashboard (Frontend)
- Real-time trading signal display
- Multi-timeframe analysis (1h, 4h)
- Interactive signal cards with confidence scores
- Dark mode UI with Tailwind CSS

### 2. ML Service (Backend)
- FastAPI-based ML inference server
- XGBoost/LightGBM models for signal generation
- Multi-asset support (crypto + traditional markets)
- Automatic model training and retraining

## Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn/pnpm
- Python 3.9+
- Binance API keys (optional, for live crypto data)

### 1. Start the ML Service

```bash
cd ml_service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys

# Start the API server
python cli.py serve
```

The ML service will run on `http://127.0.0.1:8000`

### 2. Start the Next.js Dashboard

```bash
# In the project root directory
npm install

# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## Running Both Services Together

For full functionality, both services must be running:

**Terminal 1 - ML Service:**
```bash
cd ml_service
source venv/bin/activate
python cli.py serve
```

**Terminal 2 - Next.js:**
```bash
npm run dev
```

## Features

- **Real-time Signals**: Live trading signals for 9+ instruments
- **Multi-Timeframe**: Switch between 1h and 4h timeframes
- **ML Powered**: XGBoost/LightGBM models with 60+ technical features
- **Feature Importance**: See which indicators drove each signal
- **Market Regime Detection**: Volatility and trend classification
- **RESTful API**: Easy integration with external tools

## Supported Instruments

**Cryptocurrencies (via Binance):**
- BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT

**Traditional Markets (via yfinance):**
- SPY (S&P 500), QQQ (Nasdaq 100), GLD (Gold), USO (Oil), TLT (Treasury)

## ML Service Documentation

See [ml_service/README.md](ml_service/README.md) for detailed ML service documentation including:
- CLI commands reference
- Feature engineering details
- Model training instructions
- Architecture overview

## Development

### Train Models

```bash
cd ml_service
source venv/bin/activate

# Train a specific model
python cli.py train --symbol BTCUSDT --timeframe 1h

# Train all models
python cli.py train-all --timeframe 1h
```

### Fetch Fresh Data

```bash
python cli.py fetch --symbol BTCUSDT --timeframe 1h --days 90
```

## Tech Stack

**Frontend:**
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- React

**Backend:**
- Python 3.9+
- FastAPI
- XGBoost / LightGBM
- SQLite
- pandas, numpy, scikit-learn

## Disclaimer

This system is for **educational purposes only**. It is not financial advice. Trading involves substantial risk of loss. Always do your own research and never risk more than you can afford to lose.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
