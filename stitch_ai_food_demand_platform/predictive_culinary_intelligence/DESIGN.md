---
name: Predictive Culinary Intelligence
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#464554'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#767586'
  outline-variant: '#c7c4d7'
  surface-tint: '#494bd6'
  primary: '#4648d4'
  on-primary: '#ffffff'
  primary-container: '#6063ee'
  on-primary-container: '#fffbff'
  inverse-primary: '#c0c1ff'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#825100'
  on-tertiary: '#ffffff'
  tertiary-container: '#a36700'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.05em
  mono-label:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1440px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is engineered for high-stakes decision-making within the food supply chain. It balances the technical precision of developer-centric tools like Vercel with the financial reliability of Stripe. The aesthetic is **Glassmorphic Minimalism**: a style that prioritizes data clarity through high-contrast typography while using layered translucency to establish depth and hierarchy.

The target audience consists of procurement managers and operations directors who require a "source of truth" for inventory forecasting. The emotional response should be one of absolute control, foresight, and professional sophistication. The UI feels airy yet dense with information, using "white space as a separator" rather than heavy lines.

## Colors

The palette is anchored by **Deep Indigo (#6366f1)**, used for primary actions and brand presence. Growth metrics, positive forecasts, and "safe" inventory levels utilize **Emerald (#10b981)**. A Tertiary **Amber** is reserved strictly for supply chain disruptions or low-stock alerts.

The system uses a highly refined neutral scale based on **Slate and Zinc**. In light mode, surfaces are semi-transparent white over a subtle gray-to-white gradient background. In dark mode, the "thin border" approach uses `#1e293b` to define containers against a deep slate background. Background blurs (`backdrop-filter: blur(12px)`) are essential for maintaining legibility on translucent card surfaces.

## Typography

This design system employs a dual-font strategy. **Geist** is used for headlines, navigation, and technical labels to provide a precise, engineered feel. **Inter** handles the heavy lifting for body copy and data descriptions to ensure maximum readability across dense tables.

For data-heavy dashboard views, use the `mono-label` setting which utilizes tabular numbers to ensure that fluctuating demand figures align vertically for quick scanning. High-contrast text (Slate-900 on White) is required for all primary data points.

## Layout & Spacing

The system follows a **12-column fluid grid** for the main dashboard content, with a fixed-width left sidebar (240px). Layouts are constructed using a "container-first" approach where cards snap to the grid.

- **Desktop:** 48px outer margins with 24px gutters.
- **Tablet:** 32px outer margins; cards typically stack into 2 columns.
- **Mobile:** 16px margins; all cards reflow to a single column. 

Vertical spacing follows an 8px rhythm. Information density is managed through the use of "Safe Zones"—areas of 32px-48px white space that surround major data visualizations to prevent visual fatigue.

## Elevation & Depth

Depth is communicated through three specific layers:

1.  **Level 0 (Background):** Solid color or subtle radial gradient.
2.  **Level 1 (Cards/Panels):** Semi-transparent surfaces (`rgba(255, 255, 255, 0.7)`) with a 1px solid border (`#e2e8f0`) and a soft, multi-layered shadow.
3.  **Level 2 (Overlays/Modals):** Higher opacity white with a more aggressive backdrop blur (`20px`) and a deep, diffused shadow (`0 20px 25px -5px rgba(0,0,0,0.1)`).

Shadows must feel "weightless." Avoid black; instead, use a tinted indigo shadow (`rgba(99, 102, 241, 0.05)`) to maintain the vibrant, clean aesthetic.

## Shapes

The design system utilizes **2xl roundedness**. Primary containers and cards use a 1rem (16px) corner radius, while large dashboard sections or main "hero" cards can scale up to 1.5rem (24px). Smaller elements like buttons and input fields utilize 0.5rem (8px) to maintain a crisp relationship with the larger containers. Buttons should never be fully pill-shaped; they should remain subtly rectangular to maintain the professional B2B tone.

## Components

### Buttons
Primary buttons use the Deep Indigo background with white text and a very subtle inner top-light border to simulate a slight 3D pressable surface. Secondary buttons are "ghost" style with a 1px border and a background that appears only on hover.

### Cards
Cards are the cornerstone of the platform. They must include `backdrop-filter: blur()`. Header sections within cards should be separated by a thin horizontal rule (`#e2e8f0`). 

### Data Visualization
Charts (Line and Bar) should use Emerald for "Forecasted Demand" and Slate for "Historical Data." Use area gradients beneath lines to emphasize volume.

### Inputs
Search and filter inputs use a "sunken" feel—a 1px border with a slightly darker interior background than the card they sit on. This creates a tactile sense of where data is entered.

### Status Chips
Status chips (e.g., "In Transit", "Low Stock") use low-saturation backgrounds with high-saturation text to ensure they are visible without distracting from the primary metrics.