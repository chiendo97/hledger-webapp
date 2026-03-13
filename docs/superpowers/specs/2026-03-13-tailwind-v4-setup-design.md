# Tailwind v4 Setup & Theming Design

## Goal

Migrate from Tailwind CSS CDN to Tailwind v4 CLI with a single CSS file (`static/style.css`) controlling all design tokens and component classes. This enables centralized theming — restyle the entire app by editing one file.

## Decision

| Choice | Option | Rationale |
|--------|--------|-----------|
| Tailwind version | v4 (CSS-native config) | Single-file config via `@theme`, no `tailwind.config.js` needed |
| Build tool | `@tailwindcss/cli` | Minimal tooling, no bundler, tree-shaken output |
| Theming approach | Semantic `@theme` tokens + `@apply` component classes | Colors defined once as tokens, repeated patterns as component classes |
| Build step | Yes | Required for `@theme`/`@apply`; adds `package.json` + npm to project |

## Tooling Setup

### New files

- `package.json` + `package-lock.json` — `@tailwindcss/cli` as dev dependency (run `npm install` locally first to generate lock file, commit both)
- `static/dist.css` — generated output (gitignored)
- `node_modules/` — (gitignored)

### base.html changes

Replace:
```html
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={darkMode:'class'}</script>
```

With:
```html
<link rel="stylesheet" href="/static/dist.css">
```

### Dev command

```bash
npx @tailwindcss/cli -i static/style.css -o static/dist.css --watch
```

### Dockerfile addition

Use a multi-stage build: Node stage builds the CSS, then copy the output into the Python image.

```dockerfile
# Stage 1: Build CSS
FROM node:22-slim AS css-builder
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
# Templates must be copied before CSS build — Tailwind v4 scans them for class usage
COPY static/style.css static/style.css
COPY templates/ templates/
RUN npx @tailwindcss/cli -i static/style.css -o static/dist.css --minify

# Stage 2: Python app (existing, with one addition)
FROM python:3.12-slim
# ... existing setup ...
COPY --from=css-builder /build/static/dist.css static/dist.css
```

### .gitignore additions

```
static/dist.css
node_modules/
```

## Theme Tokens (`@theme`)

All design tokens live in `static/style.css` under `@theme`:

```css
@import "tailwindcss";

@theme {
  /* Surfaces */
  --color-surface: #030712;           /* body background (gray-950) */
  --color-surface-raised: #111827;    /* cards, header, nav (gray-900) */
  --color-surface-overlay: #000000b3; /* modal backdrop */

  /* Borders */
  --color-border: #1f2937;            /* default borders (gray-800) */
  --color-border-hover: #4b5563;      /* hover state (gray-600) */
  --color-border-input: #374151;      /* form inputs (gray-700) */

  /* Text */
  --color-text: #f3f4f6;              /* primary text (gray-100) */
  --color-text-muted: #9ca3af;        /* secondary (gray-400) */
  --color-text-faint: #6b7280;        /* tertiary (gray-500) */
  --color-text-heading: #d1d5db;      /* descriptions (gray-300) */

  /* Accent */
  --color-accent: #2563eb;            /* primary buttons (blue-600) */
  --color-accent-hover: #1d4ed8;      /* button hover (blue-700) */
  --color-accent-text: #60a5fa;       /* active nav links (blue-400) */
  --color-accent-light: #3b82f6;      /* loading bar, lighter interactive (blue-500) */

  /* Secondary surfaces */
  --color-surface-button: #374151;    /* secondary buttons like Close/Cancel (gray-700) */
  --color-surface-button-hover: #4b5563; /* secondary button hover (gray-600) */
  --color-surface-inset: #1f2937;     /* pull-to-refresh, inset areas (gray-800) */

  /* Success */
  --color-success: #16a34a;           /* Save button (green-600) */
  --color-success-hover: #22c55e;     /* Save hover (green-500) */

  /* Financial (semantic) */
  --color-positive: #4ade80;          /* green amounts */
  --color-negative: #f87171;          /* red amounts */

  /* Warning */
  --color-warning: #eab308;           /* budget threshold indicator (yellow-500) */
  --color-warning-text: #facc15;      /* budget warning text (yellow-400) */

  /* Highlight surfaces (net/summary boxes) */
  --color-surface-highlight: rgb(30 58 138 / 0.3);  /* net worth/net summary bg (blue-900/30) */
  --color-border-highlight: #1e3a8a;  /* net summary border (blue-800) */

  /* Total row */
  --color-surface-total: rgb(31 41 55 / 0.5);  /* subtotal/total row bg (gray-800/50) */

  /* Interactive text */
  --color-text-link-danger: #fca5a5;  /* delete link hover (red-300) */
  --color-text-link-accent: #93c5fd;  /* add link hover (blue-300) */
}
```

### Token → utility mapping

| Token | Utility class | Replaces |
|-------|--------------|----------|
| `--color-surface` | `bg-surface` | `bg-gray-950` |
| `--color-surface-raised` | `bg-surface-raised` | `bg-gray-900` |
| `--color-surface-overlay` | `bg-surface-overlay` | `bg-black/70` |
| `--color-border` | `border-border` | `border-gray-800` |
| `--color-border-hover` | `border-border-hover` | `border-gray-600` |
| `--color-border-input` | `border-border-input` | `border-gray-700` |
| `--color-text` | `text-text` | `text-gray-100` |
| `--color-text-muted` | `text-text-muted` | `text-gray-400` |
| `--color-text-faint` | `text-text-faint` | `text-gray-500` |
| `--color-text-heading` | `text-text-heading` | `text-gray-300` |
| `--color-accent` | `bg-accent` | `bg-blue-600` |
| `--color-accent-hover` | `bg-accent-hover` | `hover:bg-blue-700` |
| `--color-accent-text` | `text-accent-text` | `text-blue-400` |
| `--color-accent-light` | `bg-accent-light` | `bg-blue-500`, loading bar `#3b82f6` |
| `--color-surface-button` | `bg-surface-button` | `bg-gray-700` |
| `--color-surface-button-hover` | `bg-surface-button-hover` | `hover:bg-gray-600` |
| `--color-surface-inset` | `bg-surface-inset` | `bg-gray-800` (pull-to-refresh, etc.) |
| `--color-success` | `bg-success` | `bg-green-600` |
| `--color-success-hover` | `bg-success-hover` | `hover:bg-green-500` |
| `--color-positive` | `text-positive` | `text-green-400` |
| `--color-negative` | `text-negative` | `text-red-400` |
| `--color-warning` | `bg-warning` | `bg-yellow-500` |
| `--color-warning-text` | `text-warning-text` | `text-yellow-400` |
| `--color-surface-highlight` | `bg-surface-highlight` | `bg-blue-900/30` |
| `--color-border-highlight` | `border-border-highlight` | `border-blue-800` |
| `--color-surface-total` | `bg-surface-total` | `bg-gray-800/50` |
| `--color-text-link-danger` | `text-text-link-danger` | `text-red-300` |
| `--color-text-link-accent` | `text-text-link-accent` | `text-blue-300` |

## Component Classes (`@apply`)

Defined in `static/style.css` after the `@theme` block:

```css
.card {
  @apply bg-surface-raised border border-border rounded-lg p-3 cursor-pointer hover:border-border-hover;
}

.btn {
  @apply bg-accent hover:bg-accent-hover text-white rounded-lg px-4 py-2 font-medium;
}

.input {
  @apply bg-surface-raised border border-border-input rounded-lg px-3 py-2 text-sm text-text focus:border-accent-text focus:outline-none;
}

.chip {
  @apply px-3 py-1 rounded-full text-xs bg-surface-raised text-text-muted hover:bg-surface-raised/80;
}

.chip-active {
  @apply px-3 py-1 rounded-full text-xs bg-accent text-white;
}

.divider {
  @apply flex items-center gap-3 text-sm font-medium text-text-heading;
}
.divider::before,
.divider::after {
  content: "";
  @apply flex-1 border-t border-border-hover;
}

.skeleton {
  @apply animate-pulse bg-surface-raised/50 rounded-lg;
}

.btn-secondary {
  @apply bg-surface-button hover:bg-surface-button-hover text-text rounded-lg px-4 py-2 font-medium;
}

.btn-success {
  @apply bg-success hover:bg-success-hover text-white rounded-lg px-4 py-2 font-medium;
}
```

## Existing CSS to preserve

The current `static/style.css` contains non-trivial rules that must be carried forward below the `@theme` and component class blocks:

- Loading bar animation (`#loading-bar`, `@keyframes load-progress`) — update `#3b82f6` to `var(--color-accent-light)`
- iOS safe-area insets (header, nav, body padding)
- Tap-highlight removal and overscroll behavior
- Date input calendar picker icon styling

The `.input` class gets replaced by the new `@apply`-based version.

## Migration Plan

### Phase 1 — Tooling switch

1. Run `npm init -y && npm install -D @tailwindcss/cli` to create `package.json` + `package-lock.json`
2. Rewrite `static/style.css` with `@import "tailwindcss"`, `@theme`, component classes, and preserved existing CSS
3. Update `base.html`: replace CDN `<script>` tags with `<link rel="stylesheet" href="/static/dist.css">`, remove `class="dark"` from `<html>` (no longer needed — app is dark-only with tokens, not `dark:` variants)
4. Update `Dockerfile` with multi-stage Node build for CSS
5. Add `static/dist.css` and `node_modules/` to `.gitignore`
6. Verify the app renders identically

### Phase 2 — Template migration

1. Replace hardcoded color classes with semantic tokens across all templates
2. Replace repeated class combos with component classes

## What stays the same

- All route handlers, `hledger.py`, Pydantic models — zero backend changes
- HTMX/Alpine.js behavior untouched
- Layout structure, grids, responsive breakpoints unchanged
- Dynamic `account_color()` inline styles unchanged
- iOS PWA safe-area handling stays in CSS
- Financial color semantics (red/green) preserved
