"""hledger web app — Litestar + Jinja2 + HTMX."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from litestar import Litestar, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Redirect, Template
from litestar.static_files import create_static_files_router
from litestar.template import TemplateConfig

import hledger

JOURNAL_FILE = os.environ.get(
    "HLEDGER_FILE",
    str(Path(__file__).resolve().parent.parent / "2025.journal"),
)

TEMPLATES_DIR = str(Path(__file__).resolve().parent / "templates")
STATIC_DIR = str(Path(__file__).resolve().parent / "static")


# ── Routes ──────────────────────────────────────────────────────────────


@get("/")
async def index() -> Redirect:
    return Redirect(path="/transactions")


@get("/transactions")
async def transactions(
    q: str = "",
    begin: str = "",
    end: str = "",
) -> Template:
    txs = await hledger.print_json(JOURNAL_FILE, query=q, begin=begin, end=end)
    txs.reverse()  # newest first
    is_htmx = False  # handled via header in middleware if needed
    return Template(
        "transactions.html",
        context={"txs": txs, "q": q, "begin": begin, "end": end},
    )


@get("/transactions/partial")
async def transactions_partial(
    q: str = "",
    begin: str = "",
    end: str = "",
) -> Template:
    txs = await hledger.print_json(JOURNAL_FILE, query=q, begin=begin, end=end)
    txs.reverse()
    return Template(
        "partials/tx_list.html",
        context={"txs": txs},
    )


@get("/transactions/new")
async def new_transaction_form() -> Template:
    accts = await hledger.accounts(JOURNAL_FILE)
    return Template("partials/tx_form.html", context={"accounts": accts})


@post("/transactions/new")
async def create_transaction(
    data: dict[str, str],
) -> Redirect:
    date = data.get("date", "")
    description = data.get("description", "")
    postings = []
    i = 0
    while f"account_{i}" in data:
        account = data[f"account_{i}"]
        amount = data.get(f"amount_{i}", "")
        if account:
            postings.append({"account": account, "amount": amount})
        i += 1
    if date and description and postings:
        await hledger.add_transaction(JOURNAL_FILE, date, description, postings)
    return Redirect(path="/transactions")


@get("/transactions/{index:int}")
async def transaction_detail(index: int) -> Template:
    tx = await hledger.get_transaction(JOURNAL_FILE, index)
    accts = await hledger.accounts(JOURNAL_FILE)
    return Template("partials/tx_detail.html", context={"tx": tx, "accounts": accts})


@post("/transactions/{index:int}")
async def update_transaction(index: int, data: dict[str, str]) -> Template:
    date = data.get("date", "")
    description = data.get("description", "")
    tags = []
    i = 0
    while f"tag_key_{i}" in data:
        key = data[f"tag_key_{i}"]
        value = data.get(f"tag_value_{i}", "")
        if key or value:
            tags.append({"key": key, "value": value})
        i += 1
    postings = []
    i = 0
    while f"account_{i}" in data:
        account = data[f"account_{i}"]
        amount = data.get(f"amount_{i}", "")
        if account:
            postings.append({"account": account, "amount": amount})
        i += 1
    if date and description and postings:
        await hledger.update_transaction(JOURNAL_FILE, index, date, description, tags, postings)
    tx = await hledger.get_transaction(JOURNAL_FILE, index)
    accts = await hledger.accounts(JOURNAL_FILE)
    return Template("partials/tx_detail.html", context={"tx": tx, "accounts": accts})


@get("/balances")
async def balances(q: str = "", depth: int = 2) -> Template:
    rows = await hledger.balances(JOURNAL_FILE, query=q, depth=depth)
    return Template("balances.html", context={"rows": rows, "q": q, "depth": depth})


@get("/incomestatement")
async def incomestatement(depth: int = 2) -> Template:
    report = await hledger.income_statement(JOURNAL_FILE, depth=depth)
    return Template("income.html", context={"report": report, "depth": depth})


@get("/balancesheet")
async def balancesheet(depth: int = 2) -> Template:
    report = await hledger.balance_sheet(JOURNAL_FILE, depth=depth)
    return Template("balancesheet.html", context={"report": report, "depth": depth})


@get("/register")
async def register_view(account: str = "") -> Template:
    accts = await hledger.accounts(JOURNAL_FILE)
    rows: list = []
    if account:
        rows = await hledger.register(JOURNAL_FILE, account)
    return Template(
        "register.html",
        context={"rows": rows, "account": account, "accounts": accts},
    )


# ── App ─────────────────────────────────────────────────────────────────

app = Litestar(
    route_handlers=[
        index,
        transactions,
        transactions_partial,
        new_transaction_form,
        create_transaction,
        transaction_detail,
        update_transaction,
        balances,
        incomestatement,
        balancesheet,
        register_view,
        create_static_files_router(path="/static", directories=[STATIC_DIR]),
    ],
    template_config=TemplateConfig(
        directory=Path(TEMPLATES_DIR),
        engine=JinjaTemplateEngine,
    ),
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
