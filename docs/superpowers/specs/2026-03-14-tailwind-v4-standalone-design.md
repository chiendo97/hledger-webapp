# Tailwind v4 Standalone CLI Setup & Theming Design

## Goal

Migrate from Tailwind CSS CDN to Tailwind v4 standalone CLI with a single CSS input file (`style.css` at project root) controlling all design tokens and component classes. Restyle the entire app by editing one file. No Node.js dependency.

## Decision

| Choice | Option | Rationale |
|--------|--------|-----------|
| Tailwind version | v4 (CSS-native config) | Single-file config via `@theme`, no `tailwind.config.js` needed |
| Build tool | Tailwind v4 standalone binary via `pytailwindcss` | No Node.js — stays in the Python toolchain |
| Theming approach | Semantic `@theme` tokens + `@apply` component classes | Colors defined once as tokens, repeated patterns as component classes |
| Build step | Yes | Required for `@theme`/`@apply`; adds one `RUN` line to Dockerfile |

## Tooling Setup

### pytailwindcss

Install via `uv` as a dependency group in `pyproject.toml`:

```toml
[dependency-groups]
build = ["pytailwindcss"]
```

The `pytailwindcss` package version pins the Tailwind binary version, ensuring reproducible builds. On first run, it downloads the correct standalone binary for the current platform. This requires internet access during `docker build` and local dev setup.

### Dev workflow

```bash
# First time after clone (dist.css is gitignored):
uv run --group build tailwindcss -i style.css -o static/dist.css

# Terminal 1: CSS watcher
uv run --group build tailwindcss -i style.css -o static/dist.css --watch

# Terminal 2: Dev server
uv run python app.py
```

### base.html changes

Replace:
```html
<link rel="stylesheet" href="/static/style.css">
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={darkMode:'class'}</script>
```

With:
```html
<link rel="stylesheet" href="/static/dist.css">
```

Remove `class="dark"` from `<html>` — the app is dark-only, tokens define the palette directly without `dark:` variants. Confirmed: no `dark:` prefixed classes exist in any template.

### Dockerfile

Single-stage build, no Node image needed:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends hledger && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --group build --frozen

COPY app.py hledger.py ./
COPY templates/ templates/
COPY static/ static/
COPY style.css ./

# Build CSS — pytailwindcss downloads the standalone binary (requires internet)
RUN uv run tailwindcss -i style.css -o static/dist.css --minify

RUN groupadd --gid 1000 appuser && \
    useradd --create-home --uid 1000 --gid 1000 appuser
USER appuser

EXPOSE 8000

ENV UV_NO_SYNC=1

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
```

### .gitignore additions

```
static/dist.css
```

## CSS Input File Location

The Tailwind input file lives at `style.css` in the project root (not inside `static/`). This avoids Litestar's static file serving exposing the raw unprocessed CSS with `@import`/`@theme` directives to browsers. Only the compiled `static/dist.css` is served.

## Content Detection

Tailwind v4 automatically scans the working directory for source files when it sees `@import "tailwindcss"`. It will find `.html` files in `templates/` and `templates/partials/`. Jinja2 syntax (`{{ }}`, `{% %}`) does not interfere with class detection.

One Alpine.js dynamic class binding exists in `base.html` (`:class="p.negative ? 'text-red-400' : 'text-green-400'"`). During Phase 2, this becomes `text-negative`/`text-positive`. Tailwind's scanner handles string literals inside `:class` bindings correctly.

## Theme Tokens (`@theme`)

All design tokens live in `style.css` (project root) under `@theme`:

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
  --color-surface-button: #374151;    /* secondary buttons (gray-700) */
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
  --color-surface-highlight: rgb(30 58 138 / 0.3);  /* net worth/net summary bg */
  --color-border-highlight: #1e3a8a;  /* net summary border (blue-800) */

  /* Total row */
  --color-surface-total: rgb(31 41 55 / 0.5);  /* subtotal/total row bg */

  /* Interactive text */
  --color-text-link-danger: #fca5a5;  /* delete link hover (red-300) */
  --color-text-link-accent: #93c5fd;  /* add link hover (blue-300) */
}
```

### Token to utility mapping

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
| `--color-accent-light` | `bg-accent-light` | `bg-blue-500` |
| `--color-surface-button` | `bg-surface-button` | `bg-gray-700` |
| `--color-surface-button-hover` | `bg-surface-button-hover` | `hover:bg-gray-600` |
| `--color-surface-inset` | `bg-surface-inset` | `bg-gray-800` |
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

Defined in `style.css` after the `@theme` block:

```css
.card {
  @apply bg-surface-raised border border-border rounded-lg p-3 cursor-pointer hover:border-border-hover;
}

.btn {
  @apply bg-accent hover:bg-accent-hover text-white rounded-lg px-4 py-2 font-medium;
}

.input {
  @apply bg-surface-raised border border-border-input rounded px-3 py-2 text-sm text-text focus:border-accent-text focus:outline-none;
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

The current `static/style.css` contains rules that must be carried forward into the new `style.css` below the `@theme` and component class blocks:

- Loading bar animation (`#loading-bar`, `@keyframes load-progress`) — update `#3b82f6` to `var(--color-accent-light)`
- iOS safe-area insets (header, nav, body padding)
- Tap-highlight removal and overscroll behavior
- Date input calendar picker icon styling

The existing `.input` class gets replaced by the new `@apply`-based version.

## Migration Plan

### Phase 1 — Tooling switch

1. Add `pytailwindcss` to `pyproject.toml` as a `build` dependency group
2. Create `style.css` at project root with `@import "tailwindcss"`, `@theme`, component classes, and preserved existing CSS from `static/style.css`
3. Remove old `static/style.css` (its contents are now in root `style.css`)
4. Update `base.html`: replace CDN `<script>` tags and old stylesheet link with `<link rel="stylesheet" href="/static/dist.css">`, remove `class="dark"` from `<html>`
5. Update `Dockerfile` with `uv sync --no-dev --group build --frozen` and CSS build `RUN` line
6. Add `static/dist.css` to `.gitignore`
7. Verify the app renders identically

### Phase 2 — Template migration

1. Replace hardcoded color classes with semantic tokens across all templates
2. Replace repeated class combos with component classes
3. Verify each template after migration

## CI/CD

No changes needed to `.github/workflows/docker.yml`. The Docker build already has internet access (required for `pytailwindcss` to download the standalone binary on first run). The binary is cached in the Docker layer after the first build.

## What stays the same

- All route handlers, `hledger.py`, Pydantic models — zero backend changes
- HTMX/Alpine.js behavior untouched
- Layout structure, grids, responsive breakpoints unchanged
- Dynamic `account_color()` inline styles unchanged
- iOS PWA safe-area handling stays in CSS (moves into the new `style.css`)
- Financial color semantics (red/green) preserved via `--color-positive`/`--color-negative`
