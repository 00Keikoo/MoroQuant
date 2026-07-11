# Trade Replay Design Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Visual Playback Scrubber

The Replay Panel renders historical tick-by-tick orderbook logs or 1-minute OHLCV candles, allowing the researcher to replay the trade lifecycle.

```
┌────────────────────────────────────────────────────────┐
│  [Play/Pause] [⏪] [⏩]  Speed: [1x] [5x] [25x] [Max]   │
│  [▬|▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬]  │
│  00:00 (Entry)       01:15 (Regime Change)    02:30 (Exit)│
└────────────────────────────────────────────────────────┘
```

### 1.1 Playback Controls
*   **⏪ Step Backward / ⏩ Step Forward**: Moves the playback state by 1 candle/tick.
*   **Playback Speed**: Logarithmic acceleration (`0.5x`, `1x`, `5x`, `25x`, `100x`).

### 1.2 Annotations & Markers
*   **Entry Marker (Green Hexagon)**: Placed at the exact timestamp and entry execution price.
*   **Exit Marker (Red Hexagon)**: Placed at exit timestamp.
*   **Target Indicators**: Dotted horizontal bounds indicating the active `Take Profit (TP)` and `Stop Loss (SL)` levels.

### 1.3 State Visualizations
*   **Floating PnL**: Sparkline overlay showing dynamic unrealized PnL scaling over duration.
*   **Regime Changes**: Background panel color bands indicating shifts in the underlying market regime (e.g. transitioning from `TRENDING_LONG` to `RANGE`).
