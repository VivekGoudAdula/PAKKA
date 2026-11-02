# Design System

## Brand Feel

**Warm, confident, crafted. Indian without clichés. Light theme only (for now).**

---

## Design Tokens

All tokens are CSS custom properties. They are mapped into Tailwind's theme extension and shadcn's CSS variable conventions.

```css
/* Colors */
--background:   #FBF9F4;   /* warm paper */
--surface:      #FFFFFF;
--surface-2:    #F4F0E8;
--ink:          #15130F;
--muted:        #6B6558;
--border:       #E8E2D5;

/* Brand */
--primary:      #FF9F1C;   /* Saffron */
--primary-hover:#E88A00;
--primary-fg:   #15130F;   /* text-on-primary = ink */

/* Semantic */
--success:      #12805C;   /* Pakka green */
--warning:      #D97706;
--danger:       #D64545;
--info:         #3B5BDB;
```

### Gradients & Textures
- Soft saffron glow gradients (radial, from primary at ~10% opacity)
- Subtle noise texture overlay (SVG or CSS)
- Hairline borders (`1px solid var(--border)`)
- Layered soft box-shadows (no harsh drops)

### Shape
- Border radius: **14–20 px** on cards/surfaces, 8–10 px on inputs/badges
- Glass navbar with `backdrop-filter: blur(12px)` and semi-transparent background

---

## Typography

Loaded via `next/font`:

| Role | Font | Usage |
|---|---|---|
| Display / Headlines | **Bricolage Grotesque** | Hero text, section heads |
| UI Body | **Geist** (or Inter fallback) | All body copy, UI labels |
| Mono | **JetBrains Mono** | Live transcript, code |
| Hindi / Devanagari | **Noto Sans Devanagari** | Bilingual microcopy |

### Bilingual Microcopy
Use natural Hinglish where appropriate, e.g.:
- "Pakka ✓ / पक्का"
- "Booking confirmed / बुकिंग पक्की हो गई"

---

## Signature Element — PAKKA ✓ Stamp

A slightly-rotated rounded stamp mark used:
1. When a job is confirmed (full-page/card overlay moment)
2. On job cards (top-right badge)
3. In the hero section

**Animation:** Framer Motion spring scale-in (scale 0 → 1 + slight bounce), with a mild rotation wobble.  
**Shape:** Rounded rectangle or circle border with double-rule, bold text "PAKKA ✓" (or पक्का in Devanagari).  
**Color:** Pakka green (`--success`) or saffron (`--primary`) based on context.

---

## Component Policy

### Priority Hierarchy
1. **shadcn/ui** — default primitives
2. **Sera UI** (https://seraui.com/docs) — expressive/signature pieces
3. **daisyUI** — only where it has no equal

### 1. shadcn/ui Primitives
`Button, Card, Dialog, Sheet, Tabs, Table, Badge, Input, Select, Tooltip, Skeleton, Sonner, Command, DropdownMenu, ScrollArea, Switch, Slider, Progress, Avatar, Calendar`

### 2. Sera UI Components
`Hero, Navigation Header, Bento Grid, Timeline, Number Ticker, Shimmer/Glow Button, Spotlight/Magic Card, Marquee, Text Reveal/Flip Words, Animated/Verify Badge, Progress Bar, Noise Background, Announcement Banner, FAQ, Footer, App Dock`

> **Re-theming rule:** Many Sera components are dark-styled. Replace all hard-coded dark colors with our CSS variables before use.

**Installation:** Via Sera CLI or copy-paste from https://seraui.com/docs/installation

### 3. daisyUI (Restricted Use)
Use **only** where shadcn/Tailwind has no equal:
- `chat` (live transcript bubbles)
- `stat`
- `steps`
- `mockup-phone` / `mockup-window`
- `radial-progress`

**Config rules:**
- Use a **class prefix** (e.g., `daisy-`) to avoid collision
- Disable `themes` and `base` overrides in config
- Verify current config options in daisyUI docs

### 4. Component Folder Layout

```
components/
├── ui/       # shadcn/ui copies (auto-generated)
├── sera/     # Sera UI copies, re-themed
├── daisy/    # daisyUI wrapper components
└── pakka/    # Composed brand components (app code imports from here)
```

> **Rule:** Never mix two UI libraries inside one component.

---

## Responsive Design

- **Mobile-first** — breakpoints: 360, 768, 1024, 1440 px
- No horizontal scroll at any breakpoint
- Touch targets ≥ 44 px
- Dashboard uses **bottom nav** on mobile (< 768 px)
- Tables collapse into cards on mobile

---

## Accessibility

- WCAG AA contrast on all text
- Visible focus rings (custom ring using `--primary`)
- ARIA labels on all interactive elements
- Full keyboard navigation support

---

## Motion

- **Framer Motion** — springs only (no linear eases for brand animations)
- Keep animations subtle and purposeful
- All motion respects `prefers-reduced-motion` media query

