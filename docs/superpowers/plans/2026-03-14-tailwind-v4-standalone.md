# Tailwind v4 Standalone CLI Migration Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate from Tailwind CSS CDN to Tailwind v4 standalone CLI with centralized theming in a single `style.css` file.

**Architecture:** Two-phase migration. Phase 1 switches tooling (CDN to compiled CSS) without changing visual output. Phase 2 replaces hardcoded color classes with semantic tokens and component classes. No backend changes.

**Tech Stack:** pytailwindcss (Tailwind v4 standalone binary wrapper), Tailwind v4 `@theme`/`@apply`, uv dependency groups

**Spec:** `docs/superpowers/specs/2026-03-14-tailwind-v4-standalone-design.md`

---

## Chunk 1: Phase 1 — Tooling Switch

### Task 1: Add pytailwindcss dependency and update .gitignore

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Add build dependency group to pyproject.toml**

Add after the existing `[dependency-groups]` `dev` group:

```toml
[dependency-groups]
dev = [
    "basedpyright>=1.38.0",
    "ruff>=0.15.1",
]
build = ["pytailwindcss"]
```

- [ ] **Step 2: Add static/dist.css to .gitignore**

Append to `.gitignore`:

```
# Tailwind compiled output
static/dist.css
```

- [ ] **Step 3: Lock dependencies**

Run: `uv lock`

Expected: `uv.lock` updated with `pytailwindcss` and its dependencies.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .gitignore
git commit -m "Add pytailwindcss build dependency and gitignore dist.css"
```

---

### Task 2: Create style.css with @theme tokens, component classes, and preserved CSS

**Files:**
- Create: `style.css` (project root)
- Delete: `static/style.css`

- [ ] **Step 1: Create style.css at project root**

Write the complete `style.css` with all sections. The `@import "tailwindcss"` directive tells Tailwind v4 to scan the working directory for class usage in `.html` files.

```css
@import "tailwindcss";

/* ===== Theme Tokens ===== */

@theme {
  /* Surfaces */
  --color-surface: #030712;
  --color-surface-raised: #111827;
  --color-surface-overlay: #000000b3;

  /* Borders */
  --color-border: #1f2937;
  --color-border-hover: #4b5563;
  --color-border-input: #374151;

  /* Text */
  --color-text: #f3f4f6;
  --color-text-muted: #9ca3af;
  --color-text-faint: #6b7280;
  --color-text-heading: #d1d5db;

  /* Accent */
  --color-accent: #2563eb;
  --color-accent-hover: #1d4ed8;
  --color-accent-text: #60a5fa;
  --color-accent-light: #3b82f6;

  /* Secondary surfaces */
  --color-surface-button: #374151;
  --color-surface-button-hover: #4b5563;
  --color-surface-inset: #1f2937;

  /* Success */
  --color-success: #16a34a;
  --color-success-hover: #22c55e;

  /* Financial (semantic) */
  --color-positive: #4ade80;
  --color-negative: #f87171;

  /* Warning */
  --color-warning: #eab308;
  --color-warning-text: #facc15;

  /* Highlight surfaces */
  --color-surface-highlight: rgb(30 58 138 / 0.3);
  --color-border-highlight: #1e3a8a;

  /* Total row */
  --color-surface-total: rgb(31 41 55 / 0.5);

  /* Interactive text */
  --color-text-link-danger: #fca5a5;
  --color-text-link-accent: #93c5fd;
}

/* ===== Component Classes ===== */

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

/* ===== Preserved CSS (from old static/style.css) ===== */

html {
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  overscroll-behavior-y: contain;
}

input[type="date"]::-webkit-calendar-picker-indicator {
  filter: invert(0.7);
}

/* Safe area insets for iOS standalone mode */
header.sticky {
  padding-top: env(safe-area-inset-top);
}
nav.fixed.bottom-0 {
  padding-bottom: env(safe-area-inset-bottom);
}
body {
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

/* Top loading bar */
#loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  z-index: 9999;
  width: 0;
  background: var(--color-accent-light);
  pointer-events: none;
}
#loading-bar.active {
  animation: load-progress 8s cubic-bezier(0.2, 0.5, 0.3, 1) forwards;
}
#loading-bar.done {
  animation: none;
  width: 100%;
  opacity: 0;
  transition: opacity 300ms ease;
}
@keyframes load-progress {
  0% { width: 0; }
  20% { width: 40%; }
  50% { width: 70%; }
  100% { width: 90%; }
}
```

- [ ] **Step 2: Delete old static/style.css**

```bash
rm static/style.css
```

- [ ] **Step 3: Build CSS to verify the new style.css compiles**

```bash
uv sync --group build
uv run --group build tailwindcss -i style.css -o static/dist.css
```

Expected: `static/dist.css` is created with compiled CSS. No errors.

- [ ] **Step 4: Commit**

```bash
git add style.css
git rm static/style.css
git commit -m "Create centralized style.css with theme tokens and component classes"
```

---

### Task 3: Update base.html to use compiled CSS

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: Replace CDN scripts and old stylesheet with compiled dist.css**

In `templates/base.html`, find these three lines (around lines 13-15):

```html
  <link rel="stylesheet" href="/static/style.css">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config={darkMode:'class'}</script>
```

Replace with:

```html
  <link rel="stylesheet" href="/static/dist.css">
```

- [ ] **Step 2: Remove class="dark" from html element**

In `templates/base.html`, find line 2:

```html
<html lang="en" class="dark">
```

Replace with:

```html
<html lang="en">
```

- [ ] **Step 3: Rebuild CSS and verify the app loads**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
uv run python app.py
```

Open `http://localhost:8000` and verify the app renders. At this point it should look the same — all existing Tailwind utility classes are still compiled by Tailwind v4's content scanner.

- [ ] **Step 4: Commit**

```bash
git add templates/base.html
git commit -m "Switch from Tailwind CDN to compiled dist.css"
```

---

### Task 4: Update Dockerfile

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Update uv sync flags and add CSS build step**

Replace the current Dockerfile content with:

```dockerfile
FROM python:3.12-slim

# Install hledger
RUN apt-get update && \
    apt-get install -y --no-install-recommends hledger && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --group build --frozen

# Copy application code
COPY app.py hledger.py ./
COPY templates/ templates/
COPY static/ static/
COPY style.css ./

# Build CSS — first invocation downloads the standalone binary (requires internet)
RUN uv run --group build tailwindcss -i style.css -o static/dist.css --minify

RUN groupadd --gid 1000 appuser && \
    useradd --create-home --uid 1000 --gid 1000 appuser
USER appuser

EXPOSE 8000

ENV UV_NO_SYNC=1

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "Update Dockerfile for Tailwind CSS build step"
```

---

## Chunk 2: Phase 2 — Template Migration (base.html)

### Task 5: Migrate base.html color classes to semantic tokens

**Files:**
- Modify: `templates/base.html`

This is the largest template (245 lines). Work through it section by section. After each edit, rebuild CSS and check the page.

- [ ] **Step 1: Migrate body, header, and bottom nav (lines 19, 22, 40)**

Find on line 19:
```html
<body hx-boost="true" class="bg-gray-950 text-gray-100 min-h-screen font-mono"
```
Replace color classes only (keep `font-mono`):
```html
<body hx-boost="true" class="bg-surface text-text min-h-screen font-mono"
```

Find the header element (line 22) with `bg-gray-900` and `border-gray-800`, replace with `bg-surface-raised` and `border-border`.

Find the bottom nav (line 40) with `bg-gray-900 border-t border-gray-800`, replace with `bg-surface-raised border-t border-border`.

- [ ] **Step 2: Migrate pull-to-refresh indicator**

Replace `bg-gray-800` with `bg-surface-inset` and `text-gray-300` with `text-text-heading`.

- [ ] **Step 3: Migrate navigation items (6 nav items)**

For each of the 6 nav items, replace:
- `text-blue-400` (active) → `text-accent-text`
- `text-gray-400` (inactive) → `text-text-muted`

- [ ] **Step 4: Migrate modal overlay and container**

Replace:
- `bg-black/70` → `bg-surface-overlay`
- `bg-gray-900` → `bg-surface-raised`
- `border-gray-700` → `border-border-input`

- [ ] **Step 5: Migrate modal content sections**

Replace across modal content:
- `border-gray-800` → `border-border` (all dividers, ~5 occurrences)
- `text-gray-400` → `text-text-muted` (labels, ~6 occurrences)
- `text-gray-100` → `text-text` (values)
- `text-gray-300` → `text-text-heading` (tag values)
- `text-gray-500` → `text-text-faint` (balance assertion, posting tags)

- [ ] **Step 6: Migrate Alpine.js :class binding**

Find:
```html
:class="p.negative ? 'text-red-400' : 'text-green-400'"
```
Replace with:
```html
:class="p.negative ? 'text-negative' : 'text-positive'"
```

- [ ] **Step 7: Migrate modal action buttons**

Find the Edit button with `bg-blue-600 hover:bg-blue-500`, replace with `.btn` class. Note: this changes hover from lighter (blue-500) to darker (accent-hover/blue-700) per the spec's token design — a minor intentional visual change.

Find Close/Cancel buttons with `bg-gray-700 hover:bg-gray-600`, replace with `bg-surface-button hover:bg-surface-button-hover` (or use `btn-secondary` class).

Find Save button with `bg-green-600 hover:bg-green-500`, replace with `bg-success hover:bg-success-hover` (or use `btn-success` class).

- [ ] **Step 8: Migrate interactive text links**

Replace across edit mode:
- `text-red-400 hover:text-red-300` (delete links) → `text-negative hover:text-text-link-danger`
- `text-blue-400 hover:text-blue-300` (add links) → `text-accent-text hover:text-text-link-accent`

- [ ] **Step 9: Migrate error message**

Replace `text-red-400` → `text-negative`.

- [ ] **Step 10: Rebuild and verify**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
uv run python app.py
```

Open `http://localhost:8000`, click through transactions, open detail/edit modals, verify all colors look correct.

- [ ] **Step 11: Commit**

```bash
git add templates/base.html
git commit -m "Migrate base.html to semantic color tokens"
```

---

## Chunk 3: Phase 2 — Template Migration (partials)

### Task 6: Migrate tx_list.html

**Files:**
- Modify: `templates/partials/tx_list.html`

- [ ] **Step 1: Migrate date divider**

Replace the date divider pattern (lines 3-5):
- `border-gray-600` → `border-border-hover` (2 occurrences)
- `text-gray-300` → `text-text-heading`

Or replace the whole `<div>` + `<span>` + `<div>` group with the `.divider` component class.

- [ ] **Step 2: Migrate transaction card**

Replace the card `<div>` class combo `bg-gray-900 border border-gray-800 ... hover:border-gray-600` with the `.card` component class (keeping any extra classes like `p-3` that `.card` already includes, remove duplicates).

- [ ] **Step 3: Migrate card content colors**

Replace:
- `text-gray-500` → `text-text-faint` (timestamp, balance assertion)
- `text-gray-600` → `text-text-faint` (transaction index — close enough)
- `text-gray-300` → `text-text-heading` (description)

- [ ] **Step 4: Migrate conditional amount colors**

Replace:
- `text-red-400` → `text-negative`
- `text-green-400` → `text-positive`

- [ ] **Step 5: Migrate empty state**

Replace `text-gray-500` → `text-text-faint`.

- [ ] **Step 6: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/tx_list.html
git commit -m "Migrate tx_list.html to semantic tokens"
```

---

### Task 7: Migrate tx_form.html

**Files:**
- Modify: `templates/partials/tx_form.html`

- [ ] **Step 1: Migrate form container and button**

Replace:
- `bg-gray-900 border border-gray-800` → `bg-surface-raised border border-border`
- Submit button `bg-blue-600 hover:bg-blue-700` → use `.btn` class

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/tx_form.html
git commit -m "Migrate tx_form.html to semantic tokens"
```

---

### Task 8: Migrate month_picker.html

**Files:**
- Modify: `templates/partials/month_picker.html`

- [ ] **Step 1: Migrate prev/next buttons and date input**

Replace:
- `bg-gray-800 text-gray-400 hover:bg-gray-700` → `bg-surface-inset text-text-muted hover:bg-surface-button`
- `text-gray-200` → `text-text-heading`

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/month_picker.html
git commit -m "Migrate month_picker.html to semantic tokens"
```

---

### Task 9: Migrate skeleton.html

**Files:**
- Modify: `templates/partials/skeleton.html`

- [ ] **Step 1: Replace skeleton placeholders**

The existing skeleton HTML wraps 5 divs with `h-10 bg-gray-800/50 rounded-lg` inside a parent `div.animate-pulse`. Replace each inner div's `bg-gray-800/50 rounded-lg` with the `.skeleton` class, keeping `h-10` (which `.skeleton` does not provide). The parent `animate-pulse` can also be removed since `.skeleton` includes it — or keep the parent wrapper for the `space-y-3 py-2` spacing.

Example replacement for each inner div:
```html
<!-- Before -->
<div class="h-10 bg-gray-800/50 rounded-lg"></div>
<!-- After -->
<div class="h-10 skeleton"></div>
```

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/skeleton.html
git commit -m "Migrate skeleton.html to component class"
```

---

### Task 10: Migrate depth_selector.html and sort_toggle.html

**Files:**
- Modify: `templates/partials/depth_selector.html`
- Modify: `templates/partials/sort_toggle.html`

- [ ] **Step 1: Migrate depth_selector.html**

Replace:
- `text-gray-500` (label) → `text-text-faint`
- Active buttons: `bg-blue-600 text-white` → use `.chip-active` class
- Inactive buttons: `bg-gray-800 text-gray-400 hover:bg-gray-700` → use `.chip` class

- [ ] **Step 2: Migrate sort_toggle.html**

Same pattern as depth_selector:
- `text-gray-500` → `text-text-faint`
- Active: use `.chip-active`
- Inactive: use `.chip`

- [ ] **Step 3: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/depth_selector.html templates/partials/sort_toggle.html
git commit -m "Migrate depth_selector and sort_toggle to chip component classes"
```

---

### Task 11: Migrate bal_content.html

**Files:**
- Modify: `templates/partials/bal_content.html`

- [ ] **Step 1: Migrate colors**

Replace:
- `border-gray-800` → `border-border`
- `hover:bg-gray-900/50` → `hover:bg-surface-raised/50`
- `text-gray-400` → `text-text-muted` (account name)
- `text-red-400` / `text-green-400` → `text-negative` / `text-positive`
- `text-gray-500` → `text-text-faint` (empty state)

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/bal_content.html
git commit -m "Migrate bal_content.html to semantic tokens"
```

---

### Task 12: Migrate bs_content.html

**Files:**
- Modify: `templates/partials/bs_content.html`

- [ ] **Step 1: Migrate colors**

Replace:
- `text-gray-400` → `text-text-muted` (section title, account name, grand total label)
- `border-gray-800` → `border-border`
- `hover:bg-gray-900/50` → `hover:bg-surface-raised/50`
- `text-red-400` / `text-green-400` → `text-negative` / `text-positive`
- `bg-gray-800/50` → `bg-surface-total` (total row)
- `text-gray-300` → `text-text-heading` (total label)
- `text-gray-100` → `text-text` (total amount)
- `bg-blue-900/30` → `bg-surface-highlight` (grand total box)
- `border-blue-800` → `border-border-highlight`

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/bs_content.html
git commit -m "Migrate bs_content.html to semantic tokens"
```

---

### Task 13: Migrate is_content.html

**Files:**
- Modify: `templates/partials/is_content.html`

- [ ] **Step 1: Migrate colors**

Same pattern as bs_content.html:
- `text-gray-400` → `text-text-muted`
- `border-gray-800` → `border-border`
- `hover:bg-gray-900/50` → `hover:bg-surface-raised/50`
- `text-red-400` / `text-green-400` → `text-negative` / `text-positive`
- `bg-gray-800/50` → `bg-surface-total`
- `text-gray-300` → `text-text-heading`
- `text-gray-100` → `text-text`
- `bg-blue-900/30` → `bg-surface-highlight`
- `border-blue-800` → `border-border-highlight`

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/is_content.html
git commit -m "Migrate is_content.html to semantic tokens"
```

---

### Task 14: Migrate budget_content.html

**Files:**
- Modify: `templates/partials/budget_content.html`

This template has multi-way conditionals for progress bar colors. The existing theme tokens cover most cases. For progress bar fills, use the existing tokens:
- `bg-red-500` → `bg-negative` (reuses negative color for progress fill)
- `bg-green-500` → `bg-positive` (reuses positive color for progress fill)
- `bg-yellow-500` → `bg-warning`
- `bg-gray-600` → `bg-border-hover` (closest semantic match for low-revenue fill)

- [ ] **Step 1: Migrate expense section**

Replace:
- `text-gray-400` → `text-text-muted` (section title)
- `bg-gray-900 border border-gray-800` → `bg-surface-raised border border-border`
- `text-gray-200` → `text-text-heading` (account link)
- `hover:text-blue-400` → `hover:text-accent-text`
- `text-red-400` / `text-yellow-400` / `text-green-400` → `text-negative` / `text-warning-text` / `text-positive`
- `bg-gray-800` → `bg-surface-inset` (progress bar background)
- `bg-red-500` / `bg-yellow-500` / `bg-green-500` → `bg-negative` / `bg-warning` / `bg-positive`
- `text-gray-500` → `text-text-faint` (budget stats)

- [ ] **Step 2: Migrate revenue section**

Same replacements as expense section, plus:
- Revenue low percentage: `text-gray-400` → `text-text-muted`
- Revenue low progress fill: `bg-gray-600` → `bg-border-hover`

- [ ] **Step 3: Migrate empty state**

Replace `text-gray-500` → `text-text-faint`.

- [ ] **Step 4: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/budget_content.html
git commit -m "Migrate budget_content.html to semantic tokens"
```

---

### Task 15: Migrate reg_content.html

**Files:**
- Modify: `templates/partials/reg_content.html`

- [ ] **Step 1: Migrate colors**

Replace:
- `border-gray-600` → `border-border-hover` (date divider, 2x)
- `text-gray-300` → `text-text-heading` (divider label)
- `bg-gray-900 border border-gray-800` → `bg-surface-raised border border-border` (entry card)
- `text-gray-400` → `text-text-muted` (account)
- `text-gray-500` → `text-text-faint` (running balance, empty state)

- [ ] **Step 2: Rebuild, verify, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/partials/reg_content.html
git commit -m "Migrate reg_content.html to semantic tokens"
```

---

### Task 16: Migrate remaining page templates

**Files:**
- Modify: `templates/transactions.html`
- Modify: `templates/register.html`

- [ ] **Step 1: Migrate transactions.html**

Replace Go button `bg-blue-600 hover:bg-blue-700` → use `.btn` class.

- [ ] **Step 2: Migrate register.html**

Replace `text-gray-500` (empty state) → `text-text-faint`.

- [ ] **Step 3: Rebuild, verify all pages, commit**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css
git add templates/transactions.html templates/register.html
git commit -m "Migrate remaining page templates to semantic tokens"
```

---

## Chunk 4: Final Verification

### Task 17: Full verification and cleanup

- [ ] **Step 1: Grep for remaining hardcoded color classes**

Search all templates for any remaining hardcoded Tailwind color classes that should have been migrated:

```bash
grep -rn 'text-gray-\|bg-gray-\|border-gray-\|text-blue-\|bg-blue-\|border-blue-\|text-red-\|bg-red-\|text-green-\|bg-green-\|text-yellow-\|bg-yellow-\|bg-black/' templates/
```

Expected: No matches (all migrated to semantic tokens). If any remain, migrate them.

- [ ] **Step 2: Build minified CSS and check file size**

```bash
uv run --group build tailwindcss -i style.css -o static/dist.css --minify
ls -la static/dist.css
```

Expected: File exists, reasonably sized (should be much smaller than CDN).

- [ ] **Step 3: Visual spot-check all pages**

Start the dev server and check each page:
- `/` (transactions) — list view, transaction cards
- Click a transaction — detail modal
- Click edit — edit modal with form, buttons
- `/balances` — balance rows, amounts
- `/balancesheet` — sections, totals, grand total highlight
- `/income` — same as balance sheet structure
- `/budget` — progress bars, color-coded percentages
- `/register?account=expenses` — register view

Verify colors match the original appearance.

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "Fix remaining color class migrations"
```

(Skip if no fixes were needed.)
