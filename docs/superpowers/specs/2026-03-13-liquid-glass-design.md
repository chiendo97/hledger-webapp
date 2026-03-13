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

### 1. Define glass classes in `static/style.css`

#### `.glass` — base glass panel

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
}

.glass::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(255,255,255,0.45) 0%, transparent 40%);
  opacity: 0.7;
  pointer-events: none;
  z-index: 0;
}

.glass::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(315deg, rgba(255,255,255,0.2) 0%, transparent 40%);
  opacity: 0.5;
  pointer-events: none;
  z-index: 0;
}

/* Content inside glass must be above pseudo-elements */
.glass > * {
  position: relative;
  z-index: 1;
}
```

Note: `.glass` does NOT set `overflow: hidden` — scrollable containers (e.g., modal panel with `overflow-y-auto`) must not be clipped.

#### `.glass-header` — sticky top bar

```css
.glass-header {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}
.glass-header::before,
.glass-header::after {
  border-radius: 0;
}
```

#### `.glass-nav` — fixed bottom nav

```css
.glass-nav {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-bottom: none;
}
.glass-nav::before,
.glass-nav::after {
  border-radius: 0;
}
```

#### `.glass-input` — form inputs

```css
.glass-input {
  background: rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 10px;
  color: #e2e8f0;
  box-shadow: inset 0 1px 0px rgba(255, 255, 255, 0.4);
  outline: none;
  transition: all 0.2s;
}
.glass-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}
.glass-input:focus {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(45, 212, 191, 0.5);
  box-shadow: inset 0 1px 0px rgba(255, 255, 255, 0.4), 0 0 0 2px rgba(45, 212, 191, 0.2);
}
```

No `::before`/`::after` pseudo-elements on inputs — they don't support them and inputs may have browser pseudo-elements (e.g., date picker indicators).

#### `.glass-chip` — filter pills and tabs

```css
.glass-chip {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  color: #94a3b8;
  transition: all 0.2s;
}
.glass-chip.active,
.glass-chip-active {
  background: rgba(45, 212, 191, 0.15);
  border-color: rgba(45, 212, 191, 0.3);
  color: #2dd4bf;
}
```

Replaces `bg-blue-600`/`bg-gray-700` pills in depth selector, sort toggle, and source filters.

#### `.glass-btn` — secondary/cancel buttons

```css
.glass-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  color: #e2e8f0;
  transition: all 0.2s;
}
.glass-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
}
```

Replaces `bg-gray-700 hover:bg-gray-600` on Close/Cancel buttons.

### 2. Body background in `static/style.css`

Add to `style.css` (replaces `bg-gray-950` which gets removed from `base.html`):

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
| `text-blue-300` | `text-teal-300` | Hover links |
| `text-blue-400` | `text-teal-400` | Active nav, links |
| `text-blue-500` | `text-teal-500` | Hover states |
| `bg-blue-500` | `bg-teal-500` | Button hover states |
| `bg-blue-600` | `bg-teal-600` | Primary buttons, active pills |
| `bg-blue-700` | `bg-teal-700` | Button hover states |
| `bg-blue-900/30` | `bg-teal-900/30` | Highlighted totals |
| `border-blue-800` | `border-teal-800` | Focus borders, highlights |
| `hover:bg-blue-700` | `hover:bg-teal-700` | Button hovers |
| `hover:bg-blue-500` | `hover:bg-teal-500` | Button hovers |
| `hover:text-blue-300` | `hover:text-teal-300` | Link hovers |
| `ring-blue-*` | `ring-teal-*` | Focus rings |
| `rgb(59 130 246)` | `rgb(45 212 191)` | Hardcoded blue in style.css (loading bar, input focus) |

Preserve red/green/yellow for financial data colors — those are semantic and unchanged.

### 4. Template changes

**`base.html`**:
- Body: remove `bg-gray-950` from class list (gradient now in `style.css`)
- Header: replace `bg-gray-900 border-b border-gray-800` with `glass glass-header`
- Bottom nav: replace `bg-gray-900 border-t border-gray-800` with `glass glass-nav`, add teal glow under active item
- `<meta name="theme-color" content="#0a0e1a">` — update from `#111827`
- Pull-to-refresh indicator: replace `bg-gray-800 text-gray-300` with `glass` styling
- Keep `dark` class on `<html>` — it controls Tailwind's `dark:` utilities and must stay

**All page templates** (`transactions.html`, `balances.html`, `income_statement.html`, `balance_sheet.html`, `budget.html`, `register.html`):
- Cards: replace `bg-gray-900 border border-gray-800 rounded-lg` with `glass`
- Hover states: replace `hover:border-gray-600` with `hover:border-white/50`
- Section backgrounds: replace `bg-gray-800/50` with glass or lighter glass variant
- Active pills/chips: replace `bg-blue-600`/`bg-gray-700` with `.glass-chip`/`.glass-chip-active`
- Secondary buttons: replace `bg-gray-700 hover:bg-gray-600` with `.glass-btn`

**Partials** (modal, transaction detail, edit form, skeleton, depth selector, sort toggle):
- Modal backdrop: keep `bg-black/70`
- Modal panel: replace `bg-gray-900 border-gray-700` with `glass` (keep `overflow-y-auto` on the scrollable inner container, which overrides since `.glass` doesn't set overflow)
- Form inputs: replace `.input` class with `.glass-input`
- Skeleton loading: replace `bg-gray-800/50 rounded-lg` with `glass` + shimmer
- Depth selector pills: use `.glass-chip` / `.glass-chip-active`
- Sort toggle pills: use `.glass-chip` / `.glass-chip-active`

**`static/style.css`**:
- Add all `.glass*` classes defined above
- Add body gradient background
- Replace `.input` with `.glass-input` (or update in-place)
- Update loading bar color from blue to teal
- Update any hardcoded `rgb(59 130 246)` to `rgb(45 212 191)`

### 5. Elements preserved (no changes)

- `dark` class on `<html>` (required for Tailwind `dark:` utilities)
- Layout structure (max-width, padding, grid columns)
- HTMX behavior (`hx-boost`, partials, swaps)
- Alpine.js modal state management
- iOS safe-area inset handling
- Pull-to-refresh gesture logic (only styling changes)
- Monospace font for amounts
- Red/green/yellow financial data colors
- Transaction card grid responsiveness
- All route handlers in `app.py`
- All hledger.py logic

## Risks

| Risk | Mitigation |
|------|------------|
| `backdrop-filter` not supported in older browsers | Graceful fallback — panels show solid bg without blur. All content remains readable. |
| Glass `::before`/`::after` conflict with inputs | `.glass-input` has no pseudo-elements. Only `.glass` panels use them. Browser pseudo-elements on date pickers already styled in `style.css` — verify they still work. |
| Teal accent may not meet WCAG contrast on dark bg | `#2dd4bf` on `#0a0e1a` = 10.2:1 ratio — passes AAA |
| Glass borders too bright on content-dense pages | Can reduce `border-white/40` to `border-white/20` per page if needed |
| Stacked `backdrop-filter` performance on mobile | Multiple blurred layers (header + cards + nav) can lag on older iOS. Mitigate by keeping blur radius small (`8px`) and testing on real devices. |
| Alpine.js template fragments inside `.glass` | `.glass > *` selector only targets direct children. Alpine `x-if`/`x-for` may insert fragments — test modal rendering and add explicit `relative z-1` classes if needed. |

## Out of scope

- No changes to `app.py` or `hledger.py`
- No new JavaScript dependencies
- No changes to data flow or caching
- No changes to PWA manifest (only `theme-color` meta tag updated)
- No responsive breakpoint changes
