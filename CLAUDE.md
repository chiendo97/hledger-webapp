# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A web frontend for [hledger](https://hledger.org) plain-text accounting, built with **Litestar** (async Python), **Jinja2** templates, and **HTMX** for interactivity. The app shells out to the `hledger` CLI via async subprocesses and parses its JSON output.

## Commands

```bash
# Run dev server (auto-reload)
uv run python app.py
# or: uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Requires `hledger` CLI on PATH. Journal file defaults to `../2025.journal`, override with `HLEDGER_FILE` env var.

## Architecture

- **`app.py`** — Litestar app with all route handlers. Entry point (`app:app`). Routes serve full pages or HTMX partials.
- **`hledger.py`** — Async wrapper around hledger CLI. All hledger interaction goes through `_run()` which calls `asyncio.create_subprocess_exec`. Public functions (`print_json`, `balances`, `income_statement`, `balance_sheet`, `register`, `accounts`, `add_transaction`, `update_transaction`) return parsed/enriched Python dicts ready for templates.
- **`templates/`** — Jinja2 templates. `base.html` is the layout. `partials/` contains HTMX-swappable fragments (tx_list, tx_form, tx_detail, depth_selector).
- **`static/`** — Static assets served at `/static`.

## Key patterns

- Transaction amounts from hledger JSON are formatted via `_fmt_amount`/`_fmt_amounts` into human-readable strings and injected as `_amount` fields on postings.
- Transaction comments are parsed into `{key, value}` tag dicts via `parse_comment_tags` and attached as `_tags`.
- `update_transaction` rewrites journal files by line-range replacement using `tsourcepos` from hledger's JSON output.
