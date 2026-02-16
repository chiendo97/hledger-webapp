# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A web frontend for [hledger](https://hledger.org) plain-text accounting, built with **Litestar** (async Python), **Jinja2** templates, and **HTMX** for interactivity. The app shells out to the `hledger` CLI via async subprocesses and parses its JSON output. The UI is a dark-themed mobile-first PWA using Tailwind CSS (CDN) with a bottom navigation bar and `hx-boost` for SPA-style navigation.

## Commands

```bash
# Run dev server (auto-reload on port 8000)
uv run python app.py

# Run with Docker/Podman
podman compose up --build -d

# Lint & type check
uv run ruff check .
uv run basedpyright
```

Requires `hledger` CLI on PATH and Python 3.12+. Journal file defaults to `../2025.journal`, override with `HLEDGER_FILE` env var. The journal can use hledger `include` directives to combine multiple files.

## Architecture

- **`app.py`** — Litestar app with all route handlers. Entry point is `app:app`. Routes serve full pages or HTMX partials. Each route calls `hledger.py` functions and passes results to Jinja2 templates.
- **`hledger.py`** — Async wrapper around hledger CLI. All hledger interaction goes through `_run()` which calls `asyncio.create_subprocess_exec`. Public functions return Pydantic models (`Transaction`, `BalanceRow`, `CompoundReport`, etc.) ready for templates. hledger JSON is parsed via Pydantic `TypeAdapter`s, not `json.loads()`.
- **`templates/`** — Jinja2 templates. `base.html` is the layout (includes Tailwind CDN, HTMX, bottom nav). `partials/` contains HTMX-swappable fragments. Full page templates extend `base.html`.
- **`static/style.css`** — Custom CSS overrides (single file).
- **`static/manifest.json`** — PWA manifest for standalone (home screen) mode.
- **`Dockerfile`** — Containerized deployment. Runs as non-root `appuser` (UID/GID 1000:1000).
- **`.github/workflows/docker.yml`** — CI/CD: builds and pushes Docker image to `ghcr.io/chiendo97/hledger-webapp` on push to `master`.

## Key patterns

- **SPA navigation**: `hx-boost="true"` on `<body>` intercepts all link clicks and form submissions, making them AJAX requests that swap the `<body>` without full page reloads.
- **Caching**: `_print_all()` caches the full transaction list (30s TTL) and `accounts()` caches the account list (60s TTL). Caches are invalidated on write operations (`add_transaction`, `update_transaction`). This makes transaction detail loads near-instant after viewing the list.
- **Parallel async calls**: Independent hledger CLI calls (e.g. `get_transaction` + `accounts`) run in parallel via `asyncio.gather`.
- **Amount formatting**: hledger JSON amounts are parsed into `Amount` Pydantic models and formatted via `_fmt_amount`/`_fmt_amounts` into display strings stored in `Posting.amount_display`.
- **VND currency handling**: VND amounts need special treatment because hledger interprets `.` ambiguously (decimal vs thousands separator). `_vnd_value()` resolves this, and `_normalize_amount()` ensures VND amounts have a trailing dot when writing back to journals.
- **Transaction editing**: `update_transaction` rewrites journal files by replacing line ranges identified by `tsourcepos` (source positions from hledger's JSON). This is a direct text replacement on the journal file.
- **Comment tags**: Transaction/posting comments are parsed into `Tag(key, value)` objects via `parse_comment_tags` and serialized back with `format_comment_tags`.
- **HTMX interactions**: Transaction detail/edit is rendered as a modal via HTMX (`hx-get` loads into `#modal` div). Form submissions use `hx-post` with `hx-target`/`hx-swap` for partial page updates.
- **iOS PWA support**: `viewport-fit=cover` with `env(safe-area-inset-*)` CSS for proper rendering in standalone mode (respects notch and home indicator).
- **No test suite**: There are currently no tests. The app is validated by running it against a real journal file.
