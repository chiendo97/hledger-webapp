"""hledger CLI wrapper — async subprocess calls returning parsed JSON."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any


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


def _fmt_amount(amt: dict[str, Any]) -> str:
    """Format an hledger amount dict to a human-readable string."""
    commodity = amt["acommodity"]
    q = amt["aquantity"]
    value = q["floatingPoint"]
    places = q["decimalPlaces"]
    if places == 0 or commodity == "vnd":
        formatted = f"{int(value):,}"
    else:
        formatted = f"{value:,.{places}f}"
    return f"{formatted} {commodity}"


def _fmt_amounts(amounts: list[dict[str, Any]]) -> str:
    return ", ".join(_fmt_amount(a) for a in amounts)


# ── Public API ──────────────────────────────────────────────────────────


def parse_comment_tags(comment: str) -> list[dict[str, str]]:
    """Parse a hledger comment string into a list of {key, value} dicts.

    Comments come as '\\nkey:value\\nkey2:value2\\n'.
    """
    tags: list[dict[str, str]] = []
    for line in comment.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            tags.append({"key": key.strip(), "value": value.strip()})
        else:
            tags.append({"key": "", "value": line})
    return tags


def format_comment_tags(tags: list[dict[str, str]]) -> str:
    """Convert tag dicts back to hledger comment lines."""
    parts: list[str] = []
    for tag in tags:
        key = tag.get("key", "").strip()
        value = tag.get("value", "").strip()
        if key and value:
            parts.append(f"{key}:{value}")
        elif key:
            parts.append(key)
        elif value:
            parts.append(value)
    return parts


async def print_json(
    file: str,
    query: str = "",
    begin: str = "",
    end: str = "",
) -> list[dict[str, Any]]:
    args = ["hledger", "-f", file, "print", "-O", "json"]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    if query:
        args.append(query)
    raw: list[dict[str, Any]] = json.loads(await _run(args))
    # Enrich with formatted amounts for templates
    for tx in raw:
        tx["_tags"] = parse_comment_tags(tx.get("tcomment", ""))
        for p in tx.get("tpostings", []):
            p["_amount"] = _fmt_amounts(p.get("pamount", []))
            p["_tags"] = parse_comment_tags(p.get("pcomment", ""))
    return raw


async def balances(file: str, query: str = "", depth: int = 0, begin: str = "", end: str = "") -> list[dict[str, Any]]:
    args = ["hledger", "-f", file, "bal", "-O", "json", "--tree"]
    if depth:
        args += ["--depth", str(depth)]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    if query:
        args.append(query)
    raw = json.loads(await _run(args))
    # bal JSON is [rows_list, totals]
    account_rows = raw[0] if raw else []
    rows: list[dict[str, Any]] = []
    for account_row in account_rows:
        name = account_row[0]
        _full = account_row[1]
        depth = account_row[2]
        amounts = account_row[3]
        rows.append({
            "name": name,
            "depth": depth,
            "amounts": _fmt_amounts(amounts),
        })
    return rows


async def income_statement(file: str, depth: int = 0, begin: str = "", end: str = "") -> dict[str, Any]:
    args = ["hledger", "-f", file, "is", "-O", "json"]
    if depth:
        args += ["--depth", str(depth)]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    raw = json.loads(await _run(args))
    return _parse_compound_report(raw)


async def balance_sheet(file: str, depth: int = 0, begin: str = "", end: str = "") -> dict[str, Any]:
    args = ["hledger", "-f", file, "bs", "-O", "json"]
    if depth:
        args += ["--depth", str(depth)]
    if begin:
        args += ["-b", begin]
    if end:
        args += ["-e", end]
    raw = json.loads(await _run(args))
    return _parse_compound_report(raw)


async def register(file: str, account: str) -> list[dict[str, Any]]:
    args = ["hledger", "-f", file, "reg", account, "-O", "json"]
    raw = json.loads(await _run(args))
    rows: list[dict[str, Any]] = []
    for entry in raw:
        date = entry[0]
        _date2 = entry[1]
        desc = entry[2]
        posting = entry[3]
        running = entry[4]
        rows.append({
            "date": date,
            "description": desc,
            "account": posting["paccount"],
            "amount": _fmt_amounts(posting.get("pamount", [])),
            "running": _fmt_amounts(running),
        })
    return rows


async def add_transaction(file: str, date: str, description: str, postings: list[dict[str, str]]) -> None:
    lines = [f"\n{date} {description}"]
    for p in postings:
        account = p["account"]
        amount = p.get("amount", "")
        if amount:
            lines.append(f"    {account}    {amount}")
        else:
            lines.append(f"    {account}")
    lines.append("")
    async with asyncio.Lock():
        with open(file, "a") as f:
            f.write("\n".join(lines))


async def get_transaction(file: str, index: int) -> dict[str, Any]:
    txs = await print_json(file)
    for tx in txs:
        if tx["tindex"] == index:
            return tx
    raise ValueError(f"Transaction {index} not found")


async def update_transaction(
    file: str,
    index: int,
    date: str,
    description: str,
    tags: list[dict[str, str]],
    postings: list[dict[str, str]],
) -> None:
    tx = await get_transaction(file, index)
    src = tx["tsourcepos"]
    start_line = src[0]["sourceLine"]
    end_line = src[1]["sourceLine"]  # points to blank line after tx

    lines = [f"{date} {description}"]
    for tag_line in format_comment_tags(tags):
        lines.append(f"    ; {tag_line}")
    for p in postings:
        account = p["account"]
        amount = p.get("amount", "")
        if amount:
            lines.append(f"    {account}    {amount}")
        else:
            lines.append(f"    {account}")

    path = Path(file)
    file_lines = path.read_text().splitlines(keepends=True)
    # Replace lines [start_line-1 .. end_line-2] (0-indexed, excluding trailing blank)
    new_block = "\n".join(lines) + "\n"
    file_lines[start_line - 1 : end_line - 1] = [new_block]
    path.write_text("".join(file_lines))


async def accounts(file: str) -> list[str]:
    args = ["hledger", "-f", file, "accounts"]
    output = await _run(args)
    return [a for a in output.strip().split("\n") if a]


# ── Helpers ─────────────────────────────────────────────────────────────


def _parse_compound_report(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse hledger compound balance report (is/bs) JSON."""
    title = raw.get("cbrTitle", "")
    subreports: list[dict[str, Any]] = []
    for sub in raw.get("cbrSubreports", []):
        sub_title = sub[0]
        sub_data = sub[1]
        rows: list[dict[str, Any]] = []
        for row in sub_data.get("prRows", []):
            name = row["prrName"]
            depth = name.count(":") if isinstance(name, str) else 0
            amounts = row.get("prrAmounts", [[]])
            amt_list = [_fmt_amount(a) for a in amounts[0]] if amounts and amounts[0] else []
            abs_total = sum(abs(a["aquantity"]["floatingPoint"]) for a in amounts[0]) if amounts and amounts[0] else 0
            rows.append({
                "name": name,
                "depth": depth,
                "amounts": _fmt_amounts(amounts[0]) if amounts and amounts[0] else "",
                "amount_items": amt_list,
                "_abs_total": abs_total,
            })
        totals = sub_data.get("prTotals", {})
        total_amounts = totals.get("prrAmounts", [[]])
        total_list = [_fmt_amount(a) for a in total_amounts[0]] if total_amounts and total_amounts[0] else []
        subreports.append({
            "title": sub_title,
            "rows": rows,
            "total": _fmt_amounts(total_amounts[0]) if total_amounts and total_amounts[0] else "",
            "total_items": total_list,
        })
    # Grand total
    grand_totals = raw.get("cbrTotals", {})
    grand_amounts = grand_totals.get("prrAmounts", [[]])
    grand_list = [_fmt_amount(a) for a in grand_amounts[0]] if grand_amounts and grand_amounts[0] else []
    return {
        "title": title,
        "subreports": subreports,
        "grand_total": _fmt_amounts(grand_amounts[0]) if grand_amounts and grand_amounts[0] else "",
        "grand_total_items": grand_list,
    }
