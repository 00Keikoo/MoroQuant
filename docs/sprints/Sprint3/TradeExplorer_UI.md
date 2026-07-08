# Trade Explorer - UI Design Specification

**Sprint 3, Task 3.1**  
**Date:** 2026-07-06  
**Status:** Design Phase

---

## 1. Executive Summary

Trade Explorer is a research-focused UI that enables quant developers and researchers to analyze paper trading execution quality. Unlike the Dashboard page (real-time monitoring) or Trading page (signal execution), Trade Explorer provides deep post-trade analysis of closed positions.

The interface surfaces execution intelligence metrics (MAE, MFE, PCR, EQS) alongside signal attribution data (confidence, regime, probabilities) to answer questions like: "Did the model predict correctly but execution fail?", "Which regimes produce the best trades?", and "How well do high-confidence signals perform?"

Trade Explorer is read-only and safe to use during live trading. It does not modify paper trading state or trigger any executions. The design prioritizes information density over simplicity, assuming users are technical and research-oriented.

**Core User Journey:**  
Filter trades by regime/confidence → Review aggregate analytics → Drill into specific trades → Diagnose model vs execution issues → Export findings for research.

---

## 2. Design Goals

### Read-Only Interface
- Zero write operations to paper trading database
- Safe for concurrent use during live trading
- No risk of accidental trade execution or state modification
- Clear visual distinction from Trading page (no action buttons)

### Research First
- Information density over simplicity (users are technical)
- Expose all execution intelligence metrics without hiding complexity
- Support deep filtering and multi-dimensional analysis
- Enable hypothesis testing ("Do trailing stops improve EQS?")

### Fast Navigation
- Minimal clicks from list to detail and back
- Persistent filters across page navigation
- Direct URL access to filtered views (shareable links)
- Keyboard shortcuts for power users (arrow keys, Enter to drill in)

### Clean Information Hierarchy
- Critical metrics at-a-glance (win rate, profit factor, EQS)
- Progressive disclosure: summary → list → detail
- Visual grouping: trade basics | execution intelligence | signal attribution
- Consistent metric formatting across all views

### Desktop-First
- Optimized for 1920×1080 and larger displays
- No mobile breakpoints in MVP (research workstation use case)
- Table-based layouts with horizontal scrolling if needed
- Multi-column detail views

### MVP Simplicity
- No charts or visualizations in MVP (MAE/MFE distributions deferred)
- No export functionality (CSV export in Phase 2)
- No comparison mode (compare policies/regimes in Phase 2)
- No real-time updates (manual refresh only)
- Focus on core filtering, sorting, and drill-down

---

## 3. User Personas

### Quant Researcher

**Role:** Develops and validates trading models, evaluates signal quality

**Goals:**
- Analyze model performance by confidence level and market regime
- Identify when model predictions are correct but execution fails
- Compare execution policies (fixed SL vs trailing stops)
- Validate signal attribution accuracy

**Workflow:**
1. Filter trades by regime ("bullish_trending") and confidence (>70)
2. Review aggregate win rate and profit factor
3. Identify trades with high MFE but low PCR (execution issues)
4. Drill into specific trades to diagnose failure modes
5. Document findings for model iteration

**Pain Points:**
- Existing paper endpoints return raw data (requires manual analysis)
- No visibility into MAE/MFE or profit capture ratio
- Cannot filter by execution classification
- Difficult to trace trades back to signal parameters

**Technical Level:** High (comfortable with SQL, statistical metrics, ML concepts)

---

### Quant Developer

**Role:** Implements and maintains paper trading infrastructure, tunes execution policies

**Goals:**
- Debug paper trading lifecycle issues
- Evaluate execution policy effectiveness (break-even, trailing stops)
- Monitor execution quality over time (EQS trends)
- Validate that MAE/MFE tracking is accurate

**Workflow:**
1. Filter trades by execution policy and status
2. Sort by EQS to identify outlier trades
3. Inspect trade detail to verify lifecycle events (SL moves, TP hits)
4. Compare MAE/MFE timestamps against entry/exit times
5. Adjust execution policy parameters based on findings

**Pain Points:**
- No structured view of execution intelligence metrics
- Difficult to trace execution policy decisions (when did trailing stop activate?)
- Cannot quickly identify trades with unusual MAE/MFE patterns
- Limited visibility into why trades closed (TP vs SL vs expired)

**Technical Level:** High (writes Python/SQL, understands paper broker internals)

---

## 4. Information Architecture

```
Trade Explorer
│
├── Summary (Top-level analytics)
│   ├── Aggregate KPIs (all filtered trades)
│   │   ├── Win Rate
│   │   ├── Profit Factor
│   │   ├── Total PnL
│   │   ├── Average EQS
│   │   └── Trade Count
│   │
│   └── Breakdowns (groupings)
│       ├── By Confidence Tier
│       ├── By Market Regime
│       └── By Execution Policy
│
├── Trades (Filterable trade list)
│   ├── Filter Panel
│   │   ├── Symbol (dropdown)
│   │   ├── Status (multi-select)
│   │   ├── Direction (LONG/SHORT)
│   │   ├── Regime (multi-select)
│   │   ├── Confidence Range (slider)
│   │   ├── PnL Range (numeric inputs)
│   │   ├── Date Range (date pickers)
│   │   └── EQS Range (slider)
│   │
│   ├── Trade List Table
│   │   ├── Sortable Columns
│   │   │   ├── Symbol
│   │   │   ├── Entry/Exit Prices
│   │   │   ├── PnL / PnL %
│   │   │   ├── Duration
│   │   │   ├── Confidence
│   │   │   ├── EQS
│   │   │   └── Closed At
│   │   │
│   │   ├── Visual Indicators
│   │   │   ├── Direction Badge (LONG/SHORT)
│   │   │   ├── Status Badge (TP_HIT/SL_HIT/EXPIRED)
│   │   │   ├── PnL Color Coding (green/red)
│   │   │   └── EQS Color Coding (gradient)
│   │   │
│   │   └── Pagination Controls
│   │
│   └── Summary Row (above table)
│       ├── Filtered trade count
│       ├── Win rate of filtered set
│       └── Total PnL of filtered set
│
└── Trade Detail (Drill-down for single trade)
    ├── Trade Summary Card
    │   ├── Symbol & Direction
    │   ├── Entry Price & Timestamp
    │   ├── Exit Price & Timestamp
    │   ├── Size (USDT & Qty)
    │   ├── Realized PnL & PnL %
    │   ├── Status & Exit Reason
    │   └── Duration
    │
    ├── Execution Intelligence Card
    │   ├── MAE (value & timestamp)
    │   ├── MFE (value & timestamp)
    │   ├── Profit Capture Ratio
    │   ├── Execution Quality Score
    │   ├── Execution Classification
    │   ├── Stop Loss & Take Profit Levels
    │   └── Execution Policy Details
    │       ├── Policy Type
    │       ├── Trailing Stop Activated?
    │       ├── Break Even Triggered?
    │       └── SL Move Count
    │
    ├── Signal Attribution Card
    │   ├── Confidence
    │   ├── Market Regime
    │   ├── Timeframe
    │   ├── Signal Direction
    │   ├── Signal Timestamp
    │   ├── Probabilities (Short/Neutral/Long)
    │   └── Execution Edge
    │
    └── Navigation
        ├── Back to List (preserves filters)
        ├── Previous Trade
        └── Next Trade
```

**Hierarchy Rationale:**

- **Summary First:** Users start with aggregate view to understand overall performance before drilling into individual trades
- **Filters Persistent:** Applied filters affect both summary analytics and trade list
- **List as Hub:** Trade list is central navigation point, not a gateway to detail
- **Detail as Deep Dive:** Trade detail exposes all available data for forensic analysis

---

## 5. Navigation Structure

### Primary Navigation

```
Dashboard Header
├── Dashboard (existing)
├── Trading (existing)
└── Trade Explorer ← NEW TAB
```

**Entry Point:** Trade Explorer link in main navigation header (same level as Dashboard and Trading)

**Active State:** Highlight "Trade Explorer" tab when on `/explorer` or `/explorer/:id` routes

---

### Trade Explorer Internal Navigation

#### Route Structure

```
/explorer              → Trade List with Filters
/explorer?symbol=...   → Trade List with Applied Filters (URL state)
/explorer/:id          → Trade Detail
```

**URL State Management:**
- All filters encoded in URL query parameters
- Enables shareable filtered views
- Browser back/forward preserves filter state
- Example: `/explorer?symbol=BTCUSDT&confidence_min=70&regime=bullish_trending`

---

### Navigation Flows

#### Flow 1: Summary → List → Detail

```
User lands on /explorer
    ↓
Views summary analytics at top of page
    ↓
Scrolls to trade list below
    ↓
Clicks trade row
    ↓
Navigates to /explorer/:id
    ↓
Clicks "Back to List" button
    ↓
Returns to /explorer with filters intact
```

#### Flow 2: Filter → Analyze → Drill

```
User applies filters (symbol, regime, confidence)
    ↓
URL updates: /explorer?symbol=BTCUSDT&regime=bullish_trending
    ↓
Summary analytics re-compute for filtered set
    ↓
Trade list re-renders with filtered trades
    ↓
User clicks high-EQS trade to investigate
    ↓
Trade detail shows execution intelligence
    ↓
User clicks "Next Trade" to compare adjacent trade
```

#### Flow 3: Direct Access via URL

```
User bookmarks: /explorer?status=TP_HIT&confidence_min=80
    ↓
Returns later, clicks bookmark
    ↓
Lands directly on filtered view
    ↓
Immediately sees high-confidence winning trades
```

---

### Trade Detail Navigation

**Within Detail Page:**

```
┌─────────────────────────────────────┐
│  ← Back to List    [◄ Prev]  [Next ►] │
│                                     │
│  Trade #42 Details                  │
└─────────────────────────────────────┘
```

**Controls:**
- **Back to List:** Returns to `/explorer` with all filters preserved
- **Previous Trade:** Navigates to `/explorer/:id-1` (previous trade in filtered list)
- **Next Trade:** Navigates to `/explorer/:id+1` (next trade in filtered list)

**Keyboard Shortcuts (Nice-to-Have):**
- `Esc` → Back to list
- `←` → Previous trade
- `→` → Next trade
- `Enter` (on trade row) → Open detail

---

### Filter Interaction Model

**Filter Panel Behavior:**
- Filters apply on user input (debounced for text inputs)
- Multi-select filters use "OR" logic within category (e.g., status = TP_HIT OR SL_HIT)
- Cross-category filters use "AND" logic (e.g., symbol = BTCUSDT AND status = TP_HIT)
- "Clear All Filters" button resets to default state
- Active filter count badge shows number of applied filters

**Filter Persistence:**
- Filters stored in URL query parameters
- Preserved across page refresh
- Preserved when navigating to detail and back
- Not persisted in localStorage (user may want different views in different tabs)

---

### No-Results State

**When Filters Return Zero Trades:**

```
┌─────────────────────────────────────┐
│  No trades match your filters.      │
│                                     │
│  Try:                               │
│  • Expanding date range             │
│  • Removing confidence constraints  │
│  • Selecting more regimes           │
│                                     │
│  [Clear All Filters]                │
└─────────────────────────────────────┘
```

**When Database is Empty:**

```
┌─────────────────────────────────────┐
│  No closed trades yet.              │
│                                     │
│  Close some paper positions first.  │
│  Go to Trading → Execute signals    │
└─────────────────────────────────────┘
```

---

### Error States

**Failed to Load Trades:**
- Display error message at top of page
- Preserve filter state
- Show "Retry" button
- Log error to console for debugging

**Failed to Load Trade Detail:**
- Display error message in place of detail cards
- Show "Back to List" button
- Do not show "Previous/Next" navigation (invalid state)

**Invalid Trade ID:**
- Return 404 page
- Show "Trade Not Found" message
- Show "Back to List" button

---

## 6. Desktop Layout

**Route:** `/explorer`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Trade Dashboard                                                            │
│  ───────────────────────────────────────────────────────────────────────    │
│  Dashboard  │  Trading  │  Trade Explorer ◄─ ACTIVE                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Trade Explorer                                                  [Refresh]  │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │  Win Rate  │  │ Profit Fctr│  │  Total PnL │  │   Avg EQS  │          │
│  │   62.5%    │  │    1.84    │  │  +$1,247   │  │     74     │          │
│  │  (25/40)   │  │            │  │            │  │            │          │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘          │
│                                                                             │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  FILTERS                                        [Clear All] (3 active)│  │
│  │  ─────────────────────────────────────────────────────────────────── │  │
│  │                                                                       │  │
│  │  Symbol: [BTCUSDT ▼]    Status: [TP_HIT][SL_HIT][ EXPIRED ]        │  │
│  │                                                                       │  │
│  │  Direction: ( ) All  (●) LONG  ( ) SHORT                           │  │
│  │                                                                       │  │
│  │  Confidence: [────●────────────] 70-100                            │  │
│  │                                                                       │  │
│  │  Date Range: [2026-06-01] to [2026-07-06]                          │  │
│  │                                                                       │  │
│  │  Regime: [✓] bullish_trending  [✓] bearish_trending  [ ] sideways  │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Showing 15 trades  │  Win Rate: 73.3% (11/15)  │  Total PnL: +$842       │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Symbol  Dir  Entry     Exit      PnL      Conf  EQS  Status  Closed │  │
│  │──────────────────────────────────────────────────────────────────────│  │
│  │ BTCUSDT LONG 65000.0   67000.0   +$3.08   72    78   TP_HIT  Jul 2  │  │
│  │ ETHUSDT LONG 3200.0    3350.0    +$4.69   85    82   TP_HIT  Jul 1  │  │
│  │ BTCUSDT SHORT 66500.0  65800.0   +$1.05   68    71   TP_HIT  Jul 1  │  │
│  │ SOLUSDT LONG 145.0     142.5     -$1.72   75    45   SL_HIT  Jun 30 │  │
│  │ BTCUSDT LONG 64200.0   65100.0   +$1.40   79    76   TP_HIT  Jun 29 │  │
│  │ ...                                                                   │  │
│  │                                                                       │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  [◄ Prev]  Page 1 of 3  [Next ►]                          50 per page ▼   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Layout Zones:**
- **Header:** Global navigation (reused from existing dashboard)
- **Summary Cards:** 4 KPI cards (fixed height, responsive width)
- **Filter Panel:** Collapsible filter form (default: expanded)
- **Filtered Summary:** One-line aggregate of current filtered set
- **Trade List Table:** Scrollable table with sortable columns
- **Pagination:** Footer controls for page navigation

**Responsive Behavior (Desktop Only):**
- Min width: 1280px
- Summary cards: 4 columns on wide, 2 columns on narrow desktop
- Filter panel: full width, wraps inputs as needed
- Table: horizontal scroll if columns exceed viewport

---

## 7. Trade List Layout

**Component:** `TradeListTable.tsx`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Symbol   Dir   Entry      Exit       PnL       PnL%   Dur   Conf  EQS Status│
│  ▲ ▼                                   ▲ ▼                   ▲ ▼             │
│──────────────────────────────────────────────────────────────────────────────│
│ BTCUSDT  LONG  65000.0    67000.0    +$3.08   +3.08%  29h   72    78  TP_HIT│
│ ETHUSDT  LONG  3200.0     3350.0     +$4.69   +4.69%  14h   85    82  TP_HIT│
│ BTCUSDT  SHORT 66500.0    65800.0    +$1.05   +1.05%   8h   68    71  TP_HIT│
│ SOLUSDT  LONG  145.0      142.5      -$1.72   -1.19%  12h   75    45  SL_HIT│
│ BTCUSDT  LONG  64200.0    65100.0    +$1.40   +1.40%  18h   79    76  TP_HIT│
│ ETHUSDT  SHORT 3400.0     3420.0     -$0.59   -0.59%   6h   62    38  SL_HIT│
│ BTCUSDT  LONG  63800.0    64500.0    +$1.10   +1.10%  22h   81    79  TP_HIT│
│ SOLUSDT  LONG  148.0      151.0      +$2.03   +2.03%  16h   77    80  TP_HIT│
│ BTCUSDT  SHORT 67000.0    66200.0    +$1.19   +1.19%  10h   70    74  TP_HIT│
│ ETHUSDT  LONG  3150.0     3280.0     +$4.13   +4.13%  20h   88    85  TP_HIT│
│──────────────────────────────────────────────────────────────────────────────│
│ [◄ Prev]  Page 1 of 3 (showing 1-10 of 28 trades)  [Next ►]    50/page ▼  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Column Specifications:**

| Column | Width | Sort | Format | Color |
|--------|-------|------|--------|-------|
| Symbol | 80px | Yes | Text | Default |
| Dir | 60px | Yes | Badge (LONG/SHORT) | Blue/Red |
| Entry | 90px | Yes | Price (2 decimals) | Default |
| Exit | 90px | Yes | Price (2 decimals) | Default |
| PnL | 90px | Yes | Currency ($X.XX) | Green (+) / Red (-) |
| PnL% | 80px | Yes | Percentage (X.XX%) | Green (+) / Red (-) |
| Dur | 60px | Yes | Hours (Xh) | Default |
| Conf | 60px | Yes | Integer (0-100) | Default |
| EQS | 60px | Yes | Integer (0-100) | Gradient (red→yellow→green) |
| Status | 80px | Yes | Badge | Green (TP) / Red (SL) / Gray (EXP) |

**Row Behavior:**
- Hover: Highlight row with subtle background color
- Click: Navigate to `/explorer/:id`
- Cursor: Pointer (entire row is clickable)

**Sort Indicators:**
- Default sort: `closed_at DESC` (most recent first)
- Active column shows arrow: ▲ (asc) or ▼ (desc)
- Click column header to toggle sort
- Only one column sortable at a time

**Empty State:**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                            No trades match filters                           │
│                                                                              │
│                        Try adjusting your filter criteria                    │
│                                                                              │
│                              [Clear All Filters]                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Loading State:**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Symbol   Dir   Entry      Exit       PnL       PnL%   Dur   Conf  EQS Status│
│──────────────────────────────────────────────────────────────────────────────│
│ ████████ ████  ████████   ████████   ████████  ████  ████  ████ ████ ██████ │
│ ████████ ████  ████████   ████████   ████████  ████  ████  ████ ████ ██████ │
│ ████████ ████  ████████   ████████   ████████  ████  ████  ████ ████ ██████ │
│ ████████ ████  ████████   ████████   ████████  ████  ████  ████ ████ ██████ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Trade Detail Layout

**Route:** `/explorer/:id`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back to List                                    [◄ Prev Trade] [Next ►]  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Trade #42 - BTCUSDT LONG                                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────┐  ┌──────────────────────────────────────┐
│  TRADE SUMMARY                 │  │  EXECUTION INTELLIGENCE              │
│  ────────────────────────────  │  │  ──────────────────────────────────  │
│                                │  │                                      │
│  Symbol:        BTCUSDT        │  │  Execution Quality Score             │
│  Direction:     LONG           │  │  ┌────────────────────────────────┐ │
│                                │  │  │          78 / 100              │ │
│  Entry Price:   $65,000.00     │  │  │  ████████████████░░░░░░░░░░   │ │
│  Entry Time:    Jul 1, 08:30   │  │  └────────────────────────────────┘ │
│                                │  │                                      │
│  Exit Price:    $67,000.00     │  │  Classification:                     │
│  Exit Time:     Jul 2, 14:15   │  │  MODEL_CORRECT_EXECUTION_CORRECT     │
│                                │  │                                      │
│  Size (USDT):   $100.00        │  │  Maximum Adverse Excursion (MAE)     │
│  Quantity:      0.001538 BTC   │  │  -1.2%  (at Jul 1, 16:45)            │
│                                │  │                                      │
│  Realized PnL:  +$3.08         │  │  Maximum Favorable Excursion (MFE)   │
│  PnL %:         +3.08%         │  │  +4.5%  (at Jul 2, 12:30)            │
│                                │  │                                      │
│  Status:        TP_HIT         │  │  Profit Capture Ratio                │
│  Exit Reason:   TP_HIT         │  │  68%  (captured 68% of MFE)          │
│  Duration:      29.75 hours    │  │                                      │
│                                │  │  ──────────────────────────────────  │
└────────────────────────────────┘  │                                      │
                                    │  Stop Loss:      $63,700.00 (-2.0%)  │
┌────────────────────────────────┐  │  Take Profit:    $67,000.00 (+3.1%)  │
│  SIGNAL ATTRIBUTION            │  │                                      │
│  ────────────────────────────  │  │  Execution Policy:    FIXED_SL       │
│                                │  │  Trailing Activated:  No             │
│  Confidence:      72 / 100     │  │  Break Even Trigger:  No             │
│  Market Regime:   bullish_trend│  │  SL Move Count:       0              │
│  Timeframe:       1h           │  │                                      │
│                                │  └──────────────────────────────────────┘
│  Signal Direction:  LONG       │
│  Signal Time:  Jul 1, 08:15    │
│                                │
│  Probabilities                 │
│  • Short:     15%              │
│  • Neutral:   13%              │
│  • Long:      72%              │
│                                │
│  Execution Edge:  +0.042       │
│                                │
└────────────────────────────────┘
```

**Layout Structure:**

**Top Bar:**
- Back button (left)
- Navigation controls (right: Previous/Next)
- Fixed position when scrolling

**Page Header:**
- Trade ID + Symbol + Direction
- Large, prominent

**Three-Column Grid:**
- Left Column (30%): Trade Summary Card
- Right Column (70%): Execution Intelligence Card (top) + Signal Attribution Card (bottom-left)

**Card Styling:**
- White background with subtle border
- Padding: 20px
- Border radius: 8px
- Gap between cards: 16px

**Responsive Stacking:**
- On narrow desktop (< 1400px): Stack cards vertically
- Order: Trade Summary → Execution Intelligence → Signal Attribution

---

## 9. Summary Cards

**Component:** `TradeAnalyticsSummary.tsx`

Four KPI cards displayed horizontally at the top of Trade Explorer page. Each card updates dynamically based on applied filters.

### Card 1: Win Rate

```
┌────────────────────────┐
│  Win Rate              │
│  ────────────────────  │
│                        │
│      62.5%             │
│                        │
│   25 wins / 40 trades  │
│                        │
└────────────────────────┘
```

**Data:**
- Primary: Win rate percentage (0-100%)
- Secondary: Win count / Total count
- Calculation: `(count where realized_pnl > 0) / (total count)`

**Color:**
- >= 60%: Green
- 40-59%: Yellow
- < 40%: Red

---

### Card 2: Profit Factor

```
┌────────────────────────┐
│  Profit Factor         │
│  ────────────────────  │
│                        │
│       1.84             │
│                        │
│   $1,450 / $788        │
│                        │
└────────────────────────┘
```

**Data:**
- Primary: Profit factor (2 decimals)
- Secondary: Total wins / Total losses
- Calculation: `sum(realized_pnl where pnl > 0) / abs(sum(realized_pnl where pnl < 0))`

**Color:**
- >= 2.0: Green
- 1.5-1.99: Yellow
- < 1.5: Red

**Edge Case:**
- If no losing trades: Display "N/A" (cannot divide by zero)

---

### Card 3: Total PnL

```
┌────────────────────────┐
│  Total PnL             │
│  ────────────────────  │
│                        │
│     +$1,247            │
│                        │
│   +$1,450 / -$203      │
│                        │
└────────────────────────┘
```

**Data:**
- Primary: Net realized PnL (currency format)
- Secondary: Gross wins / Gross losses
- Calculation: `sum(realized_pnl)`

**Color:**
- Positive: Green with + sign
- Negative: Red with - sign
- Zero: Gray

---

### Card 4: Average EQS

```
┌────────────────────────┐
│  Avg EQS               │
│  ────────────────────  │
│                        │
│       74               │
│                        │
│   Range: 38 - 92       │
│                        │
└────────────────────────┘
```

**Data:**
- Primary: Average Execution Quality Score (integer)
- Secondary: Min - Max range
- Calculation: `avg(eqs)` across filtered trades

**Color:**
- >= 70: Green
- 50-69: Yellow
- < 50: Red

---

### Additional Summary Row (Below Filters)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Showing 15 trades  │  Win Rate: 73.3% (11/15)  │  Total PnL: +$842     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Purpose:** Quick filtered summary above table

**Data:**
- Trade count
- Win rate (recalculated for filtered set)
- Total PnL (recalculated for filtered set)

**Behavior:**
- Updates immediately when filters change
- Shown only when filters are active (not on default view)

---

## 10. Filter Panel

**Component:** `TradeFilterPanel.tsx`

Horizontal filter bar with multiple input types. All filters apply immediately (debounced for text inputs).

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FILTERS                                        [Clear All] (3 active)   │
│  ──────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  Symbol: [BTCUSDT ▼]    Status: [TP_HIT][SL_HIT][ EXPIRED ]            │
│                                                                          │
│  Direction: ( ) All  (●) LONG  ( ) SHORT                               │
│                                                                          │
│  Confidence: [────●────────────] 70-100                                │
│                                                                          │
│  Date Range: [2026-06-01] to [2026-07-06]                              │
│                                                                          │
│  Regime: [✓] bullish_trending  [✓] bearish_trending  [ ] sideways      │
│                                                                          │
│  Execution Policy: [ ] FIXED_SL  [ ] BREAK_EVEN  [ ] TRAILING          │
│                                                                          │
│  PnL Range: Min [$______] Max [$______]    EQS: [──────●──────] 0-100  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Filter Specifications

#### 1. Symbol Filter

**Type:** Single-select dropdown  
**Options:** Dynamically loaded from `/api/explorer/filters`  
**Default:** All symbols  
**Example:** BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT

**Behavior:**
- Dropdown shows all symbols that have closed trades
- Search/filter input for quick symbol lookup
- Placeholder: "All Symbols"

---

#### 2. Status Filter

**Type:** Multi-select toggle buttons  
**Options:** TP_HIT | SL_HIT | EXPIRED | MANUAL_CLOSE  
**Default:** All statuses selected  
**Logic:** OR within status (any selected status matches)

**UI:**
- Toggle buttons with checkmark when active
- Green: TP_HIT
- Red: SL_HIT
- Gray: EXPIRED, MANUAL_CLOSE

---

#### 3. Direction Filter

**Type:** Radio buttons  
**Options:** All | LONG | SHORT  
**Default:** All  
**Logic:** Exact match (exclusive)

**UI:**
- Horizontal radio group
- All: No filtering by direction
- LONG: Blue badge
- SHORT: Red badge

---

#### 4. Date Range Filter

**Type:** Date pickers (from/to)  
**Default:** Last 30 days  
**Logic:** `closed_at >= date_from AND closed_at <= date_to`

**UI:**
- Two date inputs: "From" and "To"
- Calendar popup for date selection
- Preset buttons: "Last 7 days", "Last 30 days", "All time"

**Validation:**
- `date_from` cannot be after `date_to`
- Show error if invalid range

---

#### 5. Confidence Filter

**Type:** Range slider  
**Range:** 0-100  
**Default:** 0-100 (no filter)  
**Step:** 1  
**Logic:** `confidence >= min AND confidence <= max`

**UI:**
- Dual-thumb slider
- Display current range below: "70-100"
- Slider color gradient: red (0) → yellow (50) → green (100)

---

#### 6. Regime Filter

**Type:** Multi-select checkboxes  
**Options:** Dynamically loaded from `/api/explorer/filters`  
**Default:** All regimes selected  
**Logic:** OR within regime (any selected regime matches)

**Example Options:**
- bullish_trending
- bearish_trending
- sideways_choppy
- high_volatility
- low_volatility

**UI:**
- Checkbox list (horizontal or wrapped)
- Show only regimes present in data

---

#### 7. Execution Policy Filter

**Type:** Multi-select checkboxes  
**Options:** OFF | FIXED_SL | BREAK_EVEN | TRAILING  
**Default:** All policies selected  
**Logic:** OR within policy

**UI:**
- Checkbox list
- Labels: "Fixed SL", "Break Even", "Trailing"

---

#### 8. PnL Range Filter

**Type:** Numeric inputs (min/max)  
**Range:** Any currency value  
**Default:** No limits  
**Logic:** `realized_pnl >= min AND realized_pnl <= max`

**UI:**
- Two text inputs: "Min $" and "Max $"
- Currency formatting on blur
- Allow negative values for losses

---

#### 9. EQS Range Filter

**Type:** Range slider  
**Range:** 0-100  
**Default:** 0-100 (no filter)  
**Step:** 1  
**Logic:** `eqs >= min AND eqs <= max`

**UI:**
- Dual-thumb slider
- Display current range below: "50-100"
- Color gradient: red (0) → yellow (50) → green (100)

---

### Filter Panel Behavior

**Immediate Application:**
- Filters apply on change (no "Apply" button)
- Text inputs debounced (500ms)
- Sliders apply on mouse release

**Clear All:**
- Resets all filters to default state
- Updates URL to `/explorer` (no query params)
- Badge shows active filter count

**Active Filter Badge:**
- Shows count of non-default filters
- Example: "(3 active)" when 3 filters applied
- Hidden when no filters active

**URL State:**
- All filters encoded in URL query params
- Example: `/explorer?symbol=BTCUSDT&confidence_min=70&status=TP_HIT`
- Enables shareable filtered views

**Collapsible (Nice-to-Have):**
- Show/hide button to collapse filter panel
- Saves vertical space after filters set
- Preserves filter state when collapsed

---

## 17. Responsive Behaviour

### Desktop First (Primary Target)

**Minimum Supported Resolution:** 1280×720  
**Optimal Resolution:** 1920×1080 and above

**Desktop Layout (≥ 1280px):**
- Summary cards: 4 columns, fixed height
- Filter panel: full width, horizontal layout
- Trade list: full table with all columns visible
- Trade detail: 3-column card grid (summary left, intelligence + attribution right)
- Navigation: horizontal header with all tabs visible

**Design Assumptions:**
- Users work on research workstations (desktop/laptop)
- Multi-monitor setups common (can dedicate one screen to Trade Explorer)
- No touch interactions (mouse + keyboard only)

---

### Tablet Support (768px - 1279px)

**Layout Adjustments:**

**Summary Cards:**
- 2 columns × 2 rows
- Maintain card order: Win Rate, Profit Factor, Total PnL, Avg EQS

**Filter Panel:**
- Stack vertically within sections
- Symbol + Status + Direction (row 1)
- Confidence slider (row 2)
- Date range (row 3)
- Regime + Execution Policy (row 4)
- PnL Range + EQS slider (row 5)

**Trade List:**
- Hide less critical columns: Duration, Timeframe
- Remaining columns: Symbol, Dir, Entry, Exit, PnL, PnL%, Conf, EQS, Status
- Horizontal scroll enabled if needed

**Trade Detail:**
- Stack cards vertically
- Order: Trade Summary → Execution Intelligence → Signal Attribution
- Full width cards

**Pagination:**
- Reduce default page size to 25 items
- Smaller pagination controls

---

### Mobile Support (< 768px)

**Status:** NOT SUPPORTED IN MVP

**Rationale:**
- Trade Explorer is research-focused tool for desktop workstations
- Complex tabular data and dense information hierarchy unsuitable for mobile
- Multi-dimensional filtering requires desktop interaction paradigm
- Limited use case for mobile trading research

**Post-MVP Considerations:**
- Mobile view could show simplified summary cards only
- Trade detail view could be mobile-optimized (single column)
- Trade list requires fundamental redesign for mobile (card-based instead of table)

**Minimum Mobile Experience (If Implemented):**
- Show "Best viewed on desktop" banner
- Display summary cards (1 column, 4 rows)
- Provide link to single trade detail view (no list view)
- Disable complex filters (show symbol + date only)

---

## 18. Accessibility

### Keyboard Navigation

**Global Navigation:**
- `Tab` / `Shift+Tab`: Navigate through interactive elements
- `Enter` / `Space`: Activate buttons, checkboxes, dropdowns
- `Escape`: Close modals, dropdowns, date pickers

**Trade List:**
- `↑` / `↓`: Navigate between table rows
- `Enter`: Open trade detail for focused row
- `Home` / `End`: Jump to first/last row
- `Page Up` / `Page Down`: Scroll one page

**Trade Detail:**
- `Escape`: Return to trade list
- `←`: Previous trade
- `→`: Next trade
- `Tab`: Navigate through detail cards

**Filter Panel:**
- `Tab`: Move between filter inputs
- `Space`: Toggle checkboxes and radio buttons
- `←` / `→`: Adjust range sliders
- `Enter`: Apply date picker selection

**Sort Columns:**
- `Tab` to column header
- `Enter` or `Space` to sort
- Screen reader announces sort direction

---

### ARIA Labels and Roles

**Semantic HTML:**
```html
<main role="main" aria-label="Trade Explorer">
  <section aria-label="Summary Cards">
    <div role="group" aria-label="Win Rate: 62.5%">...</div>
  </section>
  
  <section aria-label="Filters">
    <form role="search" aria-label="Trade Filters">...</form>
  </section>
  
  <section aria-label="Trade List">
    <table role="table" aria-label="Closed Trades">
      <thead role="rowgroup">...</thead>
      <tbody role="rowgroup">...</tbody>
    </table>
  </section>
</main>
```

**Interactive Elements:**
```html
<button aria-label="Sort by PnL descending">PnL ▼</button>
<input type="range" aria-label="Confidence range" aria-valuemin="0" aria-valuemax="100" aria-valuenow="70" />
<div role="status" aria-live="polite">Showing 15 trades, Win Rate: 73.3%</div>
```

**Dynamic Content:**
- Use `aria-live="polite"` for filter result updates
- Use `aria-busy="true"` during loading states
- Use `aria-disabled="true"` for unavailable navigation (no next trade)

**Links:**
- Trade rows: `aria-label="View trade #42 details: BTCUSDT LONG, +$3.08"`
- Pagination: `aria-label="Go to page 2"`
- Navigation: `aria-label="Previous trade"`, `aria-label="Next trade"`

---

### Contrast and Visual Design

**WCAG 2.1 Level AA Compliance:**
- Minimum contrast ratio: 4.5:1 for normal text
- Minimum contrast ratio: 3:1 for large text (≥18pt or ≥14pt bold)
- Interactive elements: 3:1 contrast against background

**Color Palette:**

| Element | Foreground | Background | Contrast |
|---------|-----------|------------|----------|
| Body text | #1a1a1a | #ffffff | 15.3:1 ✓ |
| Positive PnL | #059669 (green-600) | #ffffff | 4.5:1 ✓ |
| Negative PnL | #dc2626 (red-600) | #ffffff | 5.1:1 ✓ |
| LONG badge | #2563eb (blue-600) | #dbeafe (blue-50) | 7.2:1 ✓ |
| SHORT badge | #dc2626 (red-600) | #fee2e2 (red-50) | 6.8:1 ✓ |
| EQS low (0-50) | #dc2626 (red-600) | #ffffff | 5.1:1 ✓ |
| EQS high (70-100) | #059669 (green-600) | #ffffff | 4.5:1 ✓ |

**Not Color-Dependent:**
- Trade status indicated by both color AND text badge
- PnL shown with color AND +/- sign
- Direction shown with color badge AND text (LONG/SHORT)
- EQS uses color gradient but always shows numeric value

---

### Focus Management

**Focus Indicators:**
- Visible focus ring on all interactive elements
- Focus ring: 2px solid #2563eb (blue-600), 2px offset
- Focus ring visible in all states (keyboard navigation, click)

**Focus Behavior:**
- Page load: Focus on first interactive element (Symbol filter)
- Trade list click: Focus moves to trade detail header
- Trade detail "Back" button: Focus returns to clicked row
- Modal open: Focus trapped within modal
- Modal close: Focus returns to trigger element

**Skip Links:**
```html
<a href="#main-content" class="sr-only focus:not-sr-only">
  Skip to main content
</a>
```

**Focus Order:**
1. Global navigation (Dashboard, Trading, Trade Explorer)
2. Summary cards (tab through each)
3. Filter panel (tab through all inputs)
4. Clear filters button
5. Trade list table
6. Pagination controls

**No Focus Traps:**
- Ensure `Tab` can exit all components
- Dropdowns/modals use `Escape` to close
- No circular tab loops without user control

---

## 19. Future Enhancements

**STATUS: POST-MVP**

These features are out of scope for MVP but documented for future phases.

---

### Charts and Visualizations

**POST-MVP: Phase 2**

**MAE/MFE Distribution Histogram:**
- X-axis: MAE or MFE percentage
- Y-axis: Trade count
- Overlay winning vs losing trades (green vs red bars)
- Identify common failure zones (MAE concentration points)

**Equity Curve:**
- X-axis: Trade sequence (chronological)
- Y-axis: Cumulative PnL
- Individual trade impact visualization
- Filter by regime/confidence to see segmented curves

**PnL Distribution:**
- Histogram of realized PnL
- Identify outlier trades (fat tails)
- Compare distributions across regimes

**Win Rate by Confidence Tier:**
- Bar chart: Confidence buckets (0-20, 20-40, 40-60, 60-80, 80-100)
- Y-axis: Win rate percentage
- Validate confidence calibration

**Technology:**
- Use existing Recharts library (already in project)
- Add chart components to trade detail page
- Add chart toggle buttons to filter panel

---

### Heatmaps

**POST-MVP: Phase 2**

**Regime × Confidence Heatmap:**
- X-axis: Confidence tiers
- Y-axis: Market regimes
- Cell color: Win rate or average PnL
- Identify optimal regime-confidence combinations

**Time-of-Day Heatmap:**
- X-axis: Hour of day (0-23)
- Y-axis: Day of week (Mon-Sun)
- Cell color: Trade count or win rate
- Identify temporal patterns in signal generation

**Symbol × Execution Policy Heatmap:**
- X-axis: Symbols
- Y-axis: Execution policies
- Cell color: Average EQS
- Identify which policies work best per symbol

---

### Trade Replay

**POST-MVP: Phase 3**

**Concept:** Visualize trade lifecycle as animated timeline

**Features:**
- Timeline slider: Entry → MAE/MFE timestamps → Exit
- Price chart with entry/exit/SL/TP levels marked
- Annotate lifecycle events (SL move, trailing activation)
- Playback controls: Play, pause, speed adjust

**Use Case:**
- Understand why trades closed early (SL hit near MFE)
- Validate MAE/MFE tracking accuracy
- Debug execution policy behavior

**Technical Requirements:**
- Integrate price history data (not in MVP database)
- Fetch 1-minute OHLCV data for trade duration
- Use lightweight charting library (TradingView, Lightweight Charts)

---

### Explainability Integration

**POST-MVP: Phase 4**

**Concept:** Link trades back to ML model explanations

**Features:**
- Show SHAP values for signal features at entry time
- Highlight which features contributed most to confidence score
- Compare feature importance across winning vs losing trades
- Identify when model was overconfident (high confidence, low win rate)

**Technical Requirements:**
- Store SHAP values in `signals.features_json` (schema extension)
- Add explainability card to trade detail page
- Visualize top 10 feature contributions as bar chart

**Use Case:**
- Understand why high-confidence signals failed
- Identify feature drift (features losing predictive power)
- Guide feature engineering for model iteration

---

### Export and Reporting

**POST-MVP: Phase 2**

**CSV Export:**
- Export filtered trade list to CSV
- Include all columns (basic + execution intelligence + attribution)
- Preserve sort order and filters applied

**PDF Trade Report:**
- Generate formatted report for single trade
- Include all detail cards + charts
- Use case: Share trade post-mortem with team

**Scheduled Reports:**
- Weekly email with summary analytics
- Breakdown by regime, confidence, policy
- Use case: Regular performance review

---

### Comparison Mode

**POST-MVP: Phase 3**

**Side-by-Side Trade Comparison:**
- Select 2-4 trades from list
- Display detail cards side-by-side
- Highlight differences in execution intelligence
- Use case: Compare similar setups with different outcomes

**Policy Comparison:**
- Compare aggregate analytics across execution policies
- Show win rate, profit factor, avg EQS per policy
- Identify which policies perform best by regime/symbol

**Regime Comparison:**
- Compare performance across market regimes
- Show confidence calibration per regime
- Identify which regimes have best signal quality

---

### Real-Time Updates

**POST-MVP: Phase 4**

**WebSocket Integration:**
- Subscribe to paper position close events
- Auto-refresh trade list when new trades close
- Show notification toast: "New trade closed: BTCUSDT +$3.08"

**Live Analytics:**
- Update summary cards in real-time
- Show "live" badge when connected
- Use case: Monitor paper trading during live market hours

**Technical Requirements:**
- Add WebSocket endpoint to FastAPI
- Emit events when `paper_positions.status` changes to closed
- Use React Query subscription pattern

---

## 20. Final UI Review Checklist

### Architecture Alignment

- [ ] **Read-Only Design:** All UI components use GET requests only, no mutations
- [ ] **REST API Integration:** Frontend consumes `/api/explorer/*` endpoints
- [ ] **Component Hierarchy:** Follows architecture: Summary → Filters → List → Detail
- [ ] **React Query:** All data fetching uses React Query for caching and state management
- [ ] **Error Boundaries:** Each major component has error handling UI
- [ ] **Loading States:** All async operations show skeleton loaders

---

### API Contract

- [ ] **Endpoint Coverage:** UI supports all endpoints defined in `TradeExplorer_API.md`
  - [ ] `GET /api/explorer/trades` (list with filters, sorting, pagination)
  - [ ] `GET /api/explorer/trades/:id` (single trade detail)
  - [ ] `GET /api/explorer/analytics` (aggregate KPIs)
  - [ ] `GET /api/explorer/filters` (available filter options)
- [ ] **Filter Parameters:** All filters documented in Section 10 map to API query params
- [ ] **Response Schemas:** Frontend types match API response schemas exactly
- [ ] **Pagination:** UI respects `page`, `page_size`, `total_count` from API
- [ ] **Sort Fields:** UI only allows sorting on fields specified in API docs

---

### Database Schema

- [ ] **Data Fields:** All displayed fields exist in `paper_positions` or `signals` tables
- [ ] **Derived Metrics:** UI correctly interprets EQS, execution_classification, duration_hours
- [ ] **JOIN Logic:** Trade detail shows signal attribution via `signal_id` foreign key
- [ ] **Status Filtering:** UI status filters match database ENUM values
- [ ] **No Schema Changes:** UI works with existing database schema (no migrations required)

---

### Repository Integration

- [ ] **Routing:** Trade Explorer accessible via `/explorer` route in Next.js app router
- [ ] **Navigation:** Header navigation includes "Trade Explorer" tab
- [ ] **Component Structure:** Follows existing project structure (`app/explorer/`, `components/explorer/`)
- [ ] **Styling:** Uses existing Tailwind CSS + shadcn/ui components
- [ ] **Testing:** Unit tests for components, integration tests for API calls

---

### Analytics Layer

- [ ] **Summary Cards:** Display win rate, profit factor, total PnL, avg EQS
- [ ] **Filtered Analytics:** Summary updates dynamically based on applied filters
- [ ] **Execution Classification:** Shows model/execution quadrant analysis
- [ ] **Execution Intelligence:** Displays MAE, MFE, PCR, EQS per trade
- [ ] **Signal Attribution:** Shows confidence, regime, probabilities per trade
- [ ] **Policy Tracking:** Filters and displays execution policy per trade

---

### Read-Only Guarantee

- [ ] **No Mutations:** Zero POST, PUT, PATCH, DELETE requests
- [ ] **No Action Buttons:** No "Edit", "Delete", "Retry" buttons
- [ ] **Safe Navigation:** Cannot trigger trade execution from Trade Explorer
- [ ] **No State Changes:** Viewing trades does not modify paper trading state
- [ ] **Concurrent Safe:** Can be used during live trading without interference

---

### MVP Scope Verification

**IN SCOPE (MVP):**
- [ ] Trade list with filtering, sorting, pagination
- [ ] Trade detail with all execution intelligence and attribution
- [ ] Summary cards with aggregate KPIs
- [ ] Desktop-first responsive layout
- [ ] URL state management for shareable filters
- [ ] Keyboard navigation and accessibility

**OUT OF SCOPE (POST-MVP):**
- [ ] No charts or visualizations (MAE/MFE distributions deferred)
- [ ] No export functionality (CSV/PDF deferred)
- [ ] No comparison mode (side-by-side trades deferred)
- [ ] No real-time updates (WebSocket deferred)
- [ ] No trade replay (price history integration deferred)
- [ ] No explainability integration (SHAP values deferred)
- [ ] No mobile optimization (tablet minimum, mobile not supported)

---

### UI/UX Quality

- [ ] **Information Density:** All execution metrics visible without excessive scrolling
- [ ] **Fast Navigation:** < 3 clicks from list to detail and back
- [ ] **Persistent Filters:** Filters preserved in URL and across navigation
- [ ] **Loading Performance:** List loads in < 500ms, detail in < 200ms
- [ ] **Accessibility:** WCAG 2.1 Level AA compliant (keyboard nav, ARIA, contrast)
- [ ] **Empty States:** Clear messaging when no trades match filters
- [ ] **Error States:** User-friendly error messages with recovery actions

---

### Documentation Complete

- [ ] **Section 1-5:** Executive summary, design goals, personas, information architecture, navigation
- [ ] **Section 6-10:** Desktop layout, trade list, trade detail, summary cards, filter panel
- [ ] **Section 17:** Responsive behavior (desktop, tablet, mobile not supported)
- [ ] **Section 18:** Accessibility (keyboard, ARIA, contrast, focus)
- [ ] **Section 19:** Future enhancements (charts, heatmaps, replay, explainability)
- [ ] **Section 20:** Final checklist (this section)

---

## Document Status

**Document:** `TradeExplorer_UI.md`  
**Version:** 1.0  
**Status:** Complete  
**Date:** 2026-07-06  
**Next Steps:** Implementation (Sprint 3 execution)

---

**END OF DOCUMENT**
