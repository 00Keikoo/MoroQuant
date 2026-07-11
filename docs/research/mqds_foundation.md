# MQDS Foundation Specification

**Sprint**: 4.9  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Visual Foundation

### 1.1 Color Palette & Dark Theme
*   **Background (Primary)**: Deep Slate Hex `#0B0F19` (Bloomberg-adjacent).
*   **Background (Secondary)**: Muted Dark Hex `#111827` (Card panels).
*   **Borders/Dividers**: Grey-Navy Hex `#1F2937` (Sharp grid lines).
*   **Accent Color**: Tech Orange Hex `#FF6B00` (High visibility highlights).

### 1.2 Semantic Colors
*   `SUCCESS`: Mint Green Hex `#10B981` (Pass validation/calibration).
*   `FAILURE`: Crimson Red Hex `#EF4444` (Fold errors, execution rejection).
*   `WARNING`: Amber Yellow Hex `#F59E0B` (Slippage anomalies, skew drift).
*   `PENDING/RUNNING`: Electric Indigo Hex `#6366F1` (Queue processing).

### 1.3 Typography Scale (Monospace Preferred)
*   Standard Font Family: `SF Pro Display`, `Inter` (UI elements).
*   Data Font Family: `SF Mono`, `JetBrains Mono` (Table metrics, logs).
*   Sizes: `Micro (10px)`, `Caption (11px)`, `Small (12px)`, `Body (13px)`, `Header (16px)`.

---

## 2. Layout, Grid, and Accessibility

### 2.1 Density Modes
*   **Default Mode (Ultra-Compact)**: Row heights set to `24px` with `4px` cell padding. Maximize cell metrics visible on a single screen.

### 2.2 Grid & Spacing System
*   **Grid Base**: 4px base increments. Spacing tokens: `4px`, `8px`, `12px`, `16px`.
*   **Border Radius**: Highly angular. `2px` for buttons, cards, and input fields. `0px` for tabular cell headers.

### 2.3 Focus States & Accessibility
*   **Keyboard Navigation**: Active elements highlighted with `1px Solid Tech Orange` focus outlines. 
*   **Contrast Standards**: Contrast ratios set to minimum `7:1` to support dark-room environment visibility.
