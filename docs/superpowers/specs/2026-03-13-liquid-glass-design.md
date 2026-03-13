# Liquid Glass Style Revamp

## Goal

Replace the current dark opaque UI style with Apple-inspired liquid glass aesthetics using David UI's Tailwind-based approach. No new JS dependencies — pure CSS changes applied to existing Jinja2 templates.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Glass library | David UI (Tailwind classes) | Zero bundle cost, works with existing Tailwind CDN, integrates naturally with Jinja2 templates |
| Background | Dark blue/purple gradient | Provides depth for glass panels to blur against while keeping the serious finance-app mood |
| Glass treatment | Layered glass with gradient shine | Top-left and bottom-right light gradients simulate light refraction; brighter top border edge adds dimension |
| Accent color | Cyan/teal (`#2dd4bf`) | Pops against blue/purple gradient; blue would blend in |
| Header | Frosted glass, sticky | Consistent glass frame with bottom nav |
| Bottom nav | Frosted glass + teal glow on active tab | Apple-like treatment with active indicator |

## Implementation

### 1. Define `.glass` utility class in `static/style.css`

Rather than repeating 8+ Tailwind classes on every element, define a reusable `.glass` class:

```css
.glass {
  position: relative;
  background: rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 14px;
  box-shadow:
    inset 0 1px 0px rgba(255, 255, 255, 0.6),
    0 0 9px rgba(0, 0, 0, 0.2),
    0 3px 8px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.glass::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(255,255,255,0.45) 0%, transparent 40%);
  opacity: 0.7;
  pointer-events: none;
}

.glass::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(315deg, rgba(255,255,255,0.2) 0%, transparent 40%);
  opacity: 0.5;
  pointer-events: none;
}

/* Content inside glass must be above pseudo-elements */
.glass > * {
  position: relative;
  z-index: 1;
}
```

Variants for specific contexts:
- `.glass-header` — `border-radius: 0; border-left: none; border-right: none; border-top: none;`
- `.glass-nav` — same as header but `border-bottom: none; border-top: ...`
- `.glass-input` — lighter background (`rgba(0,0,0,0.1)`), no pseudo-elements, focus ring in teal

### 2. Body background in `base.html`

Replace solid background with gradient:

```css
body {
  background: #0a0e1a;
  background-image:
    radial-gradient(ellipse at 20% 50%, rgba(59, 38, 120, 0.4) 0%, transparent 60%),
    radial-gradient(ellipse at 80% 20%, rgba(29, 60, 120, 0.35) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(20, 30, 80, 0.3) 0%, transparent 60%);
  min-height: 100vh;
}
```

### 3. Accent color swap

Global find-and-replace in templates:

| Old | New | Context |
|-----|-----|---------|
| `text-blue-400` | `text-teal-400` | Active nav, links |
| `text-blue-500` | `text-teal-500` | Hover states |
| `bg-blue-600` | `bg-teal-600` | Primary buttons |
| `bg-blue-900/30` | `bg-teal-900/30` | Highlighted totals |
| `border-blue-800` | `border-teal-800` | Focus borders, highlights |
| `ring-blue-*` | `ring-teal-*` | Focus rings |

Preserve red/green/yellow for financial data colors — those are semantic and unchanged.

### 4. Template changes

**`base.html`**:
- Body: remove `bg-gray-950`, add gradient background via inline style or Tailwind arbitrary values
- Header: replace `bg-gray-900 border-b border-gray-800` with `glass glass-header`
- Bottom nav: replace `bg-gray-900 border-t border-gray-800` with `glass glass-nav`, add teal glow under active item
- Remove `dark` class from `<html>` if only used for gray theming

**All page templates** (`transactions.html`, `balances.html`, `income_statement.html`, `balance_sheet.html`, `budget.html`, `register.html`):
- Cards: replace `bg-gray-900 border border-gray-800 rounded-lg` with `glass`
- Hover states: replace `hover:border-gray-600` with `hover:border-white/50`
- Section backgrounds: replace `bg-gray-800/50` with glass or lighter glass variant

**Partials** (modal, transaction detail, edit form):
- Modal backdrop: keep `bg-black/70`
- Modal panel: replace `bg-gray-900 border-gray-700` with `glass`
- Form inputs: apply `.glass-input` class

**`static/style.css`**:
- Add `.glass`, `.glass-header`, `.glass-nav`, `.glass-input` classes
- Update `.input` class for glass styling
- Update loading bar color from blue to teal
- Update any hardcoded gray background colors

### 5. Elements preserved (no changes)

- Layout structure (max-width, padding, grid columns)
- HTMX behavior (`hx-boost`, partials, swaps)
- Alpine.js modal state management
- PWA manifest and meta tags
- iOS safe-area inset handling
- Pull-to-refresh gesture
- Monospace font for amounts
- Red/green/yellow financial data colors
- Transaction card grid responsiveness
- All route handlers in `app.py`
- All hledger.py logic

## Risks

| Risk | Mitigation |
|------|------------|
| `backdrop-filter` not supported in older browsers | Graceful fallback — panels just show solid bg without blur. All content remains readable. |
| Glass pseudo-elements (`::before`/`::after`) conflict with existing pseudo-elements | Audit templates for existing `before:`/`after:` Tailwind usage; restructure if needed |
| Teal accent may not meet WCAG contrast on dark bg | `#2dd4bf` on `#0a0e1a` = 10.2:1 ratio — passes AAA |
| Glass borders too bright on content-dense pages (budget, balance sheet) | Can reduce `border-white/40` to `border-white/20` per page if needed |

## Out of scope

- No changes to `app.py` or `hledger.py`
- No new JavaScript dependencies
- No changes to data flow or caching
- No changes to PWA manifest or service worker
- No responsive breakpoint changes
