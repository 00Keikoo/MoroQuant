# Dashboard Audit

Repository State
Branch
feat/execution-analytics
Commit
d9f4560
Graphify Revision
42
Generated At
2026-07-14
Audit Version
v2

Status
FAIL

Completion
20%

---

## Difference-001

Title
Main Workspace Layout Grid Mismatch

Severity
Critical

Evidence
`components/dashboard/Layout.tsx` vs `design/stitch/current/trading_dashboard/code.html` (lines 205-414)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Main workspace layout utilizes a 12-column grid (`grid grid-cols-12 gap-px bg-outline-variant overflow-y-auto`) instead of the current vertical flex template.

---

## Difference-002

Title
Equity Curve Panel Integration

Severity
Critical

Evidence
`components/dashboard/Layout.tsx` (lines 10-12) vs `design/stitch/current/trading_dashboard/code.html` (lines 207-226)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Equity Curve panel renders details from Stitch HTML including Net Liq metrics, dot grid canvas representation, and active interactive timeline toggle controls (7D, 30D).

---

## Difference-003

Title
Daily Performance Panel Absence

Severity
Critical

Evidence
`components/dashboard/Layout.tsx` vs `design/stitch/current/trading_dashboard/code.html` (lines 227-256)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Renders top right realized PnL panel (col-span-4) with secondary 2x2 grid containing Gross Exposure, Net Delta, VaR (95%), and Sharpe Ratio (1Y) stats.

---

## Difference-004

Title
Active Inventory / Open Positions Table Integration

Severity
Critical

Evidence
`components/dashboard/Layout.tsx` (lines 14-25) vs `design/stitch/current/trading_dashboard/code.html` (lines 257-316)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Renders responsive table displaying Symbol, Side, Size, Entry, Mark, and color-coded Unrealized PnL instead of a text placeholder.

---

## Difference-005

Title
Risk Exposure Matrix Panel Absence

Severity
Major

Evidence
`components/dashboard/Layout.tsx` vs `design/stitch/current/trading_dashboard/code.html` (lines 317-349)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Bottom left panel (col-span-4) detailing Delta Sensitivity, Gamma Skew bars, and Drawdown Recovery chart is integrated.

---

## Difference-006

Title
Live Signals Feed Panel Absence

Severity
Major

Evidence
`components/dashboard/Layout.tsx` vs `design/stitch/current/trading_dashboard/code.html` (lines 353-377)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Bottom middle panel includes the live signals feed styled in monospace font (`JetBrains Mono`) with status timestamp logging.

---

## Difference-007

Title
Model Health Grid Panel Absence

Severity
Major

Evidence
`components/dashboard/Layout.tsx` vs `design/stitch/current/trading_dashboard/code.html` (lines 378-411)

Affected Files
- components/dashboard/Layout.tsx

Acceptance Criteria
- Bottom right panel contains the 2x2 Model Health Grid with active status indicators and uptime stats.

---

## Difference-008

Title
Inspector Panel Content & Subcomponents Integration

Severity
Major

Evidence
`components/dashboard/PageShell.tsx` (lines 104-106) vs `design/stitch/current/trading_dashboard/code.html` (lines 416-486)

Affected Files
- components/dashboard/PageShell.tsx

Acceptance Criteria
- Right inspector sidebar is populated with Position Details, Order Execution forms, and candlestick mini visualizer graph.

---

## Difference-009

Title
User Profile Avatar Image Link

Severity
Minor

Evidence
`components/dashboard/PageShell.tsx` (line 78) vs `design/stitch/current/trading_dashboard/code.html` (line 190)

Affected Files
- components/dashboard/PageShell.tsx

Acceptance Criteria
- Profile avatar displays the grayscale technical operator profile photo asset from Stitch instead of a blank background box.

---

## Difference-010

Title
Telemetry Footer Positioning and Classes

Severity
Minor

Evidence
`components/dashboard/PageShell.tsx` (line 111) vs `design/stitch/current/trading_dashboard/code.html` (line 489)

Affected Files
- components/dashboard/PageShell.tsx

Acceptance Criteria
- Footer styling elements updated to use fixed screen anchoring (`fixed bottom-0 left-0 right-0 z-50`) matching specifications.

---

Implementation Backlog

Sprint 6R.1
- Difference-001
- Difference-002
- Difference-004

Sprint 6R.2
- Difference-003
- Difference-008

Sprint 6R.3
- Difference-005
- Difference-006
- Difference-007
- Difference-009
- Difference-010

---

Remaining Completion %
80%
