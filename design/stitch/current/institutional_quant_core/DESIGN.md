---
name: Institutional Quant Core
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e2bfb0'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#a98a7d'
  outline-variant: '#5a4136'
  surface-tint: '#ffb693'
  primary: '#ffb693'
  on-primary: '#561f00'
  primary-container: '#ff6b00'
  on-primary-container: '#572000'
  inverse-primary: '#a04100'
  secondary: '#c8c6c5'
  on-secondary: '#313030'
  secondary-container: '#4a4949'
  on-secondary-container: '#bab8b7'
  tertiary: '#c8c6c5'
  on-tertiary: '#303030'
  tertiary-container: '#9a9999'
  on-tertiary-container: '#313131'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbcc'
  primary-fixed-dim: '#ffb693'
  on-primary-fixed: '#351000'
  on-primary-fixed-variant: '#7a3000'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1c1b1b'
  on-secondary-fixed-variant: '#474646'
  tertiary-fixed: '#e4e2e1'
  tertiary-fixed-dim: '#c8c6c5'
  on-tertiary-fixed: '#1b1c1c'
  on-tertiary-fixed-variant: '#474746'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: IBM Plex Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  header-md:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: 0.01em
  body-base:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-caps:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  panel-gutter: 1px
  container-margin: 12px
---

## Brand & Style
The design system is engineered for high-frequency institutional trading environments where cognitive load management and data density are paramount. The aesthetic is **High-Contrast / Technical**, leaning into a "Command Center" philosophy. It prioritizes utility over decoration, utilizing a strictly modular, grid-based approach reminiscent of integrated development environments (IDEs).

The emotional response should be one of absolute precision and reliability. By utilizing a dark, low-distraction canvas, the system allows critical data points and "Institutional Orange" alerts to occupy the user's primary focus. There is no room for organic shapes or soft transitions; the interface is composed of sharp 1px strokes and rigid mathematical alignment.

## Colors
The palette is built on a "Total Dark" architecture to minimize eye strain during long-duration monitoring.

*   **Surface Foundation:** The primary workspace background is a deep `#090909`. Panels and containers use `#141414` to provide subtle structural separation without breaking the dark continuity.
*   **Structural Definition:** All borders and dividers are strictly `#262626`. This creates a visible but unobtrusive skeleton for the high-density data.
*   **Primary Accent:** `#FF6B00` (Institutional Orange) is used exclusively for primary actions, active navigation states, and critical system indicators.
*   **Semantic Data:** Success (Long/Profit) uses a vibrant Mint Green, while Danger (Short/Loss) uses a high-visibility Red. These are the only "color" permitted outside of the primary accent to ensure they carry maximum signal weight.

## Typography
The typographic system utilizes a tri-font strategy to differentiate between structural headers, interface controls, and raw data.

1.  **Structural (IBM Plex Sans):** Used for panel titles, page headers, and high-level navigation. It provides a technical, engineered feel that distinguishes layout from content.
2.  **Interface (Inter):** Used for tooltips, button labels, and general UI descriptions. Its high legibility at small sizes is essential for dense layouts.
3.  **Data (JetBrains Mono):** Mandatory for all tickers, prices, PnL values, and timestamps. The monospaced nature ensures that numeric values do not "jump" when updating rapidly, maintaining a stable visual column in tables.

All type is strictly aligned to a 4px baseline grid to ensure vertical rhythm in high-density components.

## Layout & Spacing
This design system utilizes a **Fixed-Panel Grid** modeled after professional IDEs. The screen is treated as a single viewport (no scrolling on the main axis) with internal scroll regions.

*   **Panel System:** Content is housed in "Cells" separated by 1px borders. These cells should feel resizable.
*   **Density:** Spacing is extremely tight (8px default internal padding for containers) to maximize "Above the Fold" information.
*   **Structural Layout:** 
    *   **Left Rail:** Persistent 48px-64px icon-driven navigation.
    *   **Top Bar:** Global system health, connectivity status, and breadcrumbs.
    *   **Right Inspector:** A collapsible 280px-320px panel for contextual details (e.g., trade history for a specific ticker).
    *   **Main Stage:** A fluid area that accommodates multi-column data tables or charts.

## Elevation & Depth
Depth is communicated through **Tonal Layering** rather than shadows. Shadows are disabled to maintain the "flat-terminal" aesthetic.

*   **Level 0 (Base):** `#090909` - The canvas.
*   **Level 1 (Panels):** `#141414` - All data containers, charts, and table backgrounds.
*   **Level 2 (Inlays):** `#090909` - Input fields or nested lists within panels to create an "etched" look.
*   **Level 3 (Modals/Popovers):** `#1C1C1C` with a 1px `#333333` border. These are the only elements allowed to have a subtle drop shadow (0px 8px 24px rgba(0,0,0,0.5)) to ensure they float above the dense background.

## Shapes
The system uses a **Soft-Geometric** shape language.

*   **Containers & Panels:** Strictly 0px (sharp) to allow 1px borders to meet perfectly at intersections.
*   **Buttons & Inputs:** 2px border-radius. This provides just enough visual distinction from the background grid to identify them as interactive elements.
*   **Status Tags/Chips:** 2px border-radius or sharp.
*   **Charts:** All line strokes should be 1.5px to 2px, utilizing sharp miters for data points.

## Components
### Buttons
*   **Primary:** Background `#FF6B00`, Text `#FFFFFF`, 2px radius.
*   **Secondary:** Border 1px `#262626`, Background `transparent`, Text `#A1A1A1`.
*   **Ghost:** No background or border, Text `#A1A1A1`, turns White on hover.

### Data Tables
*   **Header:** 24px height, `#141414` background, border-bottom 1px `#262626`, text labels in `label-caps`.
*   **Rows:** 28px height, no zebra striping. Use 1px `#262626` dividers. Hover state: `#1C1C1C`.
*   **Cells:** All numeric data must use `data-tabular` (JetBrains Mono) right-aligned.

### Input Fields
*   Background: `#090909` (etched into the panel).
*   Border: 1px `#262626`.
*   Focus State: 1px `#FF6B00` border. No outer glow.

### Information Chips
*   Compact (16px height). 
*   Solid backgrounds for status (Green for 'Live', Red for 'Emergency Stop').
*   Monospaced text for all ID or hash-based chips.

### Navigation Rails
*   Active state: 2px thick vertical line in `#FF6B00` on the leading edge of the active icon.