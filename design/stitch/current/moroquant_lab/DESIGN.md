---
name: MoroQuant Lab
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1b1c1c'
  surface-container: '#1f2020'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353535'
  on-surface: '#e4e2e1'
  on-surface-variant: '#e2bfb0'
  inverse-surface: '#e4e2e1'
  inverse-on-surface: '#303030'
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
  secondary-container: '#474746'
  on-secondary-container: '#b7b5b4'
  tertiary: '#9ccaff'
  on-tertiary: '#003257'
  tertiary-container: '#059eff'
  on-tertiary-container: '#003357'
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
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#d0e4ff'
  tertiary-fixed-dim: '#9ccaff'
  on-tertiary-fixed: '#001d35'
  on-tertiary-fixed-variant: '#00497b'
  background: '#131313'
  on-background: '#e4e2e1'
  surface-variant: '#353535'
typography:
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  mono-data:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  mono-label:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 12px
    letterSpacing: 0.05em
  mono-code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  panel-gap: 1px
  container-padding: 8px
  cell-padding-x: 6px
  cell-padding-y: 2px
---

## Brand & Style

The design system is engineered for high-stakes quantitative research and financial modeling. The aesthetic is "Institutional Technical"—a fusion of the information density of a Bloomberg Terminal with the refined utility of modern developer tools. 

The system prioritizes raw data visibility and systematic clarity over decorative elements. It utilizes a **Functional Minimalist** approach with a heavy lean toward **Brutalist Utility**. The UI is characterized by high-density layouts, zero-latency visual cues, and a strict adherence to a grid-based, panel-driven architecture. 

The emotional response should be one of total control, precision, and surgical efficiency. It is a workspace for experts where information scent is maximized, and decorative "breathing room" is sacrificed for data proximity.

## Colors

The palette is strictly functional, utilizing a "True Dark" foundation to minimize eye strain during long research sessions and maximize contrast for data visualization.

- **Foundational Surfaces:** The workspace uses a pure black (#000000) base. Active panels and containers use nested shades of charcoal (#121212 and #1A1A1A) to create structural depth without using elevation shadows.
- **Accents:** "Institutional Orange" (#FF6B00) is reserved for high-priority interactions, active states, and primary call-to-actions.
- **Borders:** All structural separation is handled by Slate (#2D2D2D) 1px borders.
- **Semantic Status:** Success, Warning, and Danger colors are highly saturated and used sparingly for status indicators, tickers, and validation states.

## Typography

This design system employs a dual-type strategy to distinguish between UI navigation and quantitative data.

- **UI Interface:** **Inter** is used for all functional labels, headers, and navigation elements. It is set at smaller scales (12px-13px) to facilitate high-density information architecture.
- **Data & Logic:** **JetBrains Mono** is used for all numeric output, financial tickers, code blocks, and technical metadata. The monospaced nature ensures that columns of numbers align perfectly for visual scanning.
- **Scaling:** Headlines never exceed 18px. The hierarchy is driven by weight and color (High-emphasis white vs. Medium-emphasis gray) rather than large scale changes.

## Layout & Spacing

The layout is a **Fixed-Panel Grid** system inspired by IDEs (Integrated Development Environments). 

- **Structural Rhythm:** All spacing is based on a strict 4px baseline. However, to maximize density, internal component padding often utilizes 2px increments.
- **Panels:** The UI is divided into resizable "tiles" separated by 1px slate borders. There is no gutter or "air" between panels.
- **Density:** Padding is minimized. Lists and tables use a compact 2px/6px (vertical/horizontal) cell padding to ensure the maximum number of rows are visible above the fold.
- **Breakpoints:** The system is designed for ultra-wide desktop monitors (1440px+). On smaller screens, panels collapse into tabs rather than reflowing in a fluid manner.

## Elevation & Depth

This design system avoids shadows and Z-axis depth. Hierarchy is established through:

- **Border Containment:** 1px solid borders (#2D2D2D) define all boundaries.
- **Tonal Stepping:** Lower-level surfaces (backgrounds) are #000000, while foreground panels are #121212. Active or "hovered" items use #1A1A1A.
- **Focus States:** High-priority active elements (like a selected input or active code line) use a 1px #FF6B00 border or a subtle left-side accent bar.
- **No Blurs:** Transparency and backdrop blurs are strictly forbidden to ensure maximum text legibility and performance.

## Shapes

The shape language is predominantly **Sharp**. 

- **Global Radius:** A 2px radius is applied only to buttons and input fields to provide a slight affordance of "interactivity." 
- **Containers:** All primary panels, sidebars, and data tables use 0px (Sharp) corners to maintain the structural integrity of the grid.
- **Status Pills:** Small status indicators may use a 2px radius but should never be fully pill-shaped.

## Components

- **Buttons:** Rectangular with a 2px radius. Primary buttons use a solid #FF6B00 background with black text. Secondary buttons are outline-only with 1px #2D2D2D borders.
- **Data Tables:** The core component. Header rows are #1A1A1A with uppercase Mono labels. Rows use 1px bottom borders. Hover states highlight the entire row in #1A1A1A. Numeric cells must use JetBrains Mono.
- **Input Fields:** Flat #000000 background with a #2D2D2D border. On focus, the border changes to #FF6B00. No inset shadows.
- **Vertical Step Indicators (Chronicle):** Used for backtesting stages or data pipelines. A 1px vertical line connects solid 6px squares. Active steps glow #FF6B00; completed steps are #00C853.
- **Inspector Panels:** Right-aligned, collapsible panels for property editing. Uses extremely dense form layouts with labels positioned to the left of the input to save vertical space.
- **Tabs:** "Folder-style" tabs with sharp corners. Active tabs have a 2px #FF6B00 top border.