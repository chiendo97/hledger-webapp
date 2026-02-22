"""hledger web app — Litestar + Jinja2 + HTMX."""

import asyncio
import os
from datetime import date as dt_date
from pathlib import Path

from litestar import Litestar, Request, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.datastructures import State
from litestar.response import Redirect, Template
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]
from litestar.template import TemplateConfig

import hledger
from hledger import PostingInput, Tag

JOURNAL_FILE = os.environ.get(
    "HLEDGER_FILE",
    str(Path(__file__).resolve().parent.parent / "2025.journal"),
)

TEMPLATES_DIR = str(Path(__file__).resolve().parent / "templates")
STATIC_DIR = str(Path(__file__).resolve().parent / "static")


def _month_range(month: str) -> dict[str, str]:
    """Given a 'YYYY-MM' string (or empty for current month), return month context dict."""
    if not month:
        today = dt_date.today()
        month = today.strftime("%Y-%m")
    year, mon = int(month[:4]), int(month[5:7])
    begin = f"{year}-{mon:02d}-01"
    if mon == 12:
        end = f"{year + 1}-01-01"
        next_month = f"{year + 1}-01"
    else:
        end = f"{year}-{mon + 1:02d}-01"
        next_month = f"{year}-{mon + 1:02d}"
    if mon == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year}-{mon - 1:02d}"
    return {
        "month": month,
        "begin": begin,
        "end": end,
        "prev_month": prev_month,
        "next_month": next_month,
    }


# ── Routes ──────────────────────────────────────────────────────────────


@get("/")
async def index() -> Redirect:
    return Redirect(path="/transactions")


@get("/transactions")
async def transactions(q: str = "", month: str = "") -> Template:
    mr = _month_range(month)
    return Template("transactions.html", context={"q": q, **mr})


@get("/transactions/partial")
async def transactions_partial(q: str = "", month: str = "") -> Template:
    mr = _month_range(month)
    txs = await hledger.print_json(
        JOURNAL_FILE, query=q, begin=mr["begin"], end=mr["end"]
    )
    txs.reverse()
    return Template("partials/tx_list.html", context={"txs": txs})


@get("/transactions/new")
async def new_transaction_form() -> Template:
    accts = await hledger.accounts(JOURNAL_FILE)
    return Template("partials/tx_form.html", context={"accounts": accts})


@post("/transactions/new")
async def create_transaction(request: Request[object, object, State]) -> Redirect:
    data = await request.form()
    date = str(data.get("date", ""))
    description = str(data.get("description", ""))
    postings: list[PostingInput] = []
    i = 0
    while f"account_{i}" in data:
        account = str(data.get(f"account_{i}", ""))
        amount = str(data.get(f"amount_{i}", ""))
        if account:
            postings.append(PostingInput(account=account, amount=amount))
        i += 1
    if date and description and postings:
        await hledger.add_transaction(JOURNAL_FILE, date, description, postings)
    return Redirect(path="/transactions")


@get("/transactions/{index:int}")
async def transaction_detail(index: int) -> Template:
    tx, accts = await asyncio.gather(
        hledger.get_transaction(JOURNAL_FILE, index),
        hledger.accounts(JOURNAL_FILE),
    )
    return Template("partials/tx_detail.html", context={"tx": tx, "accounts": accts})


@post("/transactions/{index:int}")
async def update_transaction(
    request: Request[object, object, State], index: int
) -> Template:
    data = await request.form()
    date = str(data.get("date", ""))
    description = str(data.get("description", ""))
    tags: list[Tag] = []
    i = 0
    while f"tag_key_{i}" in data:
        key = str(data.get(f"tag_key_{i}", ""))
        value = str(data.get(f"tag_value_{i}", ""))
        if key or value:
            tags.append(Tag(key=key, value=value))
        i += 1
    postings: list[PostingInput] = []
    i = 0
    while f"account_{i}" in data:
        account = str(data.get(f"account_{i}", ""))
        amount = str(data.get(f"amount_{i}", ""))
        balance_assertion = str(data.get(f"balance_assertion_{i}", ""))
        if account:
            postings.append(
                PostingInput(
                    account=account, amount=amount, balance_assertion=balance_assertion
                )
            )
        i += 1
    if date and description and postings:
        await hledger.update_transaction(
            JOURNAL_FILE, index, date, description, tags, postings
        )
    tx, accts = await asyncio.gather(
        hledger.get_transaction(JOURNAL_FILE, index),
        hledger.accounts(JOURNAL_FILE),
    )
    return Template("partials/tx_detail.html", context={"tx": tx, "accounts": accts})


@get("/balances")
async def balances(
    q: str = "", depth: int = 2, month: str = "", sort: str = ""
) -> Template:
    return Template(
        "balances.html",
        context={"q": q, "depth": depth, "month": month, "sort": sort},
    )


@get("/balances/partial")
async def balances_partial(
    q: str = "", depth: int = 2, month: str = "", sort: str = ""
) -> Template:
    rows = await hledger.balances(JOURNAL_FILE, query=q, depth=depth)
    if sort == "amount":
        rows.sort(key=lambda r: r.abs_total, reverse=True)
    return Template(
        "partials/bal_content.html",
        context={"rows": rows, "month": month},
    )


@get("/incomestatement")
async def incomestatement(
    depth: int = 2, month: str = "", sort: str = ""
) -> Template:
    mr = _month_range(month)
    return Template(
        "income.html", context={"depth": depth, "sort": sort, **mr}
    )


@get("/incomestatement/partial")
async def incomestatement_partial(
    depth: int = 2, month: str = "", sort: str = ""
) -> Template:
    mr = _month_range(month)
    report = await hledger.income_statement(
        JOURNAL_FILE, depth=depth, begin=mr["begin"], end=mr["end"]
    )
    if sort == "amount":
        for sub in report.subreports:
            sub.rows.sort(key=lambda r: r.abs_total, reverse=True)
    return Template(
        "partials/is_content.html", context={"report": report, "month": month}
    )


@get("/balancesheet")
async def balancesheet(
    depth: int = 2, month: str = "", sort: str = ""
) -> Template:
    mr = _month_range(month)
    return Template(
        "balancesheet.html",
        context={"depth": depth, "sort": sort, **mr},
    )


@get("/balancesheet/partial")
async def balancesheet_partial(
    depth: int = 2, month: str = "", sort: str = ""
) -> Template:
    mr = _month_range(month)
    report = await hledger.balance_sheet(
        JOURNAL_FILE, depth=depth, end=mr["end"]
    )
    if sort == "amount":
        for sub in report.subreports:
            sub.rows.sort(key=lambda r: r.abs_total, reverse=True)
    return Template(
        "partials/bs_content.html",
        context={"report": report, "month": month},
    )


@get("/register")
async def register_view(account: str = "", month: str = "") -> Template:
    accts = await hledger.accounts(JOURNAL_FILE)
    return Template(
        "register.html",
        context={"account": account, "accounts": accts, "month": month},
    )


@get("/register/partial")
async def register_partial(account: str = "") -> Template:
    rows = await hledger.register(JOURNAL_FILE, account=account)
    return Template(
        "partials/reg_content.html",
        context={"rows": rows, "account": account},
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
        balances_partial,
        incomestatement,
        incomestatement_partial,
        balancesheet,
        balancesheet_partial,
        register_view,
        register_partial,
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
