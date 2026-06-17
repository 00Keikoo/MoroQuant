# Database Schema Audit Report
**MoroQuant Production Trading System**  
**Date:** 2026-06-17  
**Purpose:** Trade Intelligence Dashboard Implementation

---

## Executive Summary

The database schema contains the core infrastructure needed for live trading analytics. Signal attribution fields exist in `user_trade_history`, but some metadata fields need to be added to the `signals` table to enable complete trade-to-signal attribution.

**Status:**
- ✅ Signals table exists (22,706 signals stored)
- ✅ Trade history table exists with signal attribution fields
- ✅ Exchange sync infrastructure implemented
- ⚠️ Missing: TP/SL multipliers and labeling_method in signals table
- ⚠️ No synced Binance trades yet (0 records in user_trade_history)

---

## Current Schema

### 1. `signals` Table
**Purpose:** Store ML-generated trading signals

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('long', 'short', 'neutral')),
    confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_signals_symbol_timeframe ON signals(symbol, timeframe, timestamp DESC);
```

**Records:** 22,706 signals  
**Sample Data:**
- BTCUSDT signals with confidence scores ~79%
- Features stored as JSON (ema_50, ema_200, macd, etc.)

### 2. `user_trade_history` Table
**Purpose:** Synced Binance Futures trades with signal attribution

```sql
CREATE TABLE user_trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    qty REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    commission REAL NOT NULL,
    trade_time INTEGER NOT NULL,
    order_id TEXT UNIQUE NOT NULL,
    matched_signal_id INTEGER,
    market_regime TEXT,
    confidence_at_entry INTEGER,
    synced_at TEXT NOT NULL,
    FOREIGN KEY (matched_signal_id) REFERENCES signals(id)
);
CREATE INDEX idx_user_trade_history_symbol_time ON user_trade_history(symbol, trade_time DESC);
```

**Records:** 0 (no synced trades yet)  
**Attribution Fields Present:**
- ✅ `matched_signal_id` - Links to signals table
- ✅ `market_regime` - Trending/ranging/choppy/high_vol
- ✅ `confidence_at_entry` - Signal confidence when trade opened

### 3. `user_trades` Table (Legacy)
**Purpose:** Manual trade tracking

```sql
CREATE TABLE user_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('long', 'short')),
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    leverage REAL NOT NULL,
    size_usdt REAL NOT NULL,
    pnl REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_trades_closed_at ON user_trades(closed_at DESC);
```

**Note:** This table is for manual trade entry, not Binance sync. Use `user_trade_history` for live analytics.

### 4. Supporting Tables

**`ohlcv`** - OHLCV candlestick data  
**`macro_events`** - Economic calendar events  
**`market_dominance`** - BTC/USDT dominance metrics

---

## Required Schema Changes

### Migration: Add TP/SL Metadata to Signals

The `signals` table needs to store TP/SL multipliers and labeling method for complete attribution:

```sql
ALTER TABLE signals ADD COLUMN tp_multiplier REAL;
ALTER TABLE signals ADD COLUMN sl_multiplier REAL;
ALTER TABLE signals ADD COLUMN labeling_method TEXT;
ALTER TABLE signals ADD COLUMN atr REAL;
```

**Rationale:**
- TP/SL multipliers vary per signal (optimized per symbol/timeframe)
- Labeling method identifies training approach (triple_barrier, fixed_horizon, etc.)
- ATR is needed to reconstruct exact TP/SL prices from entry
- These fields enable analysis: "Do higher TP ratios perform better?"

**Implementation Location:** `ml_service/models/predictor.py:generate_signal()`  
When signals are saved to DB, include these metadata fields.

---

## Exchange Sync Infrastructure

### Implementation Status: ✅ Complete

**File:** `ml_service/data/exchange_sync.py`

**Functions:**
1. `fetch_user_trades(api_key, api_secret)` - Fetch Binance Futures trade history
2. `fetch_open_positions(api_key, api_secret)` - Fetch open positions
3. `save_trades_to_db(trades)` - Insert trades into user_trade_history
4. `enrich_trades_with_signals()` - Match trades to signals within 1-hour window
5. `get_position_signal_comparison(positions)` - Compare positions with current signals

**Trade-to-Signal Linking Logic:**
- Searches for signal within ±1 hour of trade_time
- Matches by symbol
- Orders by timestamp proximity (closest match wins)
- Extracts market_regime from signal's features_json
- Stores matched_signal_id, market_regime, confidence_at_entry

---

## API Endpoints

### Existing Endpoints (ml_service/api/routes.py)

✅ `GET /signals` - Generate fresh signal for symbol/timeframe  
✅ `GET /signals/history` - Historical signals from DB  
✅ `GET /backtest/{symbol}/{timeframe}` - Backtest results  
✅ `POST /trades/close` - Save manual trade  
✅ `GET /trades/history` - Manual trades with basic metrics  
✅ `GET /positions/open` - Open Binance positions with signal comparison  
✅ `GET /db/info` - Database health check  
✅ `GET /symbols` - Available symbols

### Missing Endpoints (Need Implementation)

❌ `GET /api/analytics/live-performance` - Overall live trading metrics  
❌ `GET /api/analytics/regimes` - Performance grouped by regime  
❌ `GET /api/analytics/confidence` - Performance grouped by confidence buckets  
❌ `GET /api/analytics/trade-history` - Enhanced trade history with enrichment

---

## Analytics Services (Not Yet Implemented)

### Required Services

1. **analytics/live_metrics.py**
   - Compute: win rate, profit factor, expectancy, avg PnL, avg hold time, Sharpe ratio, max drawdown
   - Source: user_trade_history table (real Binance trades)

2. **analytics/regime_performance.py**
   - Group by: market_regime (trending, ranging, choppy_low_vol, high_volatility)
   - Metrics per regime: trades, win rate, profit factor, expectancy

3. **analytics/confidence_report.py**
   - Bucket by: confidence_at_entry (50-60%, 60-70%, 70-80%, 80-90%, 90%+)
   - Metrics per bucket: trades, win rate, expectancy, total PnL
   - Goal: Validate if higher confidence = better outcomes

---

## Frontend Structure

**Current Pages:**
- `/` - Home
- `/trading` - Live trading interface
- `/trades` - Trade management
- `/backtest` - Backtest results

**Required Page:**
- `/dashboard/performance` - Live analytics dashboard

**UI Framework:** Next.js with TypeScript  
**Styling:** TailwindCSS (globals.css)  
**API Integration:** app/api/* routes

---

## Trained Models Status

**Storage:** `ml_service/storage/models/`  
**Count:** 50+ models across symbols and timeframes  
**Format:** Pickle files with metadata

**Recent Models:**
- BTCUSDT_1h (ensemble xgb+lgb)
- BNBUSDT_1h (lightgbm, xgboost)
- Multiple altcoins (ADA, ATOM, AVAX)
- Timeframes: 1h, 4h

**Metadata Included:**
- labeling_method: 'triple_barrier'
- tp_mult, sl_mult: Optimized multipliers
- trained_at: Timestamp
- feature_cols: Feature list

---

## Signal Generation Pipeline

**File:** `ml_service/models/predictor.py`

**Process:**
1. Load latest trained model for symbol/timeframe
2. Fetch recent OHLCV from database
3. Compute features (indicators, regime, price action)
4. Generate prediction with confidence
5. Load optimized TP/SL parameters
6. Calculate TP/SL prices using ATR
7. Return signal with metadata

**Current Behavior:**
- Signals stored in `signals` table when generated
- TP/SL multipliers NOT currently stored (needs fix)
- Labeling method NOT currently stored (needs fix)

---

## Open Positions Tracking

**Status:** ✅ Implemented

**Endpoint:** `GET /api/positions/open`  
**Source:** Binance Futures API (`/fapi/v2/positionRisk`)  
**Features:**
- Fetches real-time open positions
- Compares with current ML signal
- Shows agreement (match/conflict/neutral)
- Calculates unrealized PnL

**Response Format:**
```json
{
  "positions": [
    {
      "symbol": "BTCUSDT",
      "side": "long",
      "entry_price": 95000.0,
      "mark_price": 96000.0,
      "unrealized_pnl": 100.0,
      "leverage": 3,
      "position_amt": 0.1,
      "signal": { ... },
      "agreement": "match"
    }
  ],
  "total_unrealized_pnl": 100.0,
  "count": 1
}
```

---

## Recommendations

### Immediate Actions

1. **Create migration script** to add TP/SL columns to signals table
2. **Update signal generation** to store tp_multiplier, sl_multiplier, labeling_method, atr
3. **Sync Binance trades** - Run initial sync to populate user_trade_history
4. **Build analytics services** - Implement live_metrics, regime_performance, confidence_report
5. **Create API routes** - Add /api/analytics/* endpoints
6. **Build frontend dashboard** - Create /dashboard/performance page

### Data Integrity

- ✅ Foreign key constraint on matched_signal_id
- ✅ Check constraints on direction, confidence ranges
- ✅ Unique constraint on order_id (prevents duplicate syncs)
- ✅ Indexes on common query patterns (symbol, timestamp)

### Performance Considerations

- Current signals count (22K) is manageable
- Index on (symbol, timeframe, timestamp) supports fast signal lookups
- Trade history will grow over time - current indexes are appropriate
- Consider partitioning if trade_history exceeds 1M rows

---

## Next Steps

1. ✅ Schema audit complete
2. ⏭️ Implement schema migration (add TP/SL columns)
3. ⏭️ Update signal generation to store metadata
4. ⏭️ Build analytics services
5. ⏭️ Create API endpoints
6. ⏭️ Build frontend dashboard
7. ⏭️ Write comprehensive documentation

---

**End of Audit Report**
