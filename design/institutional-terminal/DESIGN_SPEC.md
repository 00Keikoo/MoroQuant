# MoroQuant V2 — Institutional Trading Operating System
## Frontend UI/UX Redesign Specification

**Version:** 2.0.0  
**Date:** 2026-07-16  
**Status:** Design Phase

---

## 1. Design Philosophy

MoroQuant V2 is being transformed into an institutional-grade trading terminal that combines the professional density of Bloomberg Terminal with the modern UX of platforms like Axon Trade, Hyperliquid, and TradingView.

### Core Principles
- **Minimal & Dense:** Every pixel communicates useful information
- **Real-time First:** All data updates automatically without user intervention
- **Zero Unnecessary Animation:** Professional tools don't distract
- **Dark Theme:** Optimized for extended trading sessions
- **Information Hierarchy:** Critical data always visible

### Design Inspirations
- Bloomberg Terminal (density, professional layout)
- Axon Trade (modern institutional UX)
- Hyperliquid (clean execution interface)
- TradingView (charting excellence)
- Binance Futures (real-time market data)

---

## 2. Trading Mode Architecture

### 2.1 Trading Mode Switch

**Location:** Top navigation, always visible

```
┌────────────────────────────────────────┐
│  [●LIVE]   [ PAPER]   [ OFF]          │
└────────────────────────────────────────┘
```

**Behavior:**

#### LIVE Mode
- Source: Real Binance APIs
- Real account equity
- Real balance and margin
- Real positions with mark prices
- Real PnL calculations
- Real execution
- Emergency Stop: **ACTIVE**

#### PAPER Mode
- Source: Paper Broker APIs
- Paper account simulation
- Paper positions
- Paper balance and equity
- Paper execution
- Emergency Stop: **DISABLED** (paper continues)

#### OFF Mode
- Trading: **DISABLED**
- No position opening
- No execution
- Analytics: **VISIBLE** (historical)
- Emergency Stop: **DISABLED**

**State Management:**
- API Endpoint: `GET/POST /api/trading/mode`
- Response: `{ mode: 'LIVE' | 'PAPER' | 'OFF', updated_at: string }`
- Frontend Hook: `useTradingMode()`

### 2.2 Emergency Stop Button

**Location:** Beside Trading Mode Switch

```
┌─────────────────────────────────────────────┐
│  [●LIVE] [PAPER] [OFF]    🛑 EMERGENCY STOP │
└─────────────────────────────────────────────┘
```

**Visual Design:**
- Color: Deep Red (#DC2626)
- Size: Prominent, 48px height
- Font: Bold, all caps
- Icon: Stop sign or shield
- Hover: Darker red with glow

**Behavior:**

**LIVE Mode:**
```
Click Emergency Stop →
  1. Disable autonomous trading
  2. Cancel future automated entries
  3. Keep existing positions (unless backend policy overrides)
  4. Stop scheduler from opening new positions
  5. Set mode to OFF
  6. Show confirmation dialog
```

**PAPER Mode:**
```
Emergency Stop has NO effect
Paper trading continues for research
Button is disabled/grayed out
```

**OFF Mode:**
```
Button is disabled
Already in safe state
```

**API Endpoint:** `POST /api/trading/emergency-stop`

---

## 3. Institutional Header

**Layout:** Full-width top bar

```
┌─────────────────────────────────────────────────────────────────────────┐
│ MODE: ●LIVE  │  EQUITY: $10,245.67  │  BAL: $8,234.11  │  MARGIN: $2,011│
│ UNREALIZED: +$234.56 (+2.34%)  │  REALIZED: +$1,289.45  │  DAILY: +$89  │
│ UPDATED: 19:55:03  │  ⚡ CONNECTED  │  🔄 AUTO-REFRESH                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Metrics:**

| Metric | Source (LIVE) | Source (PAPER) | Update Frequency |
|--------|---------------|----------------|------------------|
| Current Equity | Binance Account | Paper Account | Real-time |
| Available Balance | Binance Wallet | Paper Balance | Real-time |
| Margin Used | Binance Positions | Paper Positions | Real-time |
| Free Margin | Calculated | Calculated | Real-time |
| Unrealized PnL | Sum of open positions | Sum of open paper positions | Real-time |
| Realized PnL | Closed trades | Paper closed trades | On trade close |
| Daily PnL | Today's equity change | Today's paper equity change | Real-time |
| Last Update | System timestamp | System timestamp | Every tick |
| Connection Status | WebSocket state | API state | Real-time |

---

## 4. Main Dashboard Layout

### 4.1 Three-Column Institutional Layout

```
┌──────────────┬────────────────────────┬──────────────┐
│              │                        │              │
│   COLUMN 1   │      COLUMN 2          │   COLUMN 3   │
│              │                        │              │
│  Portfolio   │   Equity Curve         │   Model      │
│  Overview    │   (Large)              │   Intel      │
│              │                        │              │
│  Open        │   Statistics           │   Risk       │
│  Positions   │   - Win Rate           │   Panel      │
│              │   - Profit Factor      │              │
│  Recent      │   - Sharpe             │   Latest     │
│  Trades      │   - Drawdown           │   Signals    │
│              │                        │              │
└──────────────┴────────────────────────┴──────────────┘
```

### 4.2 Column 1: Portfolio & Positions

#### Portfolio Overview Card
```
┌─────────────────────────────────┐
│  PORTFOLIO OVERVIEW             │
├─────────────────────────────────┤
│  Current Equity    $10,245.67   │
│  Daily PnL         +$89.23      │
│  Unrealized PnL    +$234.56     │
│  Realized PnL      +$1,289.45   │
│  Margin Used       $2,011.00    │
│  Free Margin       $6,223.11    │
│  Total Exposure    $15,234.00   │
│  Account Health    ████████░░ 85%│
└─────────────────────────────────┘
```

**Data Sources:**
- LIVE: `GET /api/binance/account` or equivalent
- PAPER: `GET /api/paper/account/live`

#### Open Positions Table

**Columns:**
- Symbol
- Side (LONG/SHORT)
- Size (USDT)
- Entry Price
- Mark Price
- PnL ($)
- PnL (%)
- Margin
- Confidence
- Model
- Duration
- Status
- Updated

**Data Sources:**
- LIVE: Binance open positions
- PAPER: `GET /api/paper/positions/live`

**Update Frequency:** Real-time via WebSocket or 1s polling

#### Recent Trades Panel

**Columns:**
- Time
- Symbol
- Side
- Entry
- Exit
- PnL ($)
- PnL (%)
- Confidence
- Exit Reason
- Execution Quality (EQS)

**Data Sources:**
- LIVE: Recent closed trades
- PAPER: `GET /api/paper/positions/closed?limit=10`

### 4.3 Column 2: Equity Curve & Statistics

#### Equity Curve (Primary Focus)

**Critical Requirement:** Must use **historical account equity snapshots**, NOT cumulative PnL.

**Features:**
- Large, prominent chart
- Zoom controls
- Hover tooltips showing:
  - Timestamp
  - Equity value
  - Daily change
  - Drawdown from peak
- Drawdown overlay (shaded area)
- Peak equity line
- Starting equity baseline

**Data Sources:**
- LIVE: `GET /api/equity-history` or account equity snapshots
- PAPER: `GET /api/paper/equity-history?range=all`

**Chart Library:** Recharts or Lightweight Charts

**Example Structure:**
```typescript
interface EquityPoint {
  timestamp: string;
  equity: number;
  balance: number;
  unrealized_pnl: number;
}
```

**Rendering Logic:**
```
1. Fetch equity history
2. Calculate drawdown from peak
3. Plot equity line
4. Shade drawdown areas
5. Add hover interactions
6. Auto-refresh every 10 seconds
```

#### Performance Statistics

```
┌─────────────────────────────────┐
│  PERFORMANCE METRICS            │
├─────────────────────────────────┤
│  Win Rate          67.8%        │
│  Profit Factor     2.34         │
│  Expectancy        $12.45       │
│  Sharpe Ratio      1.89         │
│  Sortino Ratio     2.45         │
│  Calmar Ratio      3.12         │
│  Recovery Factor   2.89         │
│  Max Drawdown      -8.9%        │
│  Avg Win           $45.67       │
│  Avg Loss          -$23.45      │
│  Avg Hold Time     4.5h         │
└─────────────────────────────────┘
```

**Data Sources:**
- LIVE: Calculate from closed trades
- PAPER: `GET /api/paper/analytics`

### 4.4 Column 3: Model Intelligence & Risk

#### Model Intelligence Panel

```
┌─────────────────────────────────┐
│  MODEL INTELLIGENCE             │
├─────────────────────────────────┤
│  Current Model                  │
│  BTCUSDT_1H_XGB_v1.3           │
│                                 │
│  Prediction Confidence          │
│  ████████░░ 82%                 │
│                                 │
│  Signal Strength                │
│  ██████░░░░ 65%                 │
│                                 │
│  Market Regime                  │
│  🟢 TRENDING_UP                 │
│                                 │
│  Model Drift                    │
│  🟢 LOW (0.12)                  │
│                                 │
│  Execution Quality              │
│  ███████░░░ 78%                 │
│                                 │
│  Risk Score                     │
│  🟡 MEDIUM (0.45)               │
└─────────────────────────────────┘
```

**Data Sources:**
- Model metadata from model registry
- Drift metrics: `GET /api/models/{symbol}/{timeframe}/drift`
- Execution quality: `GET /api/paper/analytics/execution`

#### Risk Panel

```
┌─────────────────────────────────┐
│  RISK MANAGEMENT                │
├─────────────────────────────────┤
│  Total Exposure    $15,234.00   │
│  Risk Score        🟡 MEDIUM    │
│  Open Risk         $456.78      │
│  Daily Loss        -$0.00       │
│  Max Drawdown      -8.9%        │
│  Current Leverage  1.5x         │
│  Liquidation Buf   45.6%        │
│  Emergency Status  🟢 NORMAL    │
└─────────────────────────────────┘
```

#### Latest Signals

```
┌─────────────────────────────────┐
│  ACTIVE SIGNALS (3)             │
├─────────────────────────────────┤
│  🔵 BTCUSDT  LONG   82%   1H    │
│  🔴 ETHUSDT  SHORT  75%   4H    │
│  🔵 SOLUSDT  LONG   68%   1H    │
└─────────────────────────────────┘
```

**Data Sources:**
- `GET /api/signals/active`

---

## 5. Bloomberg-Style Status Bar

**Location:** Bottom of screen, fixed position

```
┌───────────────────────────────────────────────────────────────────────────┐
│ MODE: PAPER │ MODEL: BTCUSDT_1H_XGB_v1.3 │ Scheduler: ●RUNNING │         │
│ Paper Broker: ●RUNNING │ Signal Engine: ●RUNNING │ Market Data: ●CONNECTED│
│ Binance WS: ●CONNECTED │ Latency: 42ms │ Last Candle: 19:55:00 │         │
│ API: ●HEALTHY │ DB: ●HEALTHY                                              │
└───────────────────────────────────────────────────────────────────────────┘
```

**Status Indicators:**

| Component | States | Colors |
|-----------|--------|--------|
| MODE | LIVE, PAPER, OFF | Green (PAPER), Red (LIVE), Gray (OFF) |
| MODEL | Current active model | White text |
| Scheduler | RUNNING, STOPPED | Green, Red |
| Paper Broker | RUNNING, STOPPED | Green, Red |
| Signal Engine | RUNNING, STOPPED | Green, Red |
| Market Data | CONNECTED, DISCONNECTED | Green, Red |
| Binance WS | CONNECTED, DISCONNECTED, RECONNECTING | Green, Red, Yellow |
| Latency | <100ms, 100-500ms, >500ms | Green, Yellow, Red |
| Last Candle | Timestamp | White |
| API | HEALTHY, DEGRADED, DOWN | Green, Yellow, Red |
| DB | HEALTHY, SLOW, DOWN | Green, Yellow, Red |

**Data Sources:**
- Trading mode: `GET /api/trading/mode`
- System health: `GET /api/health` (needs to be created)
- Scheduler status: `GET /api/scheduler/status`
- Market data: WebSocket connection state
- Latency: Measure ping to backend

**Update Frequency:** 1 second polling

---

## 6. Component Architecture

### 6.1 New Components to Create

```
components/terminal/
├── TradingModeSwitch.tsx        # LIVE/PAPER/OFF switcher
├── EmergencyStopButton.tsx      # Emergency stop control
├── InstitutionalHeader.tsx      # Top metrics bar
├── StatusBar.tsx                # Bloomberg-style status bar
├── EquityCurve.tsx             # Large equity chart
├── PortfolioOverview.tsx       # Portfolio summary card
├── OpenPositionsTable.tsx      # Real-time positions
├── RecentTradesPanel.tsx       # Latest closed trades
├── ModelIntelligence.tsx       # Model health & metrics
├── RiskPanel.tsx               # Risk management display
├── PerformanceStats.tsx        # Statistics panel
└── ActiveSignals.tsx           # Current signals list
```

### 6.2 State Management

**New Hooks:**
```typescript
// lib/hooks/useTradingMode.ts
export function useTradingMode() {
  // Manages LIVE/PAPER/OFF state
  // Handles mode switching
  // Provides emergency stop function
}

// lib/hooks/useEquityHistory.ts
export function useEquityHistory(mode: TradingMode) {
  // Fetches equity snapshots based on mode
  // Auto-refreshes every 10s
}

// lib/hooks/useSystemHealth.ts
export function useSystemHealth() {
  // Monitors scheduler, broker, signals, API, DB
  // Updates status bar
}

// lib/hooks/useLivePositions.ts
export function useLivePositions(mode: TradingMode) {
  // Real-time position data
  // Switches data source based on mode
}
```

### 6.3 API Contracts (No Changes)

**Existing APIs to Use:**
- `GET /api/trading/mode` - Current trading mode
- `POST /api/trading/mode` - Change mode
- `POST /api/trading/emergency-stop` - Emergency stop
- `GET /api/paper/account/live` - Paper account state
- `GET /api/paper/positions/live` - Paper positions with mark prices
- `GET /api/paper/equity-history` - Paper equity curve
- `GET /api/paper/analytics` - Paper performance metrics
- `GET /api/paper/analytics/execution` - Execution analytics

**New APIs Needed (Backend Team):**
- `GET /api/live/account` - Real Binance account
- `GET /api/live/positions` - Real open positions
- `GET /api/live/equity-history` - Real equity snapshots
- `GET /api/health` - System health status
- `GET /api/scheduler/status` - Scheduler state

---

## 7. Design System (Institutional Quant Core)

**From:** `/design/stitch/current/institutional_quant_core/DESIGN.md`

### Colors

**Surfaces:**
- Background: `#090909`
- Panel: `#141414`
- Container: `#1C1C1C`
- Border: `#262626`

**Accent:**
- Primary: `#FF6B00` (Institutional Orange)
- Success: `#10B981` (Mint Green)
- Danger: `#DC2626` (High-visibility Red)
- Warning: `#F59E0B` (Amber)

**Text:**
- Primary: `#FFFFFF`
- Secondary: `#A1A1A1`
- Tertiary: `#666666`

### Typography

**Font Stack:**
1. **Structural:** IBM Plex Sans (headers, titles)
2. **Interface:** Inter (labels, UI text)
3. **Data:** JetBrains Mono (prices, numbers, tickers)

**Sizes:**
- Display: 24px / 600 weight
- Header: 16px / 500 weight
- Body: 13px / 400 weight
- Data: 12px / 500 weight (monospace)
- Label: 10px / 700 weight (caps)

### Spacing

**Grid:** 4px base unit
- XS: 4px
- SM: 8px
- MD: 12px
- LG: 16px
- XL: 24px

### Components

**Buttons:**
- Primary: `bg-[#FF6B00]` `text-white` `rounded-sm`
- Secondary: `border border-[#262626]` `bg-transparent` `text-[#A1A1A1]`
- Ghost: `text-[#A1A1A1]` `hover:text-white`

**Data Tables:**
- Header: 24px height, `#141414` bg, 1px `#262626` bottom border
- Row: 28px height, 1px `#262626` divider
- Hover: `#1C1C1C` bg
- Numbers: JetBrains Mono, right-aligned

**Status Chips:**
- Height: 16px
- Border-radius: 2px
- Colors: Semantic (green/red/orange)

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create Trading Mode Switch component
- [ ] Create Emergency Stop button
- [ ] Implement `useTradingMode()` hook
- [ ] Build Institutional Header
- [ ] Setup 3-column layout structure

### Phase 2: Data Integration (Week 1-2)
- [ ] Implement equity curve with historical data
- [ ] Build Portfolio Overview card
- [ ] Create Open Positions table (real-time)
- [ ] Build Recent Trades panel
- [ ] Add auto-refresh logic

### Phase 3: Intelligence & Risk (Week 2)
- [ ] Build Model Intelligence panel
- [ ] Create Risk Panel
- [ ] Implement Performance Statistics
- [ ] Add Active Signals display

### Phase 4: Status & Polish (Week 2-3)
- [ ] Build Bloomberg-style status bar
- [ ] Implement system health monitoring
- [ ] Add WebSocket state tracking
- [ ] Performance optimization
- [ ] Responsive design adjustments

### Phase 5: Testing & Validation (Week 3)
- [ ] Test LIVE mode with real data
- [ ] Test PAPER mode isolation
- [ ] Test OFF mode behavior
- [ ] Test Emergency Stop scenarios
- [ ] Load testing with real-time updates

---

## 9. Technical Specifications

### Real-time Update Strategy

**WebSocket Connections:**
- Market data: Binance WebSocket
- Position updates: Backend SSE or polling
- Equity updates: 10-second polling

**Polling Intervals:**
- Positions: 1 second
- Account: 2 seconds
- Equity: 10 seconds
- Performance: 30 seconds
- System health: 1 second

### Performance Targets

- Initial load: < 2 seconds
- Position update latency: < 100ms
- UI responsiveness: 60 FPS
- Memory usage: < 150MB
- Network bandwidth: < 100KB/s steady state

### Browser Compatibility

- Chrome 120+
- Firefox 120+
- Edge 120+
- Safari 17+

---

## 10. User Flows

### Starting a Trading Session

```
1. User loads dashboard
2. Dashboard shows current mode (PAPER/OFF)
3. User reviews portfolio state
4. User switches to LIVE mode (if desired)
5. System confirms mode switch
6. Header updates to show LIVE metrics
7. Positions table switches to real data
8. Status bar shows all systems operational
```

### Emergency Stop Flow

```
1. User sees market event requiring intervention
2. User clicks EMERGENCY STOP button
3. System prompts: "Disable autonomous trading?"
4. User confirms
5. Trading mode switches to OFF
6. Scheduler stops opening new positions
7. Existing positions remain open
8. Status bar shows: Scheduler: STOPPED
9. User manually manages existing positions
```

### Normal Operation

```
1. Dashboard loads in PAPER mode
2. Real-time equity curve updates
3. New position opens (paper)
4. Position appears in table immediately
5. Equity curve adjusts in real-time
6. PnL updates every second
7. Status bar shows all green
8. User monitors without intervention
```

---

## 11. Design Assets Needed

**Icons:**
- Emergency stop icon (shield/octagon)
- Connection status icons
- Mode indicators (LIVE/PAPER/OFF)
- Health status dots

**Colors:**
- Mode-specific colors (LIVE red, PAPER green, OFF gray)
- Semantic colors (profit green, loss red)
- Status colors (healthy green, warning yellow, error red)

**No custom graphics or illustrations needed** - keep it minimal and terminal-like.

---

## 12. Success Metrics

**User Experience:**
- Time to understand current state: < 5 seconds
- Time to emergency stop: < 2 seconds
- Information density: 20+ metrics visible without scrolling

**Technical:**
- Real-time update latency: < 100ms
- UI render time: < 16ms (60 FPS)
- Error rate: < 0.1%
- Uptime: 99.9%

**Business:**
- User confidence in data accuracy: High
- Time spent monitoring: Reduced (automated)
- Decision-making speed: Improved
- False alarm rate: Low

---

## 13. Open Questions

1. ~~Do we need MAINTENANCE mode in addition to LIVE/PAPER/OFF?~~
   - **Decision:** No, OFF serves this purpose

2. Should Emergency Stop close positions or just halt new entries?
   - **Decision:** Halt new entries, keep existing (configurable in backend)

3. What's the historical equity data retention policy?
   - **Needed:** Clarify with backend team

4. Real-time updates: WebSocket or polling?
   - **Decision:** Hybrid - WebSocket for market data, polling for account state

5. Mobile/tablet support priority?
   - **Decision:** Desktop-first, mobile is secondary

---

## 14. References

- [Institutional Quant Core Design System](/design/stitch/current/institutional_quant_core/DESIGN.md)
- [Trading Mode Backend](/ml_service/trading/mode_manager.py)
- [Paper Broker API](/ml_service/api/routes.py)
- [ML Trading API Types](/lib/types/ml.ts)
- [Current Dashboard](/app/dashboard/page.tsx)

---

**End of Design Specification**
