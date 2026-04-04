"""hledger CLI wrapper — async subprocess calls returning parsed JSON."""

import asyncio
import time
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter

# ── Models (public) ────────────────────────────────────────────────────


class Quantity(BaseModel):
    decimalMantissa: int
    decimalPlaces: int
    floatingPoint: float


class Amount(BaseModel):
    acommodity: str
    aquantity: Quantity


class SourcePos(BaseModel):
    sourceLine: int
    sourceColumn: int = 0
    sourceName: str = ""


class Tag(BaseModel):
    key: str = ""
    value: str = ""


class PostingInput(BaseModel):
    account: str
    amount: str = ""
    balance_assertion: str = ""


class BalanceAssertion(BaseModel):
    baamount: Amount


class Posting(BaseModel):
    paccount: str
    pamount: list[Amount] = Field(default_factory=list)
    pbalanceassertion: BalanceAssertion | None = None
    pcomment: str = ""
    amount_display: str = ""
    balance_assertion_display: str = ""
    tags: list[Tag] = Field(default_factory=list)


class Transaction(BaseModel):
    tindex: int = 0
    tdate: str = ""
    tdate2: str | None = None
    tdescription: str = ""
    tcomment: str = ""
    tpostings: list[Posting] = Field(default_factory=list)
    tsourcepos: list[SourcePos] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)

    @property
    def view_json(self) -> str:
        import hashlib
        import json

        colors = [
            "#e06c75", "#61afef", "#98c379", "#e5c07b", "#c678dd", "#56b6c2",
            "#d19a66", "#be5046", "#7ec8e3", "#c3e88d", "#f78c6c", "#89ddff",
            "#ffcb6b", "#f07178", "#82aaff", "#c792ea", "#4ec9b0", "#d7ba7d",
            "#b392f0", "#85e89d", "#ffab70", "#79b8ff", "#e2c08d", "#ff7b72",
        ]

        def _color(account: str) -> str:
            h = int(hashlib.md5(account.encode()).hexdigest(), 16)
            return colors[h % len(colors)]

        return json.dumps(
            {
                "tindex": self.tindex,
                "tdate": self.tdate,
                "tdescription": self.tdescription,
                "tags": [{"key": t.key, "value": t.value} for t in self.tags],
                "tpostings": [
                    {
                        "paccount": p.paccount,
                        "amount_display": p.amount_display,
                        "balance_assertion_display": p.balance_assertion_display,
                        "account_color": _color(p.paccount),
                        "negative": (
                            p.pamount[0].aquantity.floatingPoint < 0
                            if p.pamount
                            else False
                        ),
                        "tags": [
                            {"key": t.key, "value": t.value} for t in p.tags
                        ],
                    }
                    for p in self.tpostings
                ],
            }
        )


class BalanceRow(BaseModel):
    name: str
    depth: int
    amounts: str
    amount_items: list[str] = Field(default_factory=list)
    abs_total: int = 0


class RegisterRow(BaseModel):
    date: str
    description: str
    account: str
    amount: str
    running: str


class SubReport(BaseModel):
    title: str
    rows: list[BalanceRow] = Field(default_factory=list)
    total: str = ""
    total_items: list[str] = Field(default_factory=list)


class CompoundReport(BaseModel):
    title: str
    subreports: list[SubReport] = Field(default_factory=list)
    grand_total: str = ""
    grand_total_items: list[str] = Field(default_factory=list)


class BudgetRow(BaseModel):
    name: str
    actual: str
    budget: str
    percent: int = 0
    category: str = "expense"  # "income", "expense", "saving"


class AvgRow(BaseModel):
    name: str
    avg_amount: str  # Formatted average per month
    total: str  # Formatted year-to-date total
    percent: int = 0  # Percentage of section total (for proportion bars)
    avg_value: int = 0  # Raw average value (for sorting)


class AvgMonthlyReport(BaseModel):
    year: int
    months_elapsed: int
    revenue_rows: list[AvgRow] = Field(default_factory=list)
    expense_rows: list[AvgRow] = Field(default_factory=list)
    revenue_total: str = ""
    expense_total: str = ""
    expense_pct_of_income: int = 0  # Expenses as % of revenue
    expense_trend: int = 0  # Change vs prior year in % (positive = spending more)
    revenue_trend: int = 0  # Change vs prior year in % (positive = earning more)


# ── Raw JSON models (internal parsing) ─────────────────────────────────


class _RegPosting(BaseModel):
    paccount: str
    pamount: list[Amount] = Field(default_factory=list)


class _PrRow(BaseModel):
    prrName: str | list[object] = ""
    prrAmounts: list[list[Amount]] = Field(default_factory=list)


class _PrTable(BaseModel):
    prRows: list[_PrRow] = Field(default_factory=list)
    prTotals: _PrRow = Field(default_factory=_PrRow)


class _CompoundReportRaw(BaseModel):
    cbrTitle: str = ""
    cbrSubreports: list[tuple[str, _PrTable, bool]] = Field(default_factory=list)
    cbrTotals: _PrRow = Field(default_factory=_PrRow)


# ── Type adapters ──────────────────────────────────────────────────────

_tx_adapter = TypeAdapter(list[Transaction])
_reg_adapter = TypeAdapter(list[tuple[str, str | None, str, _RegPosting, list[Amount]]])
_compound_adapter = TypeAdapter(_CompoundReportRaw)


# ── Internal helpers ───────────────────────────────────────────────────


async def _run(args: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"hledger error: {stderr.decode()}")
    return stdout.decode()


def _vnd_value(q: Quantity) -> int:
    """Extract the true integer value for VND amounts.

    hledger may parse '.' as decimal (e.g. 133,824,966.0 → mantissa=1338249660, places=1)
    or as thousands separator (e.g. 139.400 → mantissa=139400, places=3).
    If the decimal digits are all zeros, it's a true decimal → divide out.
    Otherwise the '.' was a thousands separator → mantissa is the real value.
    """
    mantissa = q.decimalMantissa
    places = q.decimalPlaces
    if places == 0:
        return mantissa
    divisor: int = pow(10, places)  # pyright: ignore[reportAny]
    if mantissa % divisor == 0:
        return mantissa // divisor
    return mantissa


def _fmt_amount(amt: Amount) -> str:
    """Format an hledger amount to a human-readable string."""
    commodity = amt.acommodity
    q = amt.aquantity
    places = q.decimalPlaces
    if commodity == "vnd":
        formatted = f"{_vnd_value(q):,}"
    elif places == 0:
        formatted = f"{int(q.floatingPoint):,}"
    else:
        formatted = f"{q.floatingPoint:,.{places}f}"
    return f"{formatted} {commodity}"


def _merge_amounts(amounts: list[Amount]) -> list[Amount]:
    """Merge amounts with the same commodity by summing their quantities."""
    by_commodity: dict[str, Amount] = {}
    vnd_sums: dict[str, int] = {}
    for a in amounts:
        c = a.acommodity
        if c in by_commodity:
            existing = by_commodity[c]
            if c == "vnd":
                vnd_sums[c] += _vnd_value(a.aquantity)
            else:
                eq = existing.aquantity
                existing.aquantity = Quantity(
                    floatingPoint=eq.floatingPoint + a.aquantity.floatingPoint,
                    decimalMantissa=eq.decimalMantissa,
                    decimalPlaces=max(eq.decimalPlaces, a.aquantity.decimalPlaces),
                )
        else:
            by_commodity[c] = Amount(
                acommodity=c,
                aquantity=Quantity(
                    floatingPoint=a.aquantity.floatingPoint,
                    decimalMantissa=a.aquantity.decimalMantissa,
                    decimalPlaces=a.aquantity.decimalPlaces,
                ),
            )
            if c == "vnd":
                vnd_sums[c] = _vnd_value(a.aquantity)
    for c, entry in by_commodity.items():
        if c == "vnd" and c in vnd_sums:
            entry.aquantity = Quantity(
                decimalMantissa=vnd_sums[c],
                decimalPlaces=0,
                floatingPoint=float(vnd_sums[c]),
            )
    return list(by_commodity.values())


def _fmt_amounts(amounts: list[Amount]) -> str:
    return ", ".join(_fmt_amount(a) for a in _merge_amounts(amounts))


def _abs_total(amounts: list[Amount]) -> int:
    """Calculate total absolute value for sorting."""
    if not amounts:
        return 0
    return sum(
        abs(
            _vnd_value(a.aquantity)
            if a.acommodity == "vnd"
            else a.aquantity.decimalMantissa
        )
        for a in amounts
    )


def _parse_budget_amount(s: str) -> int:
    """Parse a budget CSV amount string, extracting the VND value.

    Handles multi-currency strings like '0.5c, 2,539.8 sgd, 107,860,080.0 vnd'
    by finding the VND component.
    """
    s = s.strip()
    if not s or s == "0":
        return 0
    # Multi-currency: find the VND component
    if " vnd" in s:
        for part in s.split(", "):
            part = part.strip()
            if part.endswith(" vnd"):
                num_str = part[: -len(" vnd")].replace(",", "")
                return int(float(num_str))
    # Single amount without commodity
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return 0


def _normalize_amount(amount: str) -> str:
    """Ensure VND amounts have trailing dot (e.g. '139,400. vnd') for hledger."""
    if amount.endswith(" vnd") and not amount.endswith(". vnd"):
        amount = amount.replace(" vnd", ". vnd")
    return amount


def _build_tree_rows(
    flat_rows: list[tuple[str, list[Amount]]], depth: int
) -> list[BalanceRow]:
    """Build hierarchical tree rows from flat leaf rows.

    Takes flat (name, amounts) pairs from hledger --flat output and creates
    rows at every depth level up to `depth`, computing parent totals by
    summing their children's amounts.
    """
    from collections import defaultdict

    # Collect raw amounts at each prefix level
    amounts_by_name: dict[str, list[Amount]] = defaultdict(list)
    for name, amounts in flat_rows:
        # Truncate to requested depth
        parts = name.split(":")
        if depth and len(parts) > depth:
            name = ":".join(parts[:depth])
        # Add amounts to this account and all ancestors
        segments = name.split(":")
        for i in range(1, len(segments) + 1):
            prefix = ":".join(segments[:i])
            amounts_by_name[prefix].extend(amounts)

    # Build BalanceRow for each prefix
    rows: list[BalanceRow] = []
    for name, raw_amounts in sorted(amounts_by_name.items()):
        merged = _merge_amounts(raw_amounts)
        rows.append(
            BalanceRow(
                name=name,
                depth=name.count(":"),
                amounts=_fmt_amounts(merged) if merged else "",
                amount_items=(
                    [_fmt_amount(a) for a in merged] if merged else []
                ),
                abs_total=_abs_total(merged),
            )
        )
    return rows


def _parse_compound_report(
    raw: _CompoundReportRaw, depth: int = 0
) -> CompoundReport:
    """Parse hledger compound balance report (is/bs).

    Expects --flat output. Builds tree rows with parent totals computed
    by summing children.
    """
    subreports: list[SubReport] = []
    for sub_title, sub_table, _increase_is_normal in raw.cbrSubreports:
        flat_rows: list[tuple[str, list[Amount]]] = []
        for row in sub_table.prRows:
            amounts = row.prrAmounts[0] if row.prrAmounts else []
            if isinstance(row.prrName, list):
                print(f"Warning: unexpected prrName list: {row.prrName}")
            name = row.prrName if isinstance(row.prrName, str) else ""
            flat_rows.append((name, amounts))
        rows = _build_tree_rows(flat_rows, depth)
        totals = sub_table.prTotals
        total_amounts = totals.prrAmounts[0] if totals.prrAmounts else []
        subreports.append(
            SubReport(
                title=sub_title,
                rows=rows,
                total=_fmt_amounts(total_amounts) if total_amounts else "",
                total_items=(
                    [_fmt_amount(a) for a in _merge_amounts(total_amounts)]
                    if total_amounts
                    else []
                ),
            )
        )
    grand_amounts_list = raw.cbrTotals.prrAmounts
    grand_amounts = grand_amounts_list[0] if grand_amounts_list else []
    return CompoundReport(
        title=raw.cbrTitle,
        subreports=subreports,
        grand_total=_fmt_amounts(grand_amounts) if grand_amounts else "",
        grand_total_items=(
            [_fmt_amount(a) for a in _merge_amounts(grand_amounts)]
            if grand_amounts
            else []
        ),
    )


# ── Public API ──────────────────────────────────────────────────────────


def parse_comment_tags(comment: str) -> list[Tag]:
    """Parse a hledger comment string into a list of Tag objects.

    Comments come as '\\nkey:value\\nkey2:value2\\n'.
    """
    tags: list[Tag] = []
    for line in comment.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            tags.append(Tag(key=key.strip(), value=value.strip()))
        else:
            tags.append(Tag(key="", value=line))
    return tags


def format_comment_tags(tags: list[Tag]) -> str:
    """Convert Tag objects back to hledger comment lines."""
    parts: list[str] = []
    for tag in tags:
        key = tag.key.strip()
        value = tag.value.strip()
        if key and value:
            parts.append(f"{key}:{value}")
        elif key:
            parts.append(key)
        elif value:
            parts.append(value)
    return "\n".join(parts)


_print_cache: tuple[float, str, list[Transaction]] = (0.0, "", [])
_PRINT_TTL = 30  # seconds


def _invalidate_cache() -> None:
    global _print_cache, _accounts_cache
    _print_cache = (0.0, "", [])
    _accounts_cache = (0.0, [])


async def _print_all(file: str) -> list[Transaction]:
    """Fetch all transactions, with short TTL cache."""
    global _print_cache
    ts, cached_file, cached_txs = _print_cache
    if cached_txs and cached_file == file and time.monotonic() - ts < _PRINT_TTL:
        return cached_txs
    args = ["hledger", "-f", file, "print", "-O", "json"]
    raw_str = await _run(args)
    txs = _tx_adapter.validate_json(raw_str)
    for tx in txs:
        tx.tags = parse_comment_tags(tx.tcomment)
        for p in tx.tpostings:
            p.amount_display = _fmt_amounts(p.pamount)
            if p.pbalanceassertion:
                p.balance_assertion_display = _fmt_amount(p.pbalanceassertion.baamount)
            p.tags = parse_comment_tags(p.pcomment)
    _print_cache = (time.monotonic(), file, txs)
    return txs


async def print_json(
    file: str,
    query: str = "",
    begin: str = "",
    end: str = "",
) -> list[Transaction]:
    if not query and not begin and not end:
        return list(await _print_all(file))
    args = ["hledger", "-f", file, "print", "-O", "json"]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    if query:
        args.append(query)
    raw_str = await _run(args)
    txs = _tx_adapter.validate_json(raw_str)
    for tx in txs:
        tx.tags = parse_comment_tags(tx.tcomment)
        for p in tx.tpostings:
            p.amount_display = _fmt_amounts(p.pamount)
            if p.pbalanceassertion:
                p.balance_assertion_display = _fmt_amount(p.pbalanceassertion.baamount)
            p.tags = parse_comment_tags(p.pcomment)
    return txs



async def income_statement(
    file: str,
    depth: int = 0,
    begin: str = "",
    end: str = "",
) -> CompoundReport:
    args = ["hledger", "-f", file, "is", "-O", "json", "--flat"]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    raw_str = await _run(args)
    raw = _compound_adapter.validate_json(raw_str)
    return _parse_compound_report(raw, depth)


async def balance_sheet(
    file: str,
    depth: int = 0,
    begin: str = "",
    end: str = "",
) -> CompoundReport:
    args = ["hledger", "-f", file, "bs", "-O", "json", "--flat"]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    raw_str = await _run(args)
    raw = _compound_adapter.validate_json(raw_str)
    return _parse_compound_report(raw, depth)


async def register(
    file: str,
    account: str,
    begin: str = "",
    end: str = "",
) -> list[RegisterRow]:
    args = ["hledger", "-f", file, "reg", account, "-O", "json"]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    raw_str = await _run(args)
    entries = _reg_adapter.validate_json(raw_str)
    return [
        RegisterRow(
            date=date,
            description=desc,
            account=posting.paccount,
            amount=_fmt_amounts(posting.pamount),
            running=_fmt_amounts(running),
        )
        for date, _date2, desc, posting, running in entries
    ]


async def add_transaction(
    file: str,
    date: str,
    description: str,
    postings: list[PostingInput],
) -> None:
    lines = [f"\n{date} {description}"]
    for p in postings:
        if p.amount:
            amount = _normalize_amount(p.amount)
            lines.append(f"    {p.account}    {amount}")
        else:
            lines.append(f"    {p.account}")
    lines.append("")
    async with asyncio.Lock():
        def _append() -> None:
            with Path(file).open("a") as f:
                f.write("\n".join(lines))

        await asyncio.to_thread(_append)
    _invalidate_cache()


async def get_transaction(file: str, index: int) -> Transaction:
    txs = await _print_all(file)
    for tx in txs:
        if tx.tindex == index:
            return tx
    raise ValueError(f"Transaction {index} not found")


async def update_transaction(
    file: str,
    index: int,
    date: str,
    description: str,
    tags: list[Tag],
    postings: list[PostingInput],
) -> None:
    tx = await get_transaction(file, index)
    start_line = tx.tsourcepos[0].sourceLine
    end_line = tx.tsourcepos[1].sourceLine

    lines = [f"{date} {description}"]
    comment = format_comment_tags(tags)
    if comment:
        lines.extend(f"    ; {tag_line}" for tag_line in comment.splitlines())
    for p in postings:
        if p.amount:
            amount = _normalize_amount(p.amount)
            if p.balance_assertion:
                ba = _normalize_amount(p.balance_assertion)
                lines.append(f"    {p.account}    {amount} = {ba}")
            else:
                lines.append(f"    {p.account}    {amount}")
        else:
            lines.append(f"    {p.account}")

    # Use the actual source file from tsourcepos (may differ from main journal
    # when the transaction lives in an included file like 2025.card.journal).
    source_file = tx.tsourcepos[0].sourceName
    path = Path(source_file) if source_file else Path(file)
    file_lines = path.read_text().splitlines(keepends=True)
    new_block = "\n".join(lines) + "\n"
    file_lines[start_line - 1 : end_line - 1] = [new_block]
    _ = path.write_text("".join(file_lines))
    _invalidate_cache()


async def budget(
    file: str,
    begin: str = "",
    end: str = "",
) -> list[BudgetRow]:
    import csv as _csv
    import io as _io

    args = ["hledger", "-f", file, "bal", "--budget", "-O", "csv"]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    raw_str = await _run(args)
    reader = _csv.reader(_io.StringIO(raw_str))
    next(reader)  # skip header
    rows: list[BudgetRow] = []
    for csv_row in reader:
        if len(csv_row) < 3:
            continue
        name, actual_str, budget_str = csv_row[0], csv_row[1], csv_row[2]
        if name.startswith("Total"):
            continue
        actual_val = _parse_budget_amount(actual_str)
        budget_val = _parse_budget_amount(budget_str)
        percent = round(actual_val / budget_val * 100) if budget_val != 0 else 0
        if name.startswith("revenue:"):
            category = "income"
        elif name.startswith("asset:"):
            category = "saving"
        else:
            category = "expense"
        # Revenue/saving amounts are negative in hledger; show absolute values
        if category in ("income", "saving"):
            actual_fmt = f"{abs(actual_val):,} vnd" if actual_val else "0 vnd"
            budget_fmt = f"{abs(budget_val):,} vnd" if budget_val else "0 vnd"
        else:
            actual_fmt = f"{actual_val:,} vnd" if actual_val else "0 vnd"
            budget_fmt = f"{budget_val:,} vnd" if budget_val else "0 vnd"
        rows.append(BudgetRow(
            name=name,
            actual=actual_fmt,
            budget=budget_fmt,
            percent=percent,
            category=category,
        ))
    # Remove parent accounts that have children (keep only leaf budget rows)
    names = {r.name for r in rows}
    rows = [r for r in rows if not any(n.startswith(r.name + ":") for n in names)]
    # Sort within each category by percent descending
    cat_order = {"income": 0, "expense": 1, "saving": 2}
    rows.sort(key=lambda r: (cat_order.get(r.category, 9), -r.percent))
    return rows


async def avg_monthly(file: str, year: int, depth: int = 2) -> AvgMonthlyReport:
    """Return average monthly revenue/expense breakdown for *year*."""
    today = date.today()
    begin = f"{year}-01-01"
    if year == today.year:
        # End is first day of next month
        if today.month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{today.month + 1:02d}-01"
        months_elapsed = today.month
    else:
        end = f"{year + 1}-01-01"
        months_elapsed = 12

    report = await income_statement(file, depth=depth, begin=begin, end=end)

    def _build_rows(subreport: SubReport, months: int) -> tuple[list[AvgRow], str, int]:
        """Return (rows, formatted_total, raw_avg_total)."""
        names = {r.name for r in subreport.rows}
        leaves = [r for r in subreport.rows if not any(
            n.startswith(r.name + ":") for n in names
        )]
        avg_rows: list[AvgRow] = []
        total_abs = 0
        for r in leaves:
            avg = r.abs_total // months
            avg_rows.append(AvgRow(
                name=r.name,
                avg_amount=f"{avg:,} vnd",
                total=f"{r.abs_total:,} vnd",
                avg_value=avg,
            ))
            total_abs += r.abs_total
        total_avg = total_abs // months if total_abs else 0
        for row in avg_rows:
            row.percent = round(row.avg_value * 100 / total_avg) if total_avg else 0
        avg_rows.sort(key=lambda r: -r.avg_value)
        return avg_rows, f"{total_avg:,} vnd", total_avg

    # Fetch prior year for trend comparison (same month range for fairness)
    prev_year = year - 1
    prev_begin = f"{prev_year}-01-01"
    if year == today.year:
        # Compare same number of months in prior year
        if today.month == 12:
            prev_end = f"{prev_year + 1}-01-01"
        else:
            prev_end = f"{prev_year}-{today.month + 1:02d}-01"
        prev_months = today.month
    else:
        prev_end = f"{prev_year + 1}-01-01"
        prev_months = 12

    report, prev_report = await asyncio.gather(
        income_statement(file, depth=depth, begin=begin, end=end),
        income_statement(file, depth=0, begin=prev_begin, end=prev_end),
    )

    # Extract prior year totals (depth=0, just need grand totals)
    prev_expense_avg = 0
    prev_revenue_avg = 0
    for sub in prev_report.subreports:
        if sub.title.lower().startswith("revenue"):
            total_abs = sum(r.abs_total for r in sub.rows if not any(
                n.startswith(r.name + ":") for n in {rr.name for rr in sub.rows}
            ))
            prev_revenue_avg = total_abs // prev_months if total_abs else 0
        elif sub.title.lower().startswith("expense"):
            total_abs = sum(r.abs_total for r in sub.rows if not any(
                n.startswith(r.name + ":") for n in {rr.name for rr in sub.rows}
            ))
            prev_expense_avg = total_abs // prev_months if total_abs else 0

    revenue_rows: list[AvgRow] = []
    expense_rows: list[AvgRow] = []
    revenue_total = ""
    expense_total = ""
    raw_expense_avg = 0
    raw_revenue_avg = 0

    for sub in report.subreports:
        if sub.title.lower().startswith("revenue"):
            revenue_rows, revenue_total, raw_revenue_avg = _build_rows(sub, months_elapsed)
        elif sub.title.lower().startswith("expense"):
            expense_rows, expense_total, raw_expense_avg = _build_rows(sub, months_elapsed)

    # Expense as % of income
    expense_pct = round(raw_expense_avg * 100 / raw_revenue_avg) if raw_revenue_avg else 0

    # Trend vs prior year (positive = increase)
    expense_trend = (
        round((raw_expense_avg - prev_expense_avg) * 100 / prev_expense_avg)
        if prev_expense_avg else 0
    )
    revenue_trend = (
        round((raw_revenue_avg - prev_revenue_avg) * 100 / prev_revenue_avg)
        if prev_revenue_avg else 0
    )

    return AvgMonthlyReport(
        year=year,
        months_elapsed=months_elapsed,
        revenue_rows=revenue_rows,
        expense_rows=expense_rows,
        revenue_total=revenue_total,
        expense_total=expense_total,
        expense_pct_of_income=expense_pct,
        expense_trend=expense_trend,
        revenue_trend=revenue_trend,
    )


async def sources(file: str) -> list[str]:
    """Return sorted unique source file basenames from all transactions."""
    txs = await _print_all(file)
    names: set[str] = set()
    for tx in txs:
        if tx.tsourcepos and tx.tsourcepos[0].sourceName:
            names.add(Path(tx.tsourcepos[0].sourceName).name)
    return sorted(names)


_accounts_cache: tuple[float, list[str]] = (0.0, [])
_ACCOUNTS_TTL = 60  # seconds


async def accounts(file: str) -> list[str]:
    global _accounts_cache
    ts, cached = _accounts_cache
    if cached and time.monotonic() - ts < _ACCOUNTS_TTL:
        return cached
    args = ["hledger", "-f", file, "accounts"]
    output = await _run(args)
    result = [a for a in output.strip().split("\n") if a]
    _accounts_cache = (time.monotonic(), result)
    return result
