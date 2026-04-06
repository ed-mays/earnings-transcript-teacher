# DESIGN.md — EarningsFluency Design System

Extracted from approved Variant D wireframe (2026-04-06).
Reference: `~/.gstack/projects/ed-mays-earnings-transcript-teacher/designs/learning-flow-20260406/variant-D-annotated-layers.html`

---

## Color System

### Base (Zinc dark theme, matches Tailwind zinc scale)

| Token | Hex | Usage |
|---|---|---|
| `bg-base` | `#0a0a0b` | Page background, input backgrounds |
| `bg-surface` | `#111113` | Chat panel, elevated surfaces |
| `bg-card` | `#18181b` | Cards (checkpoint, chat messages) |
| `border-default` | `#27272a` | Borders, dividers, inactive pill borders |
| `border-hover` | `#3f3f46` | Hover state borders |
| `text-primary` | `#e4e4e7` | Body text, highlight text |
| `text-bright` | `#fafafa` | Headers, active nav, hovered terms |
| `text-secondary` | `#a1a1aa` | Speaker text, muted body |
| `text-dim` | `#52525b` | Labels, section dividers, speaker names |
| `text-faint` | `#3f3f46` | Placeholder text, explore count |

### Annotation Layer Colors

Each annotation type has a primary color, a background tint, and a pill background.

| Layer | Primary | Bg tint (6%) | Pill bg (8%) | Usage |
|---|---|---|---|---|
| Guidance | `#3b82f6` | `rgba(59,130,246,0.06)` | `rgba(59,130,246,0.08)` | Brief card accent, guidance highlights, chat accents |
| Evasion | `#f59e0b` | `rgba(245,158,11,0.06)` | `rgba(245,158,11,0.08)` | Evasion highlights, evasion cards |
| Sentiment | `#a855f7` | `rgba(168,85,247,0.06)` | `rgba(168,85,247,0.08)` | Sentiment highlights, sentiment badges |
| Terms | `#22c55e` | `rgba(34,197,94,0.06)` | `rgba(34,197,94,0.08)` | Term underlines, tooltip titles |

### Signal Badges

| Signal | Background | Text |
|---|---|---|
| Caution | `rgba(234,179,8,0.12)` | `#facc15` |
| Skeptical | `rgba(239,68,68,0.1)` | `#f87171` |
| Moderate | `rgba(249,115,22,0.1)` | `#fb923c` |

### Brief Card

| Token | Value |
|---|---|
| Background | `linear-gradient(135deg, #0c1425, #111827)` |
| Border | `#1e3a5f` |
| Title color | `#e2e8f0` |
| Question text | `#94a3b8` |
| Context text | `#64748b` |
| Inner border | `#1e293b` |

---

## Typography

Font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`

| Role | Size | Weight | Letter-spacing | Extra |
|---|---|---|---|---|
| Transcript header (h1) | 22px | 700 | -0.5px | Ticker in blue |
| Brief title | 15px | 600 | — | — |
| Body text (speaker text) | 14px | 400 | — | line-height: 1.8 |
| Secondary text | 13px | 400/500 | — | line-height: 1.6 |
| Nav brand | 15px | 600 | -0.3px | — |
| Labels / tags | 11px | 600 | 0.8px | uppercase |
| Highlight tags | 10px | 600 | 0.5px | uppercase |
| Buttons / pills | 11-12px | 400/500 | — | — |
| Tooltips | 12px | 400 | — | line-height: 1.5 |

---

## Spacing

| Token | Value | Usage |
|---|---|---|
| Panel padding | 48px | Transcript panel horizontal padding |
| Section gap | 24px-28px | Between sections, cards, speaker blocks |
| Card padding (large) | 24px | Brief card |
| Card padding (medium) | 16px-20px | Checkpoint cards, chat messages |
| Highlight padding | 12px 16px | Highlighted passage blocks |
| Pill gap | 8px | Between layer toggle pills |
| Pill padding | 5px 12px | Inside layer toggle pills |

---

## Border Radius

| Element | Radius |
|---|---|
| Layer pills | 20px (pill shape) |
| Brief card | 12px |
| Checkpoint card | 12px |
| Chat messages | 12px (user: 12px 12px 4px 12px) |
| Highlight blocks | 0 8px 8px 0 (left border, rounded right) |
| Tooltips | 8px |
| Signal badges | 6px |
| Buttons | 6px |
| Misconception inner cards | 8px |
| Checkpoint icon | 6px |

---

## Component Patterns

### Highlighted Passages
- Left border: 3px solid `<layer-primary>`
- Background: `<layer-bg-tint>` (6% opacity)
- Negative margin left: -16px (bleeds into padding)
- Chat icon: 24x24px circle, 15% opacity layer color, positioned absolute top-right
- Chat icon opacity: 0.5 → 1.0 on hover

### Term Annotations
- Inline: dashed bottom border 1px `#22c55e`
- Text color: `#d4d4d8` → `#fafafa` on hover
- Tooltip: 240px wide, positioned above (bottom: calc(100% + 8px))
- Tooltip bg: `#18181b`, border: `#27272a`, shadow: `0 4px 12px rgba(0,0,0,0.3)`

### Section Dividers
- Flex row: label + expanding 1px line
- Label: 11px, 600 weight, uppercase, 0.8px tracking, `#52525b`
- Line: `#27272a`

### Chat Panel
- Width: 400px fixed
- Background: `#111113` (elevated surface)
- Left border: 1px `#27272a`
- Header: context passage in italic, breadcrumb in dim text
- Input focus: blue outline + `0 0 0 3px rgba(59,130,246,0.1)` shadow

---

## Interaction States (from design review)

| Feature | Loading | Empty | Error |
|---|---|---|---|
| Annotations | Skeleton pulse on layer bar + "Loading annotations..." below | Hide layer toggles, show "No learning annotations available yet." | Dismissable banner: "Couldn't load annotations. Transcript is still readable." |
| Transcript spans | Spinner (existing pattern) | "No transcript available." | Error boundary (existing) |
| Chat panel | Existing chat loading state | Suggestion chips (existing) | Error banner (existing) |
| Term tooltips | N/A (instant) | N/A | N/A |
| Brief card | Skeleton card | Omit entirely (no brief data = no card) | Omit silently |

---

## Layout Breakpoints

| Viewport | Behavior |
|---|---|
| Desktop (>1024px) | Two-panel: transcript + 400px chat panel |
| Tablet (768-1024px) | Single panel, chat as Sheet overlay |
| Mobile (<768px) | Single column, chat as full-screen Sheet |

---

## Accessibility

- Layer toggle pills: keyboard-navigable, `role="switch"`, `aria-checked`
- Term tooltips: accessible via keyboard focus (not just hover), `role="tooltip"`
- Chat icons: `aria-label="Discuss this passage"`
- Touch targets: minimum 44px on mobile for pills and icons
- Color contrast: all text meets WCAG AA against dark background
