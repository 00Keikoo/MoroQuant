# MoroQuant Lab Visual UI Design Specification

**Sprint**: 4.9B  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Research Command Center & Chronicle Layout

### 1.1 ASCII Layout
```
+------------------------------------------------------------------------------------+
| Rail | Toolbar: [Search / Ctrl+K           ] [Settings]                            |
+------+-----------------------------------------------------------------------------+
| [🧪] | RESEARCH COMMAND CENTER                                 | [⚡] Active Tasks |
|      +---------------------------------------------------------+-------------------+
| [📊] | [ Active Run Grid (3 Cards Wide)                      ] | Chron:            |
|      | +------------------+ +------------------+ +-----------+ | [14:02] Promoted  |
| [🗂️] | | Run: run_2081    | | Run: run_2082    | | ...       | | v1.4.2 [Success]  |
|      | | status: TRAINING | | status: VALIDATE | |           | |                   |
| [🧬] | | F1: --  ECE: --  | | F1: 0.68  ECE: - | |           | | [13:50] Failed    |
|      | +------------------+ +------------------+ +-----------+ | run_2041 [Error]  |
| [🎯] |                                                         |                   |
|      | +-----------------------------------------------------+ | [13:42] New Run   |
| [📈] | | Central DAG Lineage Explorer                        | | run_2082 [Ingest] |
|      | |                                                     | |                   |
| [⏱️] | | [DS: v2.4] ──► [Feat: v1.0] ──► [Run: run_2082]     | | [13:10] Ingested |
|      | |                                                     | | ohlcv 1h BTCUSDT  |
| [🚀] | +-----------------------------------------------------+ |                   |
|      |                                                         |                   |
| [📦] | [ Research Queue: 4 Pending Items ]                     |                   |
+------+---------------------------------------------------------+-------------------+
```

### 1.2 Layout Specs
*   **Desktop Layout (1440px+)**: Left rail (48px), Center content (900px), Right Chronicle pane (492px).
*   **Laptop Layout (1024px)**: Left rail (48px), Center content (676px), Right Chronicle pane collapses to hover-sheet (right-aligned, toggled via `Alt+C`).
*   **Tablet Layout (768px)**: Left rail collapses to bottom action bar (48px height), central canvas takes 100% width.

---

## 2. Validation & Calibration Workspace Layout

### 2.1 ASCII Layout
```
+------------------------------------------------------------------------------------+
| Rail | Toolbar: [Compare / Run Selector    ] [TimeTravel ▬▬▬▬▬● ]                  |
+------+-----------------------------------------------------------------------------+
| [🧪] | VALIDATION CENTER                                        | [ⓘ] Inspector     |
|      +----------------------------------------------------------+-------------------+
| [📊] | [ Walk-Forward Folds (Fold 1-5 Grid) ]                   | Name: run_2082    |
|      |  Fold 1: |███████████████████████████| [F1: 0.65]        | Git: c3f802a      |
| [🗂️] |  Fold 2: |███████████████████████████| [F1: 0.68]        |                   |
|      |                                                          | Metrics:          |
| [🧬] | +----------------------------+ +-----------------------+ | - F1-Score: 0.682 |
|      | | Confusion Matrix Heatmap   | | Calibration Reliability| | - ECE: 0.024      |
| [🎯] | |           Long  Short  Neut| | 1.0 |           /   | | - Brier: 0.012    |
|      | |     Long [  52     4     1]| |     |          /    | |                   |
| [📈] | |    Short [   2    48     0]| |     |      .--'     | | Rejection:        |
|      | |     Neut [   0     1    64]| | 0.0 |____.'_________| | - Conf Gate: PASS |
| [⏱️] | +----------------------------+ +-----------------------+ | - Edge Gate: PASS |
+------+----------------------------------------------------------+-------------------+
```

### 2.2 Component Hierarchy & Colors
*   **Fold Grid**: Unselected folds use Navy outline (`#1F2937`), selected fold active outline is Tech Orange (`#FF6B00`).
*   **Calibration Reliability Line**: Perfect diagonal reference series (grey dotted, `#374151`), actual calibration series (mint green, `#10B981`, thickness 2px).

---

## 3. Trade Forensics & Replay Workspace Layout

### 3.1 ASCII Layout
```
+------------------------------------------------------------------------------------+
| Rail | Toolbar: [Bookmarked Only [ ] ] [Regime: All] [Play/Pause] Speed: [1x [v]]  |
+------+-----------------------------------------------------------------------------+
| [🧪] | FORENSICS ENGINE                                         | [ⓘ] AI review     |
|      +----------------------------------------------------------+-------------------+
| [📊] | Replay Graph: Candlesticks & Execution Marks             | Decision:         |
|      |  54k |         +--+                                      | - RATING: PASS    |
| [🗂️] |      |    ++   |  |   [TP Hit 52k]                       | - Score: 88/100   |
|      |  52k |   [Entry 50k]  |                                  |                   |
| [🧬] |      |  +--+   |  |                                      | Context:          |
|      |  50k |  |  |   +--+                                      | Volume spike at   |
| [🎯] |      +-------------------------------------------------+ | resistance.       |
|      |      | [ Scrubber Timeline: ▬●▬▬▬▬▬▬▬▬ ]               |                   |
| [📈] |      +-------------------------------------------------+ | Actions:          |
|      |                                                          | [Export PDF]      |
| [⏱️] | [ List: ID 981 (BTC, +1.95%) ] [ ID 982 (ETH, -0.50%) ]   | [Export MD]       |
+------+----------------------------------------------------------+-------------------+
```

### 3.2 Spacing & Padding Scale (MQDS-Ultra-Compact)
*   **Header Bar Height**: 32px.
*   **Panel Padding**: 8px inner margin.
*   **Border Width**: 1px solid Gray-Navy (`#1F2937`).
*   **Row Height**: 20px (Compact tables).
