# SC Dossier — Design System Analysis

## Source Material

The Aegis Liquid Interface design system is documented in:
- `ui-example-files/DESIGN.md` — design tokens YAML + written design principles
- `ui-example-files/code.html` — full reference HTML implementation
- `ui-example-files/image.png` — visual reference screenshot

---

## Design Identity

**Name**: Aegis Liquid Interface  
**Category**: Deep-space glassmorphism + aerospace HUD  
**Emotional intent**: Authority, immersion, high-tech precision, cold elegance  
**Reference aesthetic**: Shipboard HUD, tactical telemetry display, military-spec hardware

---

## Color System

### Base Palette

| Token | Hex | Role |
|---|---|---|
| `space-void` | `#050B0F` | App background (deepest layer) |
| `surface` | `#031521` | Primary surface |
| `surface-dim` | `#031521` | Dimmed surface variant |
| `surface-bright` | `#2A3B48` | Elevated surface |
| `surface-container-lowest` | `#00101B` | Lowest container depth |
| `surface-container-low` | `#0A1D29` | Low container |
| `surface-container` | `#0F212E` | Standard container (glass card bg) |
| `surface-container-high` | `#1A2C38` | High container |
| `surface-container-highest` | `#253744` | Highest container (most visible) |

### Interactive Colors

| Token | Hex | Role |
|---|---|---|
| `primary` | `#93CCFF` | Primary accent / text highlights |
| `primary-container` | `#00AAFF` | Interactive glow, borders, active states |
| `secondary` | `#AEC6FF` | Secondary highlights |
| `secondary-container` | `#4F8EFF` | Secondary interactive states |
| `glass-border` | `rgba(0,170,255,0.3)` | Card border (translucent blue) |

### Semantic Colors

| Token | Hex | Role |
|---|---|---|
| `on-surface` | `#D2E5F6` | Primary readable text |
| `on-surface-variant` | `#BEC7D3` | Secondary text |
| `text-dim` | `#A8B3BD` | Tertiary/metadata text |
| `hazard-red` | `#FF3B3B` | Errors, warnings, destructive actions |
| `outline` | `#88929D` | General outlines |
| `outline-variant` | `#3E4851` | Subtle dividers |

---

## Typography System

### Font Stack

| Font | Use Case |
|---|---|
| **Sora** | Display, headlines, major titles |
| **Inter** | Body text, UI controls, descriptions |
| **JetBrains Mono** | Technical data, IDs, status readouts, metadata |

All three fonts must be bundled in `src/assets/fonts/` and registered via `QFontDatabase`.

### Type Scale

| Style Name | Font | Size | Weight | Tracking | Line Height | Use |
|---|---|---|---|---|---|---|
| `headline-xl` | Sora | 32px | 700 | -0.02em | 1.2 | App title, major page headers |
| `headline-lg` | Sora | 24px | 600 | 0.05em | 1.3 | Section titles |
| `body-md` | Inter | 14px | 400 | normal | 1.6 | Descriptions, bio text |
| `data-point` | JetBrains Mono | 13px | 500 | 0.03em | 1.4 | Values, handles, dates, IDs |
| `label-caps` | JetBrains Mono | 11px | 700 | 0.15em | 1.2 | ALL-CAPS labels, status readouts |

---

## Layout System

### Structural Grid

```
┌─────────────────────────────────────────────────┐
│ CustomTitleBar (48px)                           │
├──────────┬──────────────────────────────────────┤
│          │                                      │
│ NavSide  │  Main Content Area                   │
│ bar      │  (12-column fluid grid)              │
│ (64px    │                                      │
│ icon     │                                      │
│ rail)    │                                      │
│          │                                      │
├──────────┴──────────────────────────────────────┤
│ CustomStatusBar (28px)                          │
└─────────────────────────────────────────────────┘
```

### Spacing Tokens

| Token | Value | Use |
|---|---|---|
| `panel-margin` | 24px | Between glass card panels |
| `gutter` | 16px | Internal panel padding |
| `sidebar-width` | 64px (rail) / 240px (expanded) | Nav sidebar |
| `titlebar-height` | 48px | Title bar fixed height |
| `status-height` | 28px | Status bar fixed height |

---

## Elevation & Depth

Depth is communicated through **light and opacity stacking**, not shadows:

| Layer | Treatment |
|---|---|
| App background | `#050B0F` — pure black base |
| Glass panels | `rgba(10,29,41,0.4)` + simulated backdrop blur |
| Active/popup states | Increased opacity, brighter border glow |
| Focused elements | `#00AAFF` glow via `QGraphicsDropShadowEffect` |

Simulating backdrop blur in PyQt6:
- Use `QGraphicsBlurEffect` applied to a background snapshot captured before the widget is shown
- Or use a semi-transparent `rgba` background with increased opacity as a simpler fallback
- The visual goal is layered depth — exact blur is secondary to the color layering

---

## Shape Language

**"Hard Tech"** — minimal roundedness, military precision:

| Element | Corner Radius |
|---|---|
| Glass cards | `0.25rem` (4px) — very slight |
| Buttons | `0.25rem` (4px) |
| Status chips | `9999px` (full pill) — contrast element |
| Input fields | `0.375rem` (6px) |

**Chamfered corners** on some buttons and panel headers — 45° clip instead of radius — reinforces sci-fi HUD aesthetic. Implemented via `QPainter` clipping path.

---

## Component Specifications

### Glass Card (Primary Container)

```
Background:    rgba(10, 29, 41, 0.4)
Border:        1px rgba(0, 170, 255, 0.15)
Corner radius: 4px
Padding:       16px
Corner ornaments: 8×8px #00AAFF L-shapes (painted in QPainter paintEvent)
```

### Custom Title Bar

```
Height:        48px
Background:    surface-container-low (#0A1D29)
Bottom border: 1px rgba(0, 170, 255, 0.15)
Left:          App icon + app name in label-caps
Center:        Status indicators (time, connection)
Right:         Pin button + Hide button
Drag region:   Entire bar (except buttons)
```

### Custom Status Bar

```
Height:        28px
Background:    #020D14
Left:          Animated pulse dot + "SYSTEM STATUS: NOMINAL"
Right:         PING · UPTIME · connection icon
Typography:    label-caps, JetBrains Mono
```

### Navigation Sidebar (Icon Rail)

```
Width (collapsed): 64px
Width (expanded):  240px
Items: Search, Dossier, Organization, Archive, Settings
Active item:    bg-primary/10 + border border-primary/20 + inner glow
Hover:          Horizontal gradient rgba(79,142,255,0.2) → transparent
```

### Primary Button

```
Background:    #00AAFF (solid)
Text:          UPPERCASE, bold, white
Animation:     Scanning line overlay (QPropertyAnimation)
Hover:         Brightness +15%, outer glow
```

### Ghost Button

```
Background:    transparent
Border:        1px #00AAFF with tech-bracket corners
Hover:         10% blue tint fill (rgba(0,170,255,0.1))
```

### Input Field

```
Background:    rgba(5, 11, 15, 0.8) (recessed dark)
Border:        1px outline-variant (#3E4851)
Focus border:  1px primary-container (#00AAFF) + full glow effect
Animation:     Scanning line on focus (QPropertyAnimation)
```

### List Items (Archive, Roster)

```
Background:    transparent default
Hover:         Horizontal gradient rgba(79,142,255,0.2) → transparent
Selected:      bg-primary/15 + left border 2px #00AAFF
```

### Overlay Toolbar

```
Size:     ~240px × 48px (horizontal) or 48px × 240px (vertical)
Style:    Frameless, translucent, dark glass panel
Border:   1px glass-border
Always-on-top: Yes (WindowStaysOnTopHint)
Buttons:  Two icon-only buttons with SVG icons
Opacity:  Configurable (default 1.0)
```

---

## Animation Principles

| Animation | Implementation | Duration |
|---|---|---|
| Button scanning line | `QPropertyAnimation` on a gradient overlay | 1.5s loop |
| Input focus glow | `QPropertyAnimation` on `QGraphicsDropShadowEffect` blur radius | 200ms ease-in |
| Nav sidebar expand | `QPropertyAnimation` on `maximumWidth` | 200ms ease-out |
| List hover glow | `QPropertyAnimation` on background gradient | 150ms |
| Archive pane collapse | `QPropertyAnimation` on `maximumWidth` | 250ms ease-in-out |
| Progress overlay | Repeating scanline animation | 800ms loop |

---

## PyQt6 Implementation Notes

- `WA_TranslucentBackground` must be set on any frameless window using glass effects
- `FramelessWindowHint` must be paired with custom drag implementation in mouse events
- Tech bracket corners must be painted in `paintEvent` via `QPainter` — CSS cannot do this in QSS
- `QGraphicsDropShadowEffect` with `blurRadius=20, color=#00AAFF, offset=(0,0)` simulates outer glow
- `QPropertyAnimation` targeting `geometry` or custom properties implements scanline animations
- Always call `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)` before `setWindowFlags`
