---
name: High-Precision SaaS Design System
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
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#595c5e'
  on-tertiary: '#ffffff'
  tertiary-container: '#727577'
  on-tertiary-container: '#fbfdff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#e0e3e5'
  tertiary-fixed-dim: '#c4c7c9'
  on-tertiary-fixed: '#191c1e'
  on-tertiary-fixed-variant: '#444749'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  mono:
    fontFamily: Geist Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1280px
  gutter: 24px
  margin-xs: 4px
  margin-sm: 8px
  margin-md: 16px
  margin-lg: 24px
  margin-xl: 40px
  margin-2xl: 64px
  padding-page: 32px
---

## Brand & Style

This design system is built upon the principles of **High-Precision Minimalism** and **Technical Sophistication**. It draws inspiration from industry leaders like Stripe and Vercel, prioritizing clarity through generous whitespace and a reductive visual language. 

The aesthetic is characterized by:
- **Utilitarian Elegance:** Every element serves a functional purpose, stripped of unnecessary decoration.
- **Glassmorphic Depth:** Subtle use of translucency and backdrop blurs to create a sense of organized layering.
- **Micro-Precision:** High-contrast labels and hairline borders (0.5pt to 1pt) communicate a "production-ready" quality.
- **Fluid Motion:** Interactions feel elastic and purposeful, utilizing ease-in-out cubics to signal responsiveness and modern engineering.

## Colors

The palette is anchored by **Indigo-600** for primary actions and **Slate-900** for deep contrast in typography and structural elements. 

- **Primary:** A vibrant Indigo used sparingly for "north star" actions and brand accents.
- **Neutrals:** A vast range of grays from Slate-50 to Slate-900. Use higher-numbered slates for primary text and lower-numbered slates for borders and secondary backgrounds.
- **The Glass Effect:** Surfaces should utilize `rgba(255, 255, 255, 0.8)` with a `backdrop-filter: blur(12px)`.
- **Contrast:** Ensure all status labels exceed WCAG 2.1 AA standards. Use high-contrast background tints for badges (e.g., a 10% opacity primary fill with a 100% opacity text color).

## Typography

This system leverages **Geist** for its technical, neutral, and highly legible characteristics. 

- **Headlines:** Use tighter letter-spacing and heavier weights to create a "locked-in" editorial look.
- **Labels:** Small labels (`label-sm`) should always be uppercase with increased tracking to ensure legibility in data-dense environments.
- **Data Display:** For tabular data, use `Geist Mono` or enable tabular-nums OpenType features to ensure column alignment.
- **Hierarchy:** Use color (Slate-900 vs Slate-500) rather than just size to denote importance.

## Layout & Spacing

The layout philosophy follows a **Fluid Grid with Generous Safe Zones**. 

- **Base Unit:** A 4px baseline grid ensures all elements align mathematically. 
- **Grid Model:** 12-column system for desktop (1280px max-width), transitioning to 8-column for tablet and 4-column for mobile.
- **Whitespace:** Prioritize vertical "breathing room." Section margins should rarely be less than 64px on desktop to maintain the premium, airy feel.
- **Data Density:** In dashboards, use "Compact" and "Comfortable" modes. Comfortable uses 16px cell padding; Compact uses 8px cell padding.

## Elevation & Depth

Depth is conveyed through **Z-axis Layering** rather than heavy shadows.

- **Level 0 (Canvas):** Flat Slate-50 or White.
- **Level 1 (Cards/Sidebar):** White surface, 1px border (#E2E8F0), no shadow.
- **Level 2 (Dropdowns/Modals):** Glassmorphic surface (80% White, 12px blur), 1px border (#E2E8F0), and a "Soft Ambient" shadow: `0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02)`.
- **Interactive States:** On hover, elements should not move (no "lifting"). Instead, the border color should shift to Primary or a darker Neutral to signal interactivity.

## Shapes

The shape language is **Soft but Structured**. 

- **Standard Radius:** 6px is the default for buttons and input fields, providing a modern look that isn't overly "bubbly."
- **Container Radius:** 10px or 14px for larger cards and modals to create a nested visual rhythm (the inner radius should be smaller than the outer radius).
- **Interactive Elements:** Checkboxes use a 4px radius, while radio buttons are always `full`.
- **Borders:** Use hairline borders (1px) in `#E2E8F0` for most containers. For dark-mode variants, use `rgba(255, 255, 255, 0.1)`.

## Components

### Buttons
- **Primary:** Solid Indigo-600 background, White text. Subtle 1px inner-top-border in a lighter indigo for a "3D" tactile hint.
- **Secondary:** White background, Slate-900 text, 1px border (#E2E8F0).
- **Ghost:** No background or border. Text color Slate-600, shifting to Slate-900 on hover.

### Inputs
- **Default State:** White background, 1px Slate-200 border. 
- **Focus State:** 1px Indigo-600 border with a 3px soft Indigo halo (`rgba(99, 102, 241, 0.1)`).
- **Labels:** Always use `label-md` weight above the field.

### Cards
- Surfaces are White or Glass.
- Always include a 1px border (#F1F5F9).
- Titles should be `headline-md` or `body-md` (bold).

### Chips & Badges
- High-contrast, low-saturation. E.g., Success badge: Background `rgba(16, 185, 129, 0.1)`, Text `#065F46`.
- Radius should be `full`.

### Animations
- **Transitions:** All color and opacity changes use `200ms cubic-bezier(0.4, 0, 0.2, 1)`.
- **Enter/Exit:** Modals should slide up 8px while fading in to simulate a physical "settling" onto the canvas.