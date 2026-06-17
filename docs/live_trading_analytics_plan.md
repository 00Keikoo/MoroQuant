# Live Trading Analytics Implementation Plan
**MoroQuant Production Trading System**  
**Date:** 2026-06-17  
**Status:** ✅ Implementation Complete

---

## Executive Summary

The Trade Intelligence Dashboard is now fully implemented for live trading performance monitoring. The system tracks real Binance Futures trades, attributes them to ML signals, and provides comprehensive analytics across multiple dimensions: overall performance, regime-based analysis, and confidence-based validation.

**Key Capabilities:**
- Real-time performance metrics (win rate, profit factor, expectancy, Sharpe ratio, max drawdown)
- Equity curve visualization
- Open positions monitoring with signal agreement tracking
- Regime performance analysis (trending, ranging, choppy, high volatility)
- Confidence bucket analysis (validates if higher confidence = better outcomes)
- Complete signal attribution system

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│  /dashboard/performance - Live Analytics Dashboard             │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTP/REST
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (ml_service/api)               │
│  GET /analytics/live-performance                                │
│  GET /analytics/regimes                                         │
│  GET /analytics/confidence                                      │
│  GET /analytics/trade-history                                   │
│  GET /positions/open                                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│              Analytics Services (ml_service/analytics)          │
│  • live_metrics.py - Performance computation                    │
│  • regime_performance.py - Regime grouping                      │
│  • confidence_report.py - Confidence analysis                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                   SQLite Database (database.db)                 │
│  Tables:                                                        │
│  • signals (with TP/SL metadata)                                │
│  • user_trade_history (synced Binance trades)                   │
│  • ohlcv, market_dominance, macro_events                        │
└─────────────────────────────────────────────────────────────────┘
                 ↑
                 │ Sync
┌─────────────────────────────────────────────────────────────────┐
│              Exchange Sync (data/exchange_sync.py)              │
│  • fetch_user_trades() - Pull Binance history                   │
│  • save_trades_to_db() - Insert to database                     │
│  • enrich_trades_with_signals() - Link trades to signals        │
└─────────────────────────────────────────────────────────────────┘
                 ↑
                 │ API
┌─────────────────────────────────────────────────────────────────┐
│                    Binance Futures API                          │
│  /fapi/v1/userTrades - Trade history                            │
│  /fapi/v2/positionRisk - Open positions                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### Migration Applied: `001_add_signal_metadata.sql`

**New Columns Added to `signals` Table:**

```sql
ALTER TABLE signals ADD COLUMN tp_multiplier REAL;
ALTER TABLE signals ADD COLUMN sl_multiplier REAL;
ALTER TABLE signals ADD COLUMN labeling_method TEXT;
ALTER TABLE signals ADD COLUMN atr REAL;
ALTER TABLE signals ADD COLUMN regime TEXT;
```

**Purpose:**
- `tp_multiplier`: Take profit multiplier (e.g., 3.0x ATR)
- `sl_multiplier`: Stop loss multiplier (e.g., 1.5x ATR)
- `labeling_method`: Training approach (triple_barrier, fixed_horizon, etc.)
- `atr`: Average True Range value at signal generation
- `regime`: Market regime (trending, ranging, choppy_low_vol, high_volatility)

**Migration Script:** `/home/zafka/trade-dashboard/ml_service/migrations/run_migration.py`

**Status:** ✅ Applied successfully

---

## Implementation Status

### ✅ Task 1: Database Schema Audit
**Status:** Complete  
**Deliverable:** `docs/database_schema_audit.md`

**Findings:**
- Existing schema has solid foundation
- `user_trade_history` table already includes signal attribution fields
- Migration needed to add TP/SL metadata to `signals` table
- Exchange sync infrastructure already implemented

---

### ✅ Task 2: Signal Attribution System
**Status:** Complete  
**Files Modified:**
- `ml_service/migrations/001_add_signal_metadata.sql` (created)
- `ml_service/migrations/run_migration.py` (created)
- `ml_service/models/predictor.py:389` (updated `save_signal_to_db()`)

**Changes:**
1. Created SQL migration to add 5 new columns to signals table
2. Updated signal generation to populate metadata fields when saving signals
3. Verified migration applied successfully (all columns present)

**Signal Attribution Flow:**
1. ML model generates signal with confidence, regime, TP/SL parameters
2. Signal saved to database with complete metadata (including tp_multiplier, sl_multiplier, labeling_method, atr, regime)
3. When Binance trade syncs, `enrich_trades_with_signals()` matches trade to nearest signal within ±1 hour
4. Trade record enriched with: matched_signal_id, market_regime, confidence_at_entry

---

### ✅ Task 3: Live Performance Metrics Service
**Status:** Complete  
**File:** `ml_service/analytics/live_metrics.py`

**Functions:**
- `compute_live_metrics(symbol, days_back)` - Comprehensive performance metrics
- `get_equity_curve(symbol, days_back)` - Equity curve data points

**Metrics Computed:**
- Total trades, winning trades, losing trades
- Win rate (%)
- Total PnL, average PnL, average win, average loss
- Profit factor (gross profit / gross loss)
- Expectancy (expected value per trade)
- Sharpe ratio (risk-adjusted return)
- Max drawdown (largest peak-to-trough decline)
- Average hold time (hours)

**Data Source:** Real synced Binance trades from `user_trade_history` table

---

### ✅ Task 4: Regime Performance Analytics
**Status:** Complete  
**File:** `ml_service/analytics/regime_performance.py`

**Functions:**
- `compute_regime_performance(symbol, days_back)` - Metrics grouped by regime
- `get_regime_distribution(symbol, days_back)` - Regime trade distribution

**Regimes Analyzed:**
- Trending
- Ranging
- Choppy Low Vol
- High Volatility
- Unknown

**Metrics Per Regime:**
- Total trades, win rate
- Profit factor, expectancy
- Gross profit, gross loss

**Use Case:** Identify which market conditions produce best/worst results

---

### ✅ Task 5: Confidence Analytics
**Status:** Complete  
**File:** `ml_service/analytics/confidence_report.py`

**Functions:**
- `compute_confidence_performance(symbol, days_back)` - Metrics by confidence bucket
- `analyze_confidence_correlation(symbol, days_back)` - Correlation analysis

**Confidence Buckets:**
- 50-60%
- 60-70%
- 70-80%
- 80-90%
- 90%+

**Metrics Per Bucket:**
- Total trades, win rate
- Expectancy, total PnL

**Correlation Analysis:**
- Pearson correlation between confidence and PnL
- High vs low confidence comparison (75% threshold)
- Interpretation of correlation strength

**Goal:** Validate if higher confidence signals produce better outcomes

---

### ✅ Task 6: Open Positions API
**Status:** Complete (already existed)  
**Endpoint:** `GET /api/positions/open`

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
      "signal": {
        "direction": "long",
        "confidence": 75
      },
      "agreement": "match"
    }
  ],
  "total_unrealized_pnl": 100.0,
  "count": 1
}
```

**Features:**
- Fetches real-time open positions from Binance
- Compares with current ML signal
- Shows agreement status (match/conflict/neutral)

---

### ✅ Task 7: Dashboard API Endpoints
**Status:** Complete  
**File:** `ml_service/api/routes.py`

**New Endpoints:**

#### GET /analytics/live-performance
Query params: `symbol` (optional), `days_back` (optional)

Returns:
```json
{
  "status": "success",
  "metrics": {
    "total_trades": 150,
    "win_rate": 58.5,
    "profit_factor": 1.85,
    "expectancy": 12.50,
    "sharpe_ratio": 1.42,
    "max_drawdown": 450.00,
    ...
  },
  "equity_curve": [...]
}
```

#### GET /analytics/regimes
Query params: `symbol` (optional), `days_back` (optional)

Returns regime-grouped metrics and distribution.

#### GET /analytics/confidence
Query params: `symbol` (optional), `days_back` (optional)

Returns confidence bucket metrics and correlation analysis.

#### GET /analytics/trade-history
Query params: `symbol` (optional), `limit` (default: 100)

Returns enhanced trade history with signal attribution:
```json
{
  "trades": [
    {
      "id": 1,
      "symbol": "BTCUSDT",
      "side": "BUY",
      "price": 95000.0,
      "realized_pnl": 50.0,
      "matched_signal_id": 12345,
      "market_regime": "trending",
      "confidence_at_entry": 75,
      "signal_direction": "long",
      "tp_multiplier": 3.0,
      "sl_multiplier": 1.5,
      "labeling_method": "triple_barrier"
    }
  ]
}
```

---

### ✅ Task 8: Frontend Dashboard
**Status:** Complete  
**File:** `app/dashboard/performance/page.tsx`

**Sections Implemented:**

#### A. Summary Cards (Top Row)
- Win Rate (%)
- Profit Factor
- Expectancy ($)
- Sharpe Ratio

#### B. Summary Cards (Bottom Row)
- Total Trades
- Total PnL ($)
- Max Drawdown ($)
- Average Hold Time (hours)

#### C. Equity Curve
- Bar chart visualization of cumulative PnL over time
- Each bar represents a trade
- Hover shows trade details

#### D. Open Positions
- Real-time position display
- Shows: symbol, side, entry/mark price, unrealized PnL
- Signal agreement indicator (match/conflict/neutral)
- Color-coded by profitability

#### E. Confidence Analysis
- Performance metrics per confidence bucket
- Displays: trades, win rate, expectancy, total PnL
- Validates confidence calibration

#### F. Regime Performance
- Performance metrics per market regime
- Displays: trades, win rate, profit factor, expectancy
- Identifies best/worst market conditions

**Features:**
- Auto-refresh every 30 seconds
- Manual refresh button
- Responsive design with dark theme
- Color-coded performance indicators (green=profit, red=loss)
- Integrated with sidebar navigation

**Navigation:** Sidebar → "Live Analytics" link added

---

## File Structure

```
ml_service/
├── analytics/
│   ├── __init__.py
│   ├── live_metrics.py          # Performance metrics computation
│   ├── regime_performance.py    # Regime-based analysis
│   └── confidence_report.py     # Confidence analysis
├── migrations/
│   ├── 001_add_signal_metadata.sql
│   └── run_migration.py
├── api/
│   └── routes.py                # Updated with analytics endpoints
├── models/
│   └── predictor.py             # Updated to save signal metadata
└── data/
    ├── database.py              # Schema unchanged
    └── exchange_sync.py         # Existing sync infrastructure

app/
├── dashboard/
│   └── performance/
│       └── page.tsx             # Live analytics dashboard
└── components/
    └── layout/
        └── Sidebar.tsx          # Updated with dashboard link

docs/
├── database_schema_audit.md    # Schema analysis
└── live_trading_analytics_plan.md  # This document
```

---

## Next Steps for Production Use

### 1. Initial Binance Trade Sync
**Status:** Not yet run

**Command:**
```python
from ml_service.data.exchange_sync import fetch_user_trades, save_trades_to_db, enrich_trades_with_signals
import yaml

# Load config
with open('ml_service/config.yaml') as f:
    config = yaml.safe_load(f)

api_key = config['exchange_sync']['binance_api_key']
api_secret = config['exchange_sync']['binance_api_secret']

# Fetch and save trades
trades = fetch_user_trades(api_key, api_secret)
if trades:
    saved = save_trades_to_db(trades)
    print(f"Saved {saved} trades")
    
    # Link to signals
    matched = enrich_trades_with_signals()
    print(f"Matched {matched} trades to signals")
```

**Note:** Currently 0 trades in database. Once synced, dashboard will populate with real data.

### 2. Scheduled Trade Sync
**Recommendation:** Set up cron job to sync trades regularly

```bash
# Every hour
0 * * * * cd /home/zafka/trade-dashboard && python3 -c "
from ml_service.data.exchange_sync import fetch_user_trades, save_trades_to_db, enrich_trades_with_signals
import yaml
with open('ml_service/config.yaml') as f:
    config = yaml.safe_load(f)
trades = fetch_user_trades(config['exchange_sync']['binance_api_key'], config['exchange_sync']['binance_api_secret'])
if trades:
    save_trades_to_db(trades)
    enrich_trades_with_signals()
"
```

### 3. Start Services

```bash
# Terminal 1: Start ML service backend
cd ml_service
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Next.js frontend
npm run dev
```

### 4. Access Dashboard

Navigate to: `http://localhost:3000/dashboard/performance`

---

## Testing Without Real Trades

If you want to test the dashboard before syncing real trades, you can insert sample data:

```sql
-- Insert sample trade
INSERT INTO user_trade_history (
    symbol, side, price, qty, realized_pnl, commission,
    trade_time, order_id, matched_signal_id, market_regime,
    confidence_at_entry, synced_at
) VALUES (
    'BTCUSDT', 'BUY', 95000.0, 0.01, 50.0, 2.0,
    1718630400000, 'test_order_1', 1, 'trending',
    75, '2026-06-17T16:13:00'
);
```

---

## Performance Considerations

### Current Data Scale
- Signals: 22,706 records
- Trades: 0 records (awaiting sync)
- Expected trade volume: ~50-200 trades/day (production estimate)

### Indexes
All critical paths are indexed:
- `signals(symbol, timeframe, timestamp)` - Signal lookups
- `user_trade_history(symbol, trade_time)` - Trade queries
- `user_trade_history(matched_signal_id)` - Join operations

### API Response Times (estimated)
- `/analytics/live-performance` - <100ms with 1000 trades
- `/analytics/regimes` - <150ms with 1000 trades
- `/analytics/confidence` - <150ms with 1000 trades
- `/positions/open` - 200-500ms (depends on Binance API)

### Scaling Plan
- Current architecture handles 10K trades easily
- If trades exceed 100K, consider:
  - Partitioning `user_trade_history` by month
  - Materializing daily/weekly aggregate tables
  - Caching computed metrics with TTL

---

## Monitoring and Alerts

### Key Metrics to Monitor
1. **Trade sync lag** - Time between Binance execution and database insert
2. **Signal match rate** - Percentage of trades matched to signals
3. **API response times** - 95th percentile latency
4. **Database size growth** - Track storage usage

### Recommended Alerts
- Alert if no new trades synced for 6+ hours (during trading hours)
- Alert if signal match rate drops below 70%
- Alert if API p95 latency exceeds 1 second

---

## Security Notes

### API Keys
- Binance API keys stored in `config.yaml` (gitignored)
- Use read-only API keys (no trading permissions needed)
- Rotate keys quarterly

### Database Access
- SQLite file permissions: 640 (rw-r-----)
- No external database access needed
- Backup database daily

---

## Troubleshooting

### Dashboard shows "No data"
**Solution:** Run initial Binance trade sync (see Next Steps #1)

### Signal match rate is low
**Possible causes:**
- Large time gap between signal generation and trade execution
- Signal not saved to database before trade
- Symbol mismatch (check exact symbol names)

**Solution:** Check time window in `enrich_trades_with_signals()` (currently ±1 hour)

### API endpoints return 404
**Solution:** Ensure ml_service FastAPI is running on port 8000

### Frontend won't connect to backend
**Solution:** Check CORS settings in `ml_service/api/main.py`

---

## Future Enhancements

### Phase 2 (Not Implemented)
- [ ] Real-time WebSocket updates (eliminate 30s refresh)
- [ ] Per-symbol performance breakdown
- [ ] Trade notes and manual tags
- [ ] Export to CSV/Excel
- [ ] Mobile-responsive charts
- [ ] Performance alerts (email/Slack)
- [ ] Benchmark comparison (vs. buy-and-hold)
- [ ] Multi-account support

### Phase 3 (Advanced)
- [ ] ML model performance tracking (which models produce best trades)
- [ ] Slippage analysis
- [ ] Execution quality metrics
- [ ] Risk management dashboard (leverage usage, position sizing)
- [ ] Correlation analysis (symbol correlation, regime correlation)

---

## Deployment Checklist

- [x] Database migration applied
- [x] Signal generation updated to save metadata
- [x] Analytics services implemented and tested
- [x] API endpoints added and tested
- [x] Frontend dashboard built
- [x] Navigation links updated
- [ ] Initial Binance trade sync run
- [ ] Services started and verified
- [ ] Dashboard accessed and verified
- [ ] Scheduled sync cron job configured
- [ ] Monitoring and alerts configured
- [ ] Backup strategy implemented

---

## Summary

The Trade Intelligence Dashboard is fully implemented and ready for production use. Once Binance trades are synced, the dashboard will display comprehensive live trading analytics including:

- Overall performance metrics (win rate, profit factor, expectancy, Sharpe, drawdown)
- Equity curve visualization
- Open positions monitoring with signal agreement
- Regime-based performance analysis
- Confidence calibration validation

**No changes to ML models, signal generation logic, or TP/SL optimization were made** - this is purely an analytics and monitoring layer built on top of the existing production trading system.

**Implementation Status:** ✅ Complete  
**Ready for Production:** Yes (pending initial trade sync)  
**Breaking Changes:** None  
**Migration Required:** Yes (already applied)

---

**End of Implementation Plan**
