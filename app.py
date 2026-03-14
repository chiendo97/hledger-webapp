"""hledger web app — Litestar + Jinja2 + HTMX."""

import hashlib
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

# Fixed palette — maximally distinct colors readable on dark backgrounds
_ACCOUNT_COLORS = [
    "#e06c75",  # red
    "#61afef",  # blue
    "#98c379",  # green
    "#e5c07b",  # yellow
    "#c678dd",  # purple
    "#56b6c2",  # cyan
    "#d19a66",  # orange
    "#be5046",  # rust
    "#7ec8e3",  # sky
    "#c3e88d",  # lime
    "#f78c6c",  # coral
    "#89ddff",  # ice blue
    "#ffcb6b",  # gold
    "#f07178",  # salmon
    "#82aaff",  # periwinkle
    "#c792ea",  # lavender
    "#4ec9b0",  # mint
    "#d7ba7d",  # tan
    "#b392f0",  # violet
    "#85e89d",  # pastel green
    "#ffab70",  # peach
    "#79b8ff",  # cornflower
    "#e2c08d",  # wheat
    "#ff7b72",  # light red
]


def _account_color(account: str) -> str:
    """Deterministic color for an account name."""
    h = int(hashlib.md5(account.encode()).hexdigest(), 16)  # noqa: S324
    return _ACCOUNT_COLORS[h % len(_ACCOUNT_COLORS)]


def _account_short(account: str) -> str:
    """Extract a human-readable short label from an account path.

    'expense:drink:coffee' → 'Coffee'
    'asset:vietinbank:checking' → 'Checking'
    'revenue:salary' → 'Salary'
    """
    leaf = account.rsplit(":", 1)[-1] if ":" in account else account
    return leaf.replace("_", " ").title()


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


def _sort_rows_by_amount(rows: list[hledger.BalanceRow]) -> list[hledger.BalanceRow]:
    """Sort rows by amount within each top-level account group.

    Keeps top-level accounts in their original order. Only sorts
    child accounts within each top-level parent group.
    If there are no top-level (depth 0) rows (e.g. IS/BS subreports),
    sorts all rows together.
    """
    min_depth = min((r.depth for r in rows), default=0)

    # No grouping needed — all rows are at the same level (e.g. IS/BS subreports)
    if all(r.depth == min_depth for r in rows):
        return sorted(rows, key=lambda r: r.abs_total, reverse=True)

    result: list[hledger.BalanceRow] = []
    group: list[hledger.BalanceRow] = []
    parent: hledger.BalanceRow | None = None

    def flush() -> None:
        if parent is not None:
            result.append(parent)
            group.sort(key=lambda r: r.abs_total, reverse=True)
            result.extend(group)

    for row in rows:
        if row.depth == min_depth:
            flush()
            parent = row
            group = []
        else:
            group.append(row)
    flush()
    return result


# ── Routes ──────────────────────────────────────────────────────────────


@get("/")
async def index() -> Redirect:
    return Redirect(path="/transactions")


@get("/transactions")
async def transactions(q: str = "", month: str = "", source: str = "2025.journal") -> Template:
    mr = _month_range(month)
    sources = await hledger.sources(JOURNAL_FILE)
    return Template("transactions.html", context={"q": q, "source": source, "sources": sources, **mr})


@get("/transactions/partial")
async def transactions_partial(q: str = "", month: str = "", source: str = "2025.journal") -> Template:
    mr = _month_range(month)
    txs = await hledger.print_json(
        JOURNAL_FILE, query=q, begin=mr["begin"], end=mr["end"]
    )
    if source:
        txs = [
            tx for tx in txs
            if tx.tsourcepos and Path(tx.tsourcepos[0].sourceName).name == source
        ]
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


@post("/transactions/{index:int}")
async def update_transaction(
    request: Request[object, object, State], index: int
) -> None:
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
            sub.rows = _sort_rows_by_amount(sub.rows)
    return Template(
        "partials/report_content.html", context={"report": report, "month": month}
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
            sub.rows = _sort_rows_by_amount(sub.rows)
    return Template(
        "partials/report_content.html",
        context={"report": report, "month": month},
    )


@get("/budget")
async def budget_view(month: str = "") -> Template:
    mr = _month_range(month)
    return Template("budget.html", context={**mr})


@get("/budget/partial")
async def budget_partial(month: str = "") -> Template:
    mr = _month_range(month)
    rows = await hledger.budget(JOURNAL_FILE, begin=mr["begin"], end=mr["end"])
    return Template("partials/budget_content.html", context={"rows": rows, "month": month})


@get("/register")
async def register_view(account: str = "", month: str = "") -> Template:
    accts = await hledger.accounts(JOURNAL_FILE)
    return Template(
        "register.html",
        context={"account": account, "accounts": accts, "month": month},
    )


@get("/register/partial")
async def register_partial(account: str = "") -> Template:
    txs = await hledger.print_json(JOURNAL_FILE, query=account)
    txs.reverse()
    return Template("partials/tx_list.html", context={"txs": txs})


# ── App ─────────────────────────────────────────────────────────────────

app = Litestar(
    debug=os.environ.get("DEBUG", "").lower() == "true",
    route_handlers=[
        index,
        transactions,
        transactions_partial,
        new_transaction_form,
        create_transaction,
        update_transaction,
        incomestatement,
        incomestatement_partial,
        balancesheet,
        balancesheet_partial,
        budget_view,
        budget_partial,
        register_view,
        register_partial,
        create_static_files_router(path="/static", directories=[STATIC_DIR]),
    ],
    template_config=TemplateConfig(
        directory=Path(TEMPLATES_DIR),
        engine=JinjaTemplateEngine,
    ),
)

# Register Jinja2 globals
engine = app.template_engine  # pyright: ignore[reportAny]
engine.engine.globals["account_color"] = _account_color  # pyright: ignore[reportAny, reportUnknownMemberType]
engine.engine.globals["account_short"] = _account_short  # pyright: ignore[reportAny, reportUnknownMemberType]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
