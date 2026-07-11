# MQDS Chart Guidelines Specification

**Sprint**: 4.9  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Quantitative Chart Standards

All charts use vector-based canvas layers, dark themes, and high contrast colors.

### 1.1 Line Chart / Equity Curve
*   **Grid lines**: Muted dotted grid lines (spacing interval relative to asset price ranges).
*   **Series Colors**: BTC (Orange), ETH (Purple), Equity Curve (Mint green).

### 1.2 Candlestick
*   Standard candles with color fills: Bullish (Mint Green hollow outline), Bearish (Crimson Red solid fill).

### 1.3 Confusion Matrix
*   Heatmap layout representing true vs predicted values (Long/Short/Neutral). Color intensity scales linearly using Tech Orange gradients.

### 1.4 Calibration Curve
*   Plots ECE reliability. Displays a diagonal dotted reference line representing perfect calibration. Actual probability distribution is rendered as a blue polygon step series.

### 1.5 Feature Importance & SHAP
*   Horizontal bar charts sorted descending. Negative SHAP values extend left (red), positive extend right (green).
