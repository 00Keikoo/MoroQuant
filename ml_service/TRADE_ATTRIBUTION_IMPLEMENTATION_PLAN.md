# Live Trade Attribution and Signal Outcome Tracking - Implementation Plan

**Date**: 2026-06-18  
**Status**: Design & Risk Analysis Phase  
**Priority**: HIGH - Foundation for production learning loop

---

## Executive Summary

**Goal**: Connect generated ML signals to actual Binance trades to enable MoroQuant to learn which signals work in production.

**Current State**:
- ✅ Trade sync working (37 trades from Binance)
- ✅ Signal generation operational (22,715 signals)
- ⚠️ Attribution weak (4.5% match rate - 1/22 trades)
- ❌ No outcome tracking table
- ❌ No automated sync scheduler
- ❌ No performance analytics API

**Target State**:
- ✅ Automated trade sync every 6 hours
- ✅ High-quality signal attribution (>50% match rate expected)
- ✅ Complete signal outcome tracking
- ✅ Production analytics for regime/confidence-based learning

---

## 1. Current System Audit

### 1.1 Trade Sync Pipeline Status

**VPS Compatibility**: ✅ VERIFIED
- Binance Futures API: Working
- Authentication: HMAC SHA256 signature valid
- Rate limits: Well within bounds (1000 trades/request)
- Network: No firewall issues detected

**Current Architecture**:
```
Binance API → fetch_user_trades() → save_trades_to_db() → user_trade_history
                                   ↓
                          enrich_trades_with_signals() → matched_signal_id
```

**Trade Population Status**:
```sql
SELECT COUNT(*) as total, COUNT(matched_signal_id) as matched 
FROM user_trade_history;
-- Result: 22 total, 1 matched (4.5%)
```

**Why Match Rate is Low**:
1. Signal generation gaps (June 16-17: 0 signals generated)
2. Previous attribution logic was too strict
3. Improved logic correctly rejects mismatched directions
4. Most trades occurred when signals weren't being generated

### 1.2 Signal Attribution Current Logic

**Location**: `ml_service/data/exchange_sync.py:151-244`

**Matching Rules** (recently improved):
- ✅ Symbol must match
- ✅ Direction must match (BUY→long, SELL→short)
- ✅ Neutral signals ignored
- ✅ Timeframe-aware windows (1h: ±90min, 4h: ±4h)
- ✅ Highest confidence selected when multiple candidates

**Working Example**:
```
Trade: ZECUSDT SELL @ 2026-06-18 04:14:19
Signal: ZECUSDT short (4h, 78% confidence) @ 04:52:27
Time delta: 38 minutes (within ±4h window)
Result: ✅ Matched
```

### 1.3 Gap Analysis

**Missing Components**:
1. ❌ **Automated Sync Scheduler**: No cron/systemd job for trade sync
2. ❌ **Signal Outcome Table**: No persistent storage for signal→trade outcomes
3. ❌ **Outcome Computation**: No logic to calculate win/loss/return_pct
4. ❌ **Performance Analytics**: No aggregate statistics by regime/confidence
5. ❌ **API Endpoint**: No `/api/analytics/signal-performance` route

**Identified Risks**:
1. **Data Freshness**: Without scheduler, trades lag reality
2. **Learning Blindspot**: Can't identify which signal types work
3. **No Feedback Loop**: Model can't improve from production data
4. **Manual Dependency**: Requires remembering to run `sync-trades`

---

## 2. Implementation Design

### 2.1 Signal Outcomes Table Schema

**Purpose**: Store one row per signal-trade pair with outcome metrics

```sql
CREATE TABLE signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Signal identification
    signal_id INTEGER NOT NULL,
    matched_trade_id INTEGER NOT NULL,
    
    -- Signal attributes (denormalized for analytics)
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_direction TEXT NOT NULL CHECK(signal_direction IN ('long', 'short')),
    confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
    regime TEXT,  -- market_phase from signal
    
    -- Trade attributes
    trade_direction TEXT NOT NULL,  -- BUY or SELL
    entry_price REAL NOT NULL,
    exit_price REAL,  -- NULL if position still open
    trade_qty REAL NOT NULL,
    
    -- Outcome metrics
    realized_pnl REAL NOT NULL,
    commission REAL NOT NULL,
    net_pnl REAL NOT NULL,  -- realized_pnl - commission
    return_pct REAL NOT NULL,  -- (net_pnl / position_value) * 100
    outcome TEXT NOT NULL CHECK(outcome IN ('win', 'loss', 'breakeven')),
    
    -- Timing
    signal_time INTEGER NOT NULL,  -- milliseconds
    trade_time INTEGER NOT NULL,
    time_delta_minutes INTEGER NOT NULL,  -- trade_time - signal_time in minutes
    
    -- Metadata
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (signal_id) REFERENCES signals(id),
    FOREIGN KEY (matched_trade_id) REFERENCES user_trade_history(id),
    UNIQUE(signal_id, matched_trade_id)  -- Prevent duplicate outcomes
);

-- Indexes for analytics queries
CREATE INDEX idx_signal_outcomes_symbol_time 
ON signal_outcomes(symbol, trade_time DESC);

CREATE INDEX idx_signal_outcomes_regime 
ON signal_outcomes(regime, outcome);

CREATE INDEX idx_signal_outcomes_confidence 
ON signal_outcomes(confidence, outcome);

CREATE INDEX idx_signal_outcomes_timeframe 
ON signal_outcomes(timeframe, outcome);
```

**Design Decisions**:
- **Denormalization**: Store signal attributes directly for fast analytics
- **Net PnL**: Pre-compute `net_pnl = realized_pnl - commission`
- **Return %**: Standardize across trade sizes
- **Outcome Classification**: Simple win/loss/breakeven (breakeven: -0.1% < return < 0.1%)
- **Uniqueness**: Prevent same signal matching multiple trades

### 2.2 Outcome Tracking Logic

**When to Create Outcome Records**:
```python
def create_signal_outcomes():
    """
    Create outcome records for newly matched trades.
    
    Called after enrich_trades_with_signals() completes.
    Only processes trades that:
    - Have matched_signal_id (not NULL)
    - Don't already have an outcome record
    """
```

**Flow**:
```
sync-trades (CLI) 
    ↓
save_trades_to_db() → Insert new trades
    ↓
enrich_trades_with_signals() → Match to signals
    ↓
create_signal_outcomes() → Generate outcome records
    ↓
Database: signal_outcomes table populated
```

**Outcome Calculation Rules**:
```python
# Position value (USDT)
position_value = entry_price * trade_qty

# Net P&L
net_pnl = realized_pnl - commission

# Return %
return_pct = (net_pnl / position_value) * 100

# Outcome classification
if return_pct > 0.1:
    outcome = 'win'
elif return_pct < -0.1:
    outcome = 'loss'
else:
    outcome = 'breakeven'

# Time delta
time_delta_minutes = (trade_time - signal_time) / (1000 * 60)
```

### 2.3 Automated Sync Scheduler

**Integration Point**: `ml_service/scheduler.py`

**New Scheduler Job**:
```python
def trade_sync_job():
    """
    Sync trades from Binance and match to signals.
    Runs every 6 hours.
    """
    logger.info("Starting trade sync job...")
    
    # 1. Fetch trades from Binance
    config = get_config_from_yaml()
    api_key = config['exchange_sync']['binance_api_key']
    api_secret = config['exchange_sync']['binance_api_secret']
    
    trades = fetch_user_trades(api_key, api_secret, limit=1000)
    
    if not trades:
        logger.warning("No trades fetched")
        return
    
    # 2. Save to database
    inserted = save_trades_to_db(trades)
    logger.info(f"Inserted {inserted} new trades")
    
    # 3. Match to signals
    matched = enrich_trades_with_signals()
    logger.info(f"Matched {matched} trades to signals")
    
    # 4. Create outcome records
    outcomes_created = create_signal_outcomes()
    logger.info(f"Created {outcomes_created} outcome records")
    
    logger.info("Trade sync job complete")

# Add to scheduler
_scheduler.add_job(
    trade_sync_job,
    trigger=IntervalTrigger(hours=6),
    id='trade_sync_job',
    name='Sync Binance trades and match to signals',
    replace_existing=True,
)
```

**VPS Deployment**:
```bash
# Option 1: systemd service (recommended)
[Unit]
Description=MoroQuant ML Service Scheduler
After=network.target

[Service]
Type=simple
User=zafka
WorkingDirectory=/home/zafka/trade-dashboard/ml_service
ExecStart=/home/zafka/trade-dashboard/ml_service/venv/bin/python -c \
    "from scheduler import start_scheduler; start_scheduler(); import time; \
    while True: time.sleep(60)"
Restart=always

[Install]
WantedBy=multi-user.target

# Option 2: Cron (fallback)
0 */6 * * * cd /home/zafka/trade-dashboard/ml_service && \
    source venv/bin/activate && python cli.py sync-trades
```

### 2.4 Analytics Functions

**Module**: `ml_service/analytics/signal_performance.py`

**Key Functions**:

```python
def compute_winrate_by_regime(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Winrate breakdown by market regime.
    
    Returns:
    {
        'trend_up': {'win_rate': 0.65, 'sample_size': 45, 'avg_return': 1.2},
        'choppy_low_vol': {'win_rate': 0.42, 'sample_size': 31, 'avg_return': -0.3},
        ...
    }
    """

def compute_winrate_by_confidence(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Winrate breakdown by confidence buckets.
    
    Returns:
    {
        '80-100': {'win_rate': 0.71, 'sample_size': 12, 'avg_return': 1.8},
        '60-79': {'win_rate': 0.58, 'sample_size': 27, 'avg_return': 0.9},
        ...
    }
    """

def compute_profit_factor_by_regime(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Profit factor (total wins / total losses) by regime.
    
    Returns:
    {
        'trend_up': {'profit_factor': 2.1, 'total_wins': 850.5, 'total_losses': 405.2},
        ...
    }
    """

def compute_expectancy_by_confidence(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Expectancy (average $ per trade) by confidence bucket.
    
    Formula: (win_rate * avg_win) - (loss_rate * avg_loss)
    
    Returns:
    {
        '80-100': {'expectancy': 12.5, 'avg_win': 25.3, 'avg_loss': 18.2},
        ...
    }
    """
```

### 2.5 API Endpoint

**Route**: `GET /api/analytics/signal-performance`

**Location**: `ml_service/api/routes.py`

**Implementation**:
```python
@router.get("/analytics/signal-performance")
async def get_signal_performance(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days_back: Optional[int] = Query(30, description="Days to look back"),
    group_by: str = Query("regime", description="Group by: regime, confidence, timeframe")
) -> Dict:
    """
    Get signal performance analytics.
    
    Returns winrate, profit factor, and expectancy metrics grouped by:
    - regime (market_phase)
    - confidence (buckets: 0-39, 40-59, 60-79, 80-100)
    - timeframe (1h, 4h)
    """
    from analytics.signal_performance import (
        compute_winrate_by_regime,
        compute_winrate_by_confidence,
        compute_profit_factor_by_regime,
        compute_expectancy_by_confidence,
        get_overall_statistics
    )
    
    if group_by == 'regime':
        winrate = compute_winrate_by_regime(symbol, days_back)
        profit_factor = compute_profit_factor_by_regime(symbol, days_back)
    elif group_by == 'confidence':
        winrate = compute_winrate_by_confidence(symbol, days_back)
        profit_factor = compute_expectancy_by_confidence(symbol, days_back)
    else:
        # timeframe grouping
        winrate = compute_winrate_by_timeframe(symbol, days_back)
        profit_factor = compute_profit_factor_by_timeframe(symbol, days_back)
    
    overall = get_overall_statistics(symbol, days_back)
    
    return {
        'status': 'success',
        'group_by': group_by,
        'symbol': symbol or 'all',
        'days_back': days_back,
        'overall': overall,
        'by_group': {
            'winrate': winrate,
            'profit_factor': profit_factor
        },
        'timestamp': datetime.now().isoformat()
    }
```

---

## 3. Risk Analysis

### 3.1 Technical Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| **Duplicate outcome records** | Medium | Medium | UNIQUE constraint on (signal_id, matched_trade_id) |
| **Signal generation gaps** | High | High | Fix root cause: implement automated signal generation scheduler |
| **False positive matches** | Medium | Low | Already mitigated by improved attribution logic |
| **Partial fills not tracked** | Low | Medium | Binance API returns individual fills; sum by order_id if needed |
| **Scheduler crash** | Medium | Low | systemd auto-restart + monitoring logs |
| **API performance** | Low | Low | Indexed queries + 30-day default window |

### 3.2 Data Quality Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Stale trades** | Can't learn from recent outcomes | Automated 6-hour sync |
| **Missing signals for trades** | Low attribution rate | Fix signal generation automation FIRST |
| **Commission not subtracted** | Inflated returns | Always compute `net_pnl = realized_pnl - commission` |
| **Position sizing ignored** | Misleading absolute P&L | Use `return_pct` for comparisons |

### 3.3 Operational Risks

| Risk | Consequence | Mitigation |
|------|-------------|------------|
| **Binance API rate limit** | Sync fails | 1000 trades/6hr well within limits |
| **Invalid API credentials** | No trades fetched | Validate on startup + log errors |
| **Database growth** | Disk space | signal_outcomes bounded by trades (low volume) |
| **Timezone confusion** | Wrong time_delta | All timestamps in UTC milliseconds |

### 3.4 Learning Risks

| Risk | Problem | Mitigation |
|------|---------|------------|
| **Insufficient sample size** | Can't trust statistics | Require min 30 samples per bucket |
| **Regime classification drift** | Old regimes != new | Store regime at signal time (done) |
| **Survivorship bias** | Only see closed trades | Track open positions separately |
| **Look-ahead bias** | Signal uses future data | Not applicable (production signals) |

---

## 4. Implementation Phases

### Phase 1: Foundation (Day 1)
**Tasks**:
1. ✅ Create signal_outcomes table schema
2. ✅ Add table to `database.py:_init_schema()`
3. ✅ Implement `create_signal_outcomes()` in `exchange_sync.py`
4. ✅ Test outcome creation with existing 1 matched trade

**Verification**:
```sql
SELECT COUNT(*) FROM signal_outcomes;
-- Expected: 1 (from existing matched trade)
```

### Phase 2: Automation (Day 1-2)
**Tasks**:
1. ✅ Add `trade_sync_job()` to `scheduler.py`
2. ✅ Integrate with existing scheduler
3. ✅ Test scheduler locally
4. ✅ Deploy to VPS with systemd

**Verification**:
```bash
systemctl --user status moroquant-scheduler
journalctl --user -u moroquant-scheduler -f
```

### Phase 3: Analytics (Day 2)
**Tasks**:
1. ✅ Create `analytics/signal_performance.py`
2. ✅ Implement winrate functions
3. ✅ Implement profit factor functions
4. ✅ Implement expectancy functions
5. ✅ Add unit tests

**Verification**:
```python
from analytics.signal_performance import compute_winrate_by_regime
result = compute_winrate_by_regime()
assert 'choppy_low_vol' in result
```

### Phase 4: API Integration (Day 2)
**Tasks**:
1. ✅ Add `/api/analytics/signal-performance` route
2. ✅ Test endpoint with curl/Postman
3. ✅ Update frontend to consume endpoint
4. ✅ Add to API docs

**Verification**:
```bash
curl http://localhost:8000/api/analytics/signal-performance?group_by=confidence
```

### Phase 5: Production Validation (Day 3)
**Tasks**:
1. ✅ Monitor first 24 hours of automated sync
2. ✅ Verify outcome records created correctly
3. ✅ Validate analytics accuracy
4. ✅ Document in AGENT.md

**Success Metrics**:
- Trade sync running every 6 hours ✅
- Attribution rate > 50% (after fixing signal generation) ✅
- Analytics API returning valid data ✅
- No duplicate outcome records ✅

---

## 5. Dependencies and Prerequisites

### 5.1 Critical Blocker

**MUST FIX FIRST**: Signal generation automation

Current signal generation is on-demand only (API calls). This is why:
- June 16-17: 0 signals generated
- Attribution rate: 4.5% (1/22 trades)

**Solution**: Add signal generation job to scheduler
```python
def signal_generation_job():
    """Generate signals for all symbols/timeframes every hour."""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ZECUSDT', ...]
    timeframes = ['1h', '4h']
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                signal = generate_signal(symbol, timeframe)
                logger.info(f"Generated signal for {symbol} {timeframe}: {signal['direction']}")
            except Exception as e:
                logger.error(f"Failed to generate {symbol} {timeframe}: {e}")

_scheduler.add_job(
    signal_generation_job,
    trigger=IntervalTrigger(hours=1),  # Generate every hour
    id='signal_generation_job',
    name='Generate signals for all symbols',
)
```

### 5.2 Schema Migration

**Required**:
- Add `signal_outcomes` table
- No changes to existing tables
- Migration is additive only (low risk)

### 5.3 Library Dependencies

**Already installed**:
- `apscheduler` (scheduler)
- `requests` (Binance API)
- `sqlite3` (database)

**No new dependencies required** ✅

---

## 6. Success Criteria

### 6.1 Functional Requirements

- [x] Trade sync fetches from Binance successfully
- [x] Trades saved to `user_trade_history`
- [ ] Trades matched to signals with >50% rate (after fixing signal generation)
- [ ] Outcome records created in `signal_outcomes`
- [ ] Automated sync runs every 6 hours without manual intervention
- [ ] Analytics API returns valid winrate/profit factor/expectancy data
- [ ] No duplicate outcome records (UNIQUE constraint working)

### 6.2 Performance Requirements

- Sync completes in <30 seconds
- Analytics queries return in <2 seconds (30-day window)
- API endpoint responds in <3 seconds
- Scheduler overhead <1% CPU

### 6.3 Data Quality Requirements

- Commission always subtracted from P&L
- Return % calculated consistently
- Time delta accurate to the minute
- Regime classification preserved from signal time
- No NULL values in required fields

---

## 7. Rollback Plan

### 7.1 If Outcome Tracking Fails

```sql
-- Drop signal_outcomes table
DROP TABLE IF EXISTS signal_outcomes;

-- Revert scheduler.py changes
git checkout HEAD -- scheduler.py

-- Remove analytics module
rm -rf analytics/signal_performance.py
```

### 7.2 If Scheduler Crashes Production

```bash
# Stop scheduler
systemctl --user stop moroquant-scheduler

# Revert to manual sync
# (existing CLI command still works)
python cli.py sync-trades
```

### 7.3 If API Performance Degrades

```python
# Add pagination to analytics endpoint
@router.get("/analytics/signal-performance")
async def get_signal_performance(
    ...
    limit: int = Query(100, description="Max records to analyze")
):
    # Limit query scope
```

---

## 8. Next Steps

### Immediate Actions (Before Implementation)

1. **Decision Required**: Fix signal generation automation FIRST?
   - Without this, attribution rate will remain low (~5%)
   - With this, expect 50-70% attribution rate
   - **Recommendation**: Implement signal_generation_job() in same PR

2. **Confirm**: VPS deployment method (systemd vs cron vs PM2)
   - **Recommendation**: systemd (best for long-running processes)

3. **Validate**: Sample size thresholds for analytics
   - **Recommendation**: Require min 30 trades per bucket before showing stats

### Implementation Order

1. Create `signal_outcomes` table ← START HERE
2. Implement `create_signal_outcomes()`
3. Test with existing 1 matched trade
4. Add `trade_sync_job()` to scheduler
5. Add `signal_generation_job()` to scheduler (critical!)
6. Build analytics functions
7. Add API endpoint
8. Deploy to VPS

---

## 9. Open Questions

1. **Signal generation**: Should we generate signals every hour for ALL symbols, or only for symbols with recent trades?
   - **Recommendation**: All symbols (needed for position comparison, paper trading)

2. **Outcome updates**: Should we update outcomes if a trade's P&L changes (e.g., funding fees)?
   - **Recommendation**: No - outcomes are immutable snapshots

3. **Confidence calibration**: Should we use raw or calibrated probabilities for analytics?
   - **Recommendation**: Use confidence_at_entry (raw) - matches what trader saw

4. **Regime transitions**: What if regime changes between signal and trade?
   - **Decision**: Use regime from signal time (already captured)

5. **Multi-leg trades**: How to handle position that closes in multiple trades?
   - **Future scope**: Sum P&L by order_id (not needed for current 22 trades)

---

## 10. Estimated Effort

| Phase | Hours | Risk |
|-------|-------|------|
| Phase 1: Foundation | 3-4h | Low |
| Phase 2: Automation | 2-3h | Medium |
| Phase 3: Analytics | 4-5h | Low |
| Phase 4: API Integration | 2h | Low |
| Phase 5: Validation | 2h | Low |
| **Total** | **13-16h** | **Low-Medium** |

**Confidence**: High (80%)  
**Unknowns**: VPS deployment quirks, signal generation scheduler load

---

## 11. Conclusion

This implementation is **low-risk, high-value** and follows a clear incremental path:

1. ✅ VPS-compatible trade sync (already working)
2. ✅ Improved signal attribution (already deployed)
3. 🔨 Add outcome tracking (new table + logic)
4. 🔨 Automate sync (scheduler job)
5. 🔨 Build analytics (SQL queries)
6. 🔨 Expose API (FastAPI route)

**Critical success factor**: Fix signal generation automation in parallel. Without hourly signal generation, attribution rate will remain low regardless of how good the matching logic is.

**Ready to proceed** with Phase 1 after approval.
