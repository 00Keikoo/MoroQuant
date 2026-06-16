# Next Steps Roadmap

**Date:** 2026-06-16  
**Status:** Based on Paper Trading Readiness Audit (72/100)  
**Priority:** Validation before new models

---

## Guiding Principles

1. **Validate robustness before adding complexity**
2. **Cross-asset validation before production**
3. **Risk management before live capital**
4. **Infrastructure before optimization**
5. **No new models until current winner is validated across regimes**

---

## Priority 1: Cross-Asset Validation (CRITICAL)

**Goal:** Confirm Triple TP=3.0 SL=1.5 works beyond BTCUSDT 1h

**Tasks:**
1. Run `compare_backtest_methods.py` on ETHUSDT, BNBUSDT, SOLUSDT (1h)
2. Test on 4h timeframe for all symbols
3. Document Sharpe/Sortino/PF for each (symbol, timeframe) pair
4. Identify which assets/timeframes fail (Sharpe < 2.0)
5. Analyze failure modes: prediction collapse, low confidence, poor win rate

**Success Criteria:**
- Sharpe > 2.0 on at least 3 out of 4 symbols (1h)
- Sharpe > 1.5 on 4h timeframe
- No prediction collapse to single class
- Confidence distributions remain reasonable (mean > 0.55)

**Expected Findings:**
- Some assets may fail completely (document and exclude)
- Confidence thresholds may need asset-specific tuning
- Different labeling methods may win on different assets

**Estimated Time:** 8-12 hours

**Command:**
```bash
# Test multiple symbols
python -m ml_service.compare_backtest_methods --symbol ETHUSDT --symbol BNBUSDT --timeframe 1h

# Test 4h timeframe
python -m ml_service.compare_backtest_methods --symbol BTCUSDT --timeframe 4h
```

**Output:** Create `docs/cross_asset_validation.md` with results table

---

## Priority 2: Regime Robustness Validation (HIGH)

**Goal:** Validate consistency across market regimes

**Tasks:**
1. Fix any remaining issues in `regime_validation.py`
2. Run on BTCUSDT 1h with default windows (1000 rows, 200 step)
3. Analyze rank stability: does TP=3.0/1.5 consistently rank #1?
4. Check consistency: what % of windows have positive Sharpe?
5. Examine worst-performing windows to identify failure regimes

**Success Criteria:**
- Average rank ≤ 2.0 for Triple TP=3.0 SL=1.5
- Consistency > 60% (positive Sharpe in 60%+ windows)
- Times best > times worst by factor of 2x

**Expected Findings:**
- Some regimes (sideways, low volatility) may underperform
- Rank stability may be lower than single-window Sharpe suggests
- Need regime-specific model selection or confidence thresholds

**Estimated Time:** 4-6 hours (assuming script runs without errors)

**Command:**
```bash
python -m ml_service.regime_validation --symbol BTCUSDT --timeframe 1h
```

**Output:** Regime validation report with rank stability table

---

## Priority 3: Feature Importance Analysis (MEDIUM)

**Goal:** Understand which features drive predictions

**Tasks:**
1. Extract feature importance from trained models
2. Aggregate importance across walk-forward folds
3. Identify top 10 features for each labeling method
4. Check for redundant features (correlated, low importance)
5. Validate no lookahead features (VWAP issue)

**Success Criteria:**
- Top 10 features account for 70%+ of importance
- No suspicious features (e.g., future-looking)
- Clear difference in feature usage by labeling method

**Analysis:**
- EMA features likely dominant for Fixed Horizon
- ATR likely important for Triple Barrier methods
- Volume/regime features may differentiate winners

**Estimated Time:** 6-8 hours

**Implementation:** Add feature importance logging to `compare_backtest_methods.py`

---

## Priority 4: Position Sizing Implementation (CRITICAL)

**Goal:** Add confidence-based position sizing with risk limits

**Tasks:**
1. Design position sizing function: `calculate_position_size(capital, confidence, risk_per_trade)`
2. Implement Kelly criterion or fixed fractional approach
3. Add max risk per trade (1-2% of capital)
4. Add min/max position size limits
5. Backtest with new position sizing to validate P&L impact

**Formula (confidence-weighted):**
```python
base_risk = 0.02  # 2% of capital max
position_size = base_risk * capital * confidence
position_size = clip(position_size, min_size, max_size)
```

**Success Criteria:**
- Backtest Sharpe remains > 8.0 with position sizing
- Max single-trade risk = 2% of capital
- Drawdown improves compared to 100% capital usage

**Estimated Time:** 8-12 hours

**Files to modify:**
- `compare_backtest_methods.py:run_backtest_simulation()`
- Add `utils/position_sizing.py`

---

## Priority 5: Risk Management Framework (CRITICAL)

**Goal:** Add circuit breakers and protective mechanisms

**Tasks:**
1. Implement daily loss limit (-5% max)
2. Implement max drawdown circuit breaker (-10%)
3. Add position count limits (max 3 concurrent)
4. Enforce stop-losses from triple barrier parameters
5. Build emergency kill switch (pause all trading)

**Implementation:**
```python
class RiskManager:
    def check_daily_loss_limit(self, current_pnl, initial_capital) -> bool
    def check_max_drawdown(self, peak_capital, current_capital) -> bool
    def check_position_limits(self, open_positions) -> bool
    def should_allow_trade(self, trade_signal) -> bool
```

**Success Criteria:**
- Backtests respect all limits
- Kill switch stops trading immediately
- Alerts trigger before limits exceeded

**Estimated Time:** 16-24 hours

**Files to create:**
- `ml_service/risk/manager.py`
- `ml_service/risk/limits.py`

---

## Priority 6: Production API Scaffold (CRITICAL)

**Goal:** Build minimal production infrastructure

**Tasks:**
1. FastAPI endpoint: `/predict` (get signal for symbol/timeframe)
2. Model loading and caching (avoid reloading every request)
3. Feature calculation endpoint (real-time OHLCV → features)
4. Health check endpoint
5. Basic logging (requests, predictions, latency)

**Endpoints:**
```
GET  /health              → {status: "ok", model_version: "..."}
POST /predict             → {symbol, timeframe} → {signal, confidence, timestamp}
GET  /model/info          → {labeling_method, trained_at, metrics}
POST /model/reload        → Reload model from disk
```

**Success Criteria:**
- Predictions match backtest results (deterministic)
- Latency < 500ms per prediction
- Models loaded once, cached in memory

**Estimated Time:** 12-16 hours

**Files to create:**
- `ml_service/api/production.py`
- `ml_service/serving/model_cache.py`

---

## Priority 7: Trade Logging and Monitoring (HIGH)

**Goal:** Persist all trading activity and monitor performance

**Tasks:**
1. Database schema for trades, positions, P&L
2. Trade execution logger (entry, exit, P&L)
3. Daily P&L aggregation
4. Confidence distribution tracking
5. Alert on anomalies (confidence drop, zero trades, API errors)

**Schema:**
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    timeframe TEXT,
    signal TEXT,  -- long/short/neutral
    confidence REAL,
    entry_price REAL,
    exit_price REAL,
    pnl REAL,
    timestamp INTEGER
);
```

**Estimated Time:** 8-12 hours

---

## Priority 8: Exchange Integration (Paper Trading Mode) (HIGH)

**Goal:** Connect to exchange API in paper trading mode

**Tasks:**
1. Select exchange (Binance Testnet recommended)
2. Implement order placement (market orders only initially)
3. Position tracking (open/close positions)
4. Paper trading mode (simulated fills, no real capital)
5. Error handling (rate limits, network failures, order rejections)

**Success Criteria:**
- Orders execute without errors
- Fill prices logged for slippage analysis
- No API key leaks or security issues

**Estimated Time:** 16-24 hours

---

## Priority 9: End-to-End Integration Testing (HIGH)

**Goal:** Test full pipeline from data → prediction → order → fill

**Tasks:**
1. Build integration test: load data → generate signal → place order
2. Test error scenarios: API down, bad data, model failure
3. Test circuit breakers: daily loss limit, max drawdown
4. Dry run for 24 hours with paper trading
5. Document all failures and edge cases

**Success Criteria:**
- Zero crashes during 24-hour dry run
- All circuit breakers activate correctly
- Predictions match backtests (same data)

**Estimated Time:** 12-16 hours

---

## Priority 10: Multi-Timeframe Validation (MEDIUM)

**Goal:** Test if different timeframes need different models

**Tasks:**
1. Train separate models for 1h, 4h, 1d
2. Compare performance: can single model work across timeframes?
3. Test multi-timeframe ensembles (1h + 4h signals)
4. Analyze timeframe-specific features (longer EMAs for 4h)

**Expected Finding:**
- 1h model may fail on 4h data (different regime dynamics)
- Need separate models or timeframe-specific features

**Estimated Time:** 8-12 hours

---

## Items EXPLICITLY NOT Prioritized

**Avoid until validation complete:**

1. ❌ New model architectures (neural networks, ensemble stacking)
2. ❌ Feature engineering experiments (new indicators)
3. ❌ Hyperparameter optimization (Optuna, grid search)
4. ❌ Advanced calibration methods (temperature scaling, Venn-ABERS)
5. ❌ Live trading deployment
6. ❌ UI/dashboard development
7. ❌ Portfolio optimization (multi-asset allocation)

**Rationale:** Current winner (Triple TP=3.0/1.5 + 60% conf) achieves Sharpe 10.33 on single asset/timeframe. Validate it works robustly before adding complexity.

---

## Roadmap Timeline

**Phase 1: Validation (2-3 weeks)**
- Week 1: Cross-asset + regime robustness validation
- Week 2: Feature analysis + position sizing
- Week 3: Risk management + production API

**Phase 2: Infrastructure (2-3 weeks)**
- Week 1: Trade logging + monitoring
- Week 2: Exchange integration + testing
- Week 3: Multi-timeframe validation

**Phase 3: Paper Trading (4-8 weeks)**
- Month 1: Live paper trading with monitoring
- Month 2: Analyze execution quality vs backtests

**Phase 4: Live Trading (only after successful paper trading)**
- Start with small capital ($500-1000)
- Scale gradually based on performance

---

## Success Metrics

**By end of Phase 1:**
- [ ] Cross-asset validation complete
- [ ] Regime robustness confirmed (avg rank ≤ 2.0)
- [ ] Position sizing implemented
- [ ] Risk management active

**By end of Phase 2:**
- [ ] Production API operational
- [ ] Trade logging functional
- [ ] Paper trading integrated

**By end of Phase 3:**
- [ ] 30+ paper trades executed
- [ ] Execution quality measured
- [ ] Sharpe remains > 5.0 in paper trading

---

## Decision Points

**After Cross-Asset Validation:**
- If Sharpe < 2.0 on 3/4 assets → STOP, investigate feature/label issues
- If only BTCUSDT works → Proceed with single asset, but acknowledge limitation

**After Regime Validation:**
- If consistency < 50% → STOP, add regime detection
- If rank stability poor → Consider regime-specific models

**After Paper Trading (30+ trades):**
- If realized Sharpe < 3.0 → STOP, backtest assumptions broken
- If execution slippage > 0.1% → Adjust fee assumptions

---

## Long-Term Vision (6+ months out)

1. Multi-asset portfolio (5-10 symbols)
2. Regime-adaptive model selection
3. Multi-timeframe signal fusion (1h + 4h + 1d)
4. Real-time market microstructure features
5. Advanced risk management (correlation limits, sector exposure)

**But first: validate current winner works robustly across assets and regimes.**

---

## Summary

**Focus for next 2-3 weeks:**
1. Cross-asset validation (CRITICAL)
2. Regime robustness (HIGH)
3. Position sizing (CRITICAL)
4. Risk management (CRITICAL)
5. Production API (CRITICAL)

**Avoid until validation complete:**
- New models
- Feature experiments
- Live trading

**Validation before optimization. Robustness before complexity.**
