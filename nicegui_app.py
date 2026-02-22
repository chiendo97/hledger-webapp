"""hledger web app — NiceGUI SPA."""

import asyncio
import os
from datetime import date as dt_date
from pathlib import Path
from typing import Any, Callable

from nicegui import ui

import hledger
from hledger import BalanceRow, PostingInput, RegisterRow, Tag, Transaction

JOURNAL = os.environ.get(
    "HLEDGER_FILE",
    str(Path(__file__).resolve().parent.parent / "2025.journal"),
)

# ── Helpers ────────────────────────────────────────────────────────────


def _month_range(month: str) -> dict[str, str]:
    if not month:
        month = dt_date.today().strftime("%Y-%m")
    y, m = int(month[:4]), int(month[5:7])
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
    return {
        "month": month,
        "begin": f"{y}-{m:02d}-01",
        "end": f"{ny}-{nm:02d}-01",
        "prev": f"{py}-{pm:02d}",
        "next": f"{ny}-{nm:02d}",
    }


def _amt_color(text: str) -> str:
    return "text-red-400" if text.startswith("-") else "text-green-400"


def _posting_display(p: Any) -> tuple[str, str]:
    """Return (text, css_color) for a posting."""
    if p.balance_assertion_display:
        return f"= {p.balance_assertion_display}", "text-gray-500"
    color = "text-red-400" if p.pamount and p.pamount[0].aquantity.floatingPoint < 0 else "text-green-400"
    return p.amount_display, color


def _nav_to(route: str, defaults: dict[str, Any], **overrides: Any) -> None:
    p = {**defaults, **overrides}
    qs = "&".join(f"{k}={v}" for k, v in p.items() if v)
    ui.navigate.to(f"{route}?{qs}")


# ── UI Components ──────────────────────────────────────────────────────


def _month_picker(month: str, on_change: Callable) -> None:
    mr = _month_range(month)
    with ui.row().classes("items-center justify-center gap-2 mb-3 w-full"):
        ui.button("←", on_click=lambda: on_change(mr["prev"])).classes(
            "px-2 py-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm !min-w-0"
        ).props("flat dense")
        inp = ui.input(value=mr["month"]).classes(
            "bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200"
        ).props('type="month" dense outlined dark')
        inp.on("update:model-value", lambda e: on_change(e.args))
        ui.button("→", on_click=lambda: on_change(mr["next"])).classes(
            "px-2 py-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm !min-w-0"
        ).props("flat dense")


def _pill_group(label: str, options: list[tuple[Any, str]], current: Any, on_change: Callable) -> None:
    with ui.row().classes("gap-1 items-center text-xs mb-3"):
        ui.label(f"{label}:").classes("text-gray-500 mr-1")
        for val, text in options:
            active = "bg-blue-600 text-white" if current == val else "bg-gray-800 text-gray-400 hover:bg-gray-700"
            ui.button(text, on_click=lambda v=val: on_change(v)).classes(
                f"px-3 py-1 rounded-full {active}"
            ).props("flat dense unelevated !min-w-0")


def _balance_table(
    rows: list[BalanceRow], month: str, *,
    title: str = "", total: str = "", total_items: list[str] | None = None,
    multi: bool = False,
) -> None:
    if title:
        ui.label(title).classes("text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2")
    with ui.element("table").classes("w-full text-sm table-fixed"):
        with ui.element("colgroup"):
            ui.html('<col class="w-3/5"><col class="w-2/5">')
        with ui.element("tbody"):
            for row in rows:
                with ui.element("tr").classes(
                    "border-b border-gray-800 hover:bg-gray-900/50 cursor-pointer"
                ).on("click", lambda r=row: ui.navigate.to(
                    f"/register?account={r.name}" + (f"&month={month}" if month else "")
                )):
                    with ui.element("td").classes("py-2 pr-2 text-gray-400 truncate").style(
                        f"padding-left: {row.depth * 12}px"
                    ):
                        ui.label(row.name).classes("!p-0 !m-0")
                    items = row.amount_items
                    if multi and len(items) > 1:
                        with ui.element("td").classes(
                            "py-2 pl-2 font-mono text-right whitespace-nowrap overflow-hidden text-ellipsis"
                        ):
                            for item in items:
                                ui.label(item).classes(f"!p-0 !m-0 {_amt_color(item)}")
                    else:
                        with ui.element("td").classes(
                            f"py-2 pl-2 font-mono text-right whitespace-nowrap overflow-hidden text-ellipsis {_amt_color(row.amounts)}"
                        ):
                            ui.label(row.amounts).classes("!p-0 !m-0")
            if total or total_items:
                _items = total_items or []
                with ui.element("tr").classes("bg-gray-800/50"):
                    with ui.element("td").classes("py-2 pr-2 font-semibold text-gray-300"):
                        ui.label("Total").classes("!p-0 !m-0")
                    if multi and len(_items) > 1:
                        with ui.element("td").classes(
                            "py-2 pl-2 font-mono font-semibold text-right whitespace-nowrap text-gray-100"
                        ):
                            for item in _items:
                                ui.label(item).classes("!p-0 !m-0")
                    else:
                        with ui.element("td").classes(
                            "py-2 pl-2 font-mono font-semibold text-right whitespace-nowrap text-gray-100"
                        ):
                            ui.label(total).classes("!p-0 !m-0")


def _grand_total(label: str, items: list[str]) -> None:
    if not items:
        return
    with ui.element("div").classes("bg-blue-900/30 border border-blue-800 rounded-lg p-3 w-full"):
        ui.label(label).classes("text-xs text-gray-400 uppercase tracking-wider mb-2 text-center w-full")
        with ui.element("div").classes("text-center space-y-1 w-full"):
            for item in items:
                ui.label(item).classes(
                    f"font-mono text-lg font-semibold {_amt_color(item)} text-center w-full"
                )


def _tx_card(tx: Transaction) -> None:
    with ui.element("div").classes("flex justify-between items-start mb-2"):
        ui.label(tx.tdate).classes("text-xs text-gray-500 !p-0 !m-0")
        ui.label(f"#{tx.tindex}").classes("text-xs text-gray-600 !p-0 !m-0")
    ui.label(tx.tdescription).classes(
        "font-medium text-sm mb-2 text-gray-100 !p-0 !m-0 desc-clamp"
    )
    with ui.element("div").classes("space-y-1"):
        for p in tx.tpostings:
            text, color = _posting_display(p)
            with ui.element("div").classes("flex justify-between items-baseline gap-2 text-xs"):
                ui.label(p.paccount).classes("text-gray-400 truncate min-w-0 !p-0 !m-0")
                ui.label(text).classes(f"font-mono whitespace-nowrap {color} shrink-0 !p-0 !m-0")


def _tx_grid(
    txs: list[Transaction], on_click: Callable, running: dict[int, str] | None = None,
) -> None:
    current_date = ""
    container = None
    for tx in txs:
        if tx.tdate != current_date:
            current_date = tx.tdate
            with ui.row().classes(
                f"items-center gap-3 {'mt-6' if container else ''} mb-3 w-full"
            ):
                ui.element("div").classes("flex-1 border-t border-gray-600")
                ui.label(tx.tdate).classes("text-sm font-medium text-gray-300 whitespace-nowrap")
                ui.element("div").classes("flex-1 border-t border-gray-600")
            container = ui.element("div").classes(
                "space-y-3 sm:grid sm:grid-cols-2 sm:gap-3 sm:space-y-0 lg:grid-cols-3 overflow-hidden"
            )
        with container:  # type: ignore[union-attr]
            card = ui.element("div").classes(
                "bg-gray-900 border border-gray-800 rounded-lg p-3 cursor-pointer "
                "hover:border-gray-600 transition-colors overflow-hidden min-w-0"
            )
            card.on("click", lambda t=tx: on_click(t))
            with card:
                _tx_card(tx)
                bal = (running or {}).get(tx.tindex, "")
                if bal:
                    with ui.element("div").classes(
                        "mt-2 pt-1 border-t border-gray-800 flex justify-between text-xs"
                    ):
                        ui.label("Balance").classes("text-gray-500 !p-0 !m-0")
                        ui.label(bal).classes("font-mono text-gray-400 !p-0 !m-0")


# ── Dialogs ────────────────────────────────────────────────────────────


def _dialog_header(title: str, on_close: Callable) -> None:
    with ui.row().classes("justify-between items-center w-full pb-3 border-b border-gray-800"):
        ui.label(title).classes("text-lg font-semibold")
        ui.button("×", on_click=on_close).classes(
            "text-gray-400 hover:text-white text-xl !min-w-0"
        ).props("flat dense")


def _tx_detail_view(tx: Transaction) -> None:
    meta: list[tuple[str, str, str]] = [
        ("Date", tx.tdate, "text-gray-100"),
        ("Description", tx.tdescription, "text-gray-100"),
    ]
    meta += [(t.key, t.value, "text-gray-300") for t in tx.tags]
    with ui.element("table").classes("w-full text-sm"):
        with ui.element("tbody"):
            for label, value, cls in meta:
                with ui.element("tr").classes("border-b border-gray-800"):
                    with ui.element("td").classes(
                        "text-gray-400 py-1.5 pr-4 whitespace-nowrap align-top"
                    ):
                        ui.label(label).classes("!p-0 !m-0")
                    with ui.element("td").classes(
                        f"{cls} py-1.5 text-right"
                    ).style("word-break:break-all"):
                        ui.label(value).classes("!p-0 !m-0")
    with ui.element("table").classes("w-full text-sm"):
        with ui.element("tbody"):
            for p in tx.tpostings:
                text, color = _posting_display(p)
                with ui.element("tr").classes("border-b border-gray-800"):
                    with ui.element("td").classes(
                        "text-gray-300 py-1.5 pr-2"
                    ).style("word-break:break-all"):
                        ui.label(p.paccount).classes("!p-0 !m-0")
                    with ui.element("td").classes(
                        f"font-mono py-1.5 text-right whitespace-nowrap {color}"
                    ):
                        ui.label(text).classes("!p-0 !m-0")
                for ptag in p.tags:
                    with ui.element("tr"):
                        with ui.element("td").classes(
                            "pl-4 py-0.5 text-xs text-gray-500"
                        ).props('colspan="2"'):
                            ui.label(f"{ptag.key} {ptag.value}").classes(
                                "font-mono !p-0 !m-0"
                            )


def _show_tx_dialog(tx: Transaction) -> None:
    async def _save(
        dlg: ui.dialog, d_inp: ui.input, desc_inp: ui.input,
        tag_rows: list[tuple[ui.input, ui.input]],
        posting_rows: list[tuple[ui.input, ui.input, str]],
    ) -> None:
        tags = [Tag(key=k.value, value=v.value) for k, v in tag_rows if k.value or v.value]
        postings = [
            PostingInput(account=a.value, amount=amt.value, balance_assertion=ba)
            for a, amt, ba in posting_rows if a.value
        ]
        if d_inp.value and desc_inp.value and postings:
            await hledger.update_transaction(
                JOURNAL, tx.tindex, d_inp.value, desc_inp.value, tags, postings,
            )
            dlg.close()
            ui.navigate.to("/transactions")

    with ui.dialog() as dlg, ui.card().classes(
        "bg-gray-900 border border-gray-700 w-full max-w-lg lg:max-w-2xl"
    ):
        # View mode
        with ui.element("div") as view_div:
            _dialog_header(f"Transaction #{tx.tindex}", dlg.close)
            with ui.element("div").classes("space-y-3 pt-3"):
                _tx_detail_view(tx)
                with ui.row().classes("gap-2 pt-3 border-t border-gray-800 w-full"):
                    ui.button(
                        "Edit",
                        on_click=lambda: (
                            view_div.set_visibility(False),
                            edit_div.set_visibility(True),
                        ),
                    ).classes("flex-1 bg-blue-600 hover:bg-blue-500 text-white text-sm py-2 rounded-lg")
                    ui.button("Close", on_click=dlg.close).classes(
                        "flex-1 bg-gray-700 hover:bg-gray-600 text-white text-sm py-2 rounded-lg"
                    )

        # Edit mode
        with ui.element("div") as edit_div:
            edit_div.set_visibility(False)
            _dialog_header("Edit Transaction", dlg.close)
            with ui.element("div").classes("space-y-3 pt-3"):
                ui.label("Date").classes("text-xs text-gray-400")
                d_inp = ui.input(value=tx.tdate).classes("w-full").props(
                    'type="date" dense outlined dark'
                )
                ui.label("Description").classes("text-xs text-gray-400")
                desc_inp = ui.input(value=tx.tdescription).classes("w-full").props(
                    "dense outlined dark"
                )
                ui.label("Tags").classes("text-xs text-gray-400")
                tag_rows: list[tuple[ui.input, ui.input]] = []
                tags_c = ui.column().classes("gap-2 w-full")
                with tags_c:
                    for tag in tx.tags:
                        with ui.row().classes("gap-2 w-full items-center"):
                            k = ui.input(value=tag.key, placeholder="key").classes(
                                "w-1/3"
                            ).props("dense outlined dark")
                            v = ui.input(value=tag.value, placeholder="value").classes(
                                "flex-1"
                            ).props("dense outlined dark")
                            tag_rows.append((k, v))

                def _add_tag() -> None:
                    with tags_c:
                        with ui.row().classes("gap-2 w-full items-center"):
                            k = ui.input(placeholder="key").classes("w-1/3").props(
                                "dense outlined dark"
                            )
                            v = ui.input(placeholder="value").classes("flex-1").props(
                                "dense outlined dark"
                            )
                            tag_rows.append((k, v))

                ui.button("+ Tag", on_click=_add_tag).classes(
                    "text-blue-400 text-xs"
                ).props("flat dense")

                ui.label("Postings").classes("text-xs text-gray-400")
                posting_rows: list[tuple[ui.input, ui.input, str]] = []
                postings_c = ui.column().classes("gap-2 w-full")

                async def _build_edit() -> None:
                    accts = await hledger.accounts(JOURNAL)
                    with postings_c:
                        for p in tx.tpostings:
                            with ui.row().classes("gap-2 w-full items-center"):
                                a = ui.select(
                                    options=accts, value=p.paccount, with_input=True,
                                ).classes("flex-1").props("dense outlined dark")
                                amt = ui.input(
                                    value=p.amount_display, placeholder="Amount",
                                ).classes("w-32").props("dense outlined dark")
                                posting_rows.append(
                                    (a, amt, p.balance_assertion_display or "")
                                )

                    def _add_posting() -> None:
                        with postings_c:
                            with ui.row().classes("gap-2 w-full items-center"):
                                a = ui.select(
                                    options=accts, value="", with_input=True,
                                ).classes("flex-1").props("dense outlined dark")
                                amt = ui.input(placeholder="Amount").classes(
                                    "w-32"
                                ).props("dense outlined dark")
                                posting_rows.append((a, amt, ""))

                    ui.button("+ Posting", on_click=_add_posting).classes(
                        "text-blue-400 text-sm"
                    ).props("flat dense")

                    with ui.row().classes("gap-2 pt-3 border-t border-gray-800 w-full"):
                        ui.button(
                            "Save",
                            on_click=lambda: _save(
                                dlg, d_inp, desc_inp, tag_rows, posting_rows,
                            ),
                        ).classes(
                            "flex-1 bg-green-600 hover:bg-green-500 text-white text-sm py-2 rounded-lg"
                        )
                        ui.button(
                            "Cancel",
                            on_click=lambda: (
                                edit_div.set_visibility(False),
                                view_div.set_visibility(True),
                            ),
                        ).classes(
                            "flex-1 bg-gray-700 hover:bg-gray-600 text-white text-sm py-2 rounded-lg"
                        )

                asyncio.ensure_future(_build_edit())

    dlg.open()


def _show_add_dialog() -> None:
    async def _save_new(
        dlg: ui.dialog, d_inp: ui.input, desc_inp: ui.input,
        posting_rows: list[tuple[ui.select, ui.input]],
    ) -> None:
        postings = [
            PostingInput(account=a.value, amount=amt.value)
            for a, amt in posting_rows if a.value
        ]
        if d_inp.value and desc_inp.value and postings:
            await hledger.add_transaction(
                JOURNAL, d_inp.value, desc_inp.value, postings,
            )
            dlg.close()
            ui.navigate.to("/transactions")

    with ui.dialog() as dlg, ui.card().classes(
        "bg-gray-900 border border-gray-700 w-full max-w-lg"
    ):
        _dialog_header("New Transaction", dlg.close)
        with ui.element("div").classes("space-y-3 pt-3"):
            ui.label("Date").classes("text-xs text-gray-400")
            d_inp = ui.input(value=dt_date.today().isoformat()).classes("w-full").props(
                'type="date" dense outlined dark'
            )
            ui.label("Description").classes("text-xs text-gray-400")
            desc_inp = ui.input(placeholder="Description").classes("w-full").props(
                "dense outlined dark"
            )
            ui.label("Postings").classes("text-xs text-gray-400")
            posting_rows: list[tuple[ui.select, ui.input]] = []
            postings_c = ui.column().classes("gap-2 w-full")

            async def _build() -> None:
                accts = await hledger.accounts(JOURNAL)
                with postings_c:
                    for _ in range(2):
                        with ui.row().classes("gap-2 w-full items-center"):
                            a = ui.select(
                                options=accts, value="", with_input=True,
                            ).classes("flex-1").props("dense outlined dark")
                            amt = ui.input(placeholder="Amount").classes(
                                "w-36"
                            ).props("dense outlined dark")
                            posting_rows.append((a, amt))

                def _add() -> None:
                    with postings_c:
                        with ui.row().classes("gap-2 w-full items-center"):
                            a = ui.select(
                                options=accts, value="", with_input=True,
                            ).classes("flex-1").props("dense outlined dark")
                            amt = ui.input(placeholder="Amount").classes(
                                "w-36"
                            ).props("dense outlined dark")
                            posting_rows.append((a, amt))

                ui.button("+ Posting", on_click=_add).classes(
                    "text-blue-400 text-sm"
                ).props("flat dense")
                ui.button(
                    "Save",
                    on_click=lambda: _save_new(dlg, d_inp, desc_inp, posting_rows),
                ).classes(
                    "w-full bg-blue-600 hover:bg-blue-700 rounded-lg px-4 py-2 text-sm font-medium"
                )

            asyncio.ensure_future(_build())

    dlg.open()


# ── Sub-pages ──────────────────────────────────────────────────────────


def _update_nav(nav_links: dict[str, ui.element], active: str) -> None:
    for key, el in nav_links.items():
        if key == active:
            el.classes(remove="text-gray-400", add="text-blue-400")
        else:
            el.classes(remove="text-blue-400", add="text-gray-400")


def _setup_sub(
    title_el: ui.label, nav: dict[str, ui.element], page_title: str, nav_key: str,
) -> ui.spinner:
    title_el.set_text(page_title)
    ui.page_title(page_title)
    _update_nav(nav, nav_key)
    return ui.spinner("dots", size="lg").classes("self-center mt-8 text-blue-400")


async def _transactions_sub(
    title: ui.label, nav: dict[str, ui.element], q: str = "", month: str = "",
) -> None:
    spinner = _setup_sub(title, nav, "Transactions", "tx")
    mr = _month_range(month)
    month = mr["month"]
    txs = await hledger.print_json(JOURNAL, query=q, begin=mr["begin"], end=mr["end"])
    txs.reverse()
    spinner.delete()

    _month_picker(
        month,
        lambda m: ui.navigate.to(
            f"/transactions?month={m}" + (f"&q={q}" if q else "")
        ),
    )

    with ui.row().classes("gap-2 mb-4 w-full"):
        si = ui.input(value=q, placeholder="Search...").classes(
            "flex-1 bg-gray-800 border border-gray-700 rounded-lg text-sm"
        ).props("dense outlined dark")

        def _go() -> None:
            ui.navigate.to(f"/transactions?month={month}&q={si.value}")

        si.on("keydown.enter", _go)
        ui.button("Go", on_click=_go).classes(
            "bg-blue-600 hover:bg-blue-700 rounded-lg px-4 py-2 text-sm font-medium"
        )

    ui.button("+ Add Transaction", on_click=_show_add_dialog).classes(
        "w-full bg-green-700 hover:bg-green-600 rounded-lg px-4 py-2 text-sm font-medium mb-4"
    )

    if txs:
        _tx_grid(txs, _show_tx_dialog)
    else:
        ui.label("No transactions found.").classes(
            "text-gray-500 text-center py-8 w-full"
        )


async def _balances_sub(
    title: ui.label, nav: dict[str, ui.element],
    q: str = "", depth: int = 2, month: str = "", sort: str = "",
) -> None:
    spinner = _setup_sub(title, nav, "Balances", "bal")
    rows = await hledger.balances(JOURNAL, query=q, depth=depth)
    if sort == "amount":
        rows.sort(key=lambda r: r.abs_total, reverse=True)
    spinner.delete()

    defaults = {"depth": depth, "month": month, "sort": sort, "q": q}
    go = lambda **ov: _nav_to("/balances", defaults, **ov)  # noqa: E731
    _pill_group("Depth", [(1, "1"), (2, "2"), (3, "3")], depth, lambda d: go(depth=d))
    _pill_group("Sort", [("", "Name"), ("amount", "Amount")], sort, lambda s: go(sort=s))

    fi = ui.input(value=q, placeholder="Filter accounts...").classes(
        "w-full bg-gray-800 border border-gray-700 rounded-lg text-sm mb-4"
    ).props("dense outlined dark")
    fi.on("keydown.enter", lambda: go(q=fi.value))

    if rows:
        _balance_table(rows, month)
    else:
        ui.label("No data.").classes("text-gray-500 text-center py-8 w-full")


async def _compound_sub(
    title_el: ui.label, nav: dict[str, ui.element], *,
    page_title: str, nav_key: str, route: str,
    fetch: Callable, grand_label: str,
    multi: bool = False, use_begin: bool = True,
    depth: int = 2, month: str = "", sort: str = "",
) -> None:
    spinner = _setup_sub(title_el, nav, page_title, nav_key)
    mr = _month_range(month)
    month = mr["month"]
    kw: dict[str, Any] = {"depth": depth, "end": mr["end"]}
    if use_begin:
        kw["begin"] = mr["begin"]
    report = await fetch(JOURNAL, **kw)
    if sort == "amount":
        for sub in report.subreports:
            sub.rows.sort(key=lambda r: r.abs_total, reverse=True)
    spinner.delete()

    defaults: dict[str, Any] = {"depth": depth, "month": month, "sort": sort}
    go = lambda **ov: _nav_to(route, defaults, **ov)  # noqa: E731
    _month_picker(month, lambda m: go(month=m))
    _pill_group("Depth", [(1, "1"), (2, "2"), (3, "3")], depth, lambda d: go(depth=d))
    _pill_group("Sort", [("", "Name"), ("amount", "Amount")], sort, lambda s: go(sort=s))

    for sub in report.subreports:
        with ui.element("div").classes("mb-6"):
            _balance_table(
                sub.rows, month, title=sub.title,
                total=sub.total, total_items=sub.total_items, multi=multi,
            )
    _grand_total(grand_label, report.grand_total_items)


async def _is_sub(
    title: ui.label, nav: dict[str, ui.element],
    depth: int = 2, month: str = "", sort: str = "",
) -> None:
    await _compound_sub(
        title, nav, page_title="Income Statement", nav_key="is",
        route="/incomestatement", fetch=hledger.income_statement,
        grand_label="Net", depth=depth, month=month, sort=sort,
    )


async def _bs_sub(
    title: ui.label, nav: dict[str, ui.element],
    depth: int = 2, month: str = "", sort: str = "",
) -> None:
    await _compound_sub(
        title, nav, page_title="Balance Sheet", nav_key="bs",
        route="/balancesheet", fetch=hledger.balance_sheet,
        grand_label="Net Worth", multi=True, use_begin=False,
        depth=depth, month=month, sort=sort,
    )


async def _register_sub(
    title: ui.label, nav: dict[str, ui.element],
    account: str = "", month: str = "",
) -> None:
    spinner = _setup_sub(title, nav, "Register", "reg")
    mr = _month_range(month)
    month = mr["month"]

    accts = await hledger.accounts(JOURNAL)
    txs: list[Transaction] = []
    reg_rows: list[RegisterRow] = []
    if account:
        txs, reg_rows = await asyncio.gather(
            hledger.print_json(
                JOURNAL, query=account, begin=mr["begin"], end=mr["end"],
            ),
            hledger.register(
                JOURNAL, account=account, begin=mr["begin"], end=mr["end"],
            ),
        )
        txs.reverse()
        reg_rows.reverse()

    running: dict[int, str] = {}
    if txs and reg_rows:
        ri = 0
        for tx in txs:
            last = ""
            while (
                ri < len(reg_rows)
                and reg_rows[ri].date == tx.tdate
                and reg_rows[ri].description == tx.tdescription
            ):
                last = reg_rows[ri].running
                ri += 1
            if last:
                running[tx.tindex] = last

    spinner.delete()

    options = {a: a for a in accts}
    if account and account not in options:
        options[account] = account

    _month_picker(
        month,
        lambda m: ui.navigate.to(
            f"/register?month={m}" + (f"&account={account}" if account else "")
        ),
    )
    ui.select(
        options=options, value=account or None, with_input=True,
        label="Select account...",
        on_change=lambda e: (
            ui.navigate.to(f"/register?account={e.value}&month={month}")
            if e.value else None
        ),
    ).classes("w-full mb-4").props("dense outlined dark")

    if txs:
        _tx_grid(txs, _show_tx_dialog, running)
    elif account:
        ui.label(f"No entries for {account}.").classes(
            "text-gray-500 text-center py-8 w-full"
        )
    else:
        ui.label("Select an account above.").classes(
            "text-gray-500 text-center py-8 w-full"
        )


# ── Layout ─────────────────────────────────────────────────────────────

NAV_ITEMS = [
    ("Txns", "/transactions", "tx",
     "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"
     "M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"),
    ("Bal", "/balances", "bal",
     "M3 6h18M3 12h18M3 18h18"),
    ("Income", "/incomestatement", "is",
     "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"),
    ("BS", "/balancesheet", "bs",
     "M9 7h6m0 10v-3m-3 3v-6m-3 6v-1m6-9a2 2 0 012 2v8a2 2 0 01-2 2H9a2 2 0 01-2-2V9a2 2 0 012-2"),
    ("Register", "/register", "reg",
     "M4 6h16M4 10h16M4 14h16M4 18h16"),
]

HEAD_CSS = """<style>
    body { overflow-x: hidden !important; }
    .nicegui-content { padding: 0 !important; gap: 0 !important; width: 100% !important; max-width: 100vw !important; overflow-x: hidden !important; }
    .nicegui-sub-pages { gap: 0 !important; width: 100% !important; min-width: 0 !important; }
    .nicegui-row, .nicegui-column { min-width: 0 !important; max-width: 100% !important; }
    .q-field { max-width: 100% !important; }
    .nicegui-html { width: 100% !important; min-width: 0 !important; overflow-x: auto !important; }
    .q-footer { padding-bottom: env(safe-area-inset-bottom) !important; }
    table { table-layout: fixed; }
    .desc-clamp {
        display: -webkit-box !important; -webkit-line-clamp: 2 !important;
        -webkit-box-orient: vertical !important; overflow: hidden !important;
        word-break: break-all;
    }
</style>"""


@ui.page("/")
@ui.page("/{_:path}")
def main_page() -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, '
        'maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
    )
    ui.add_head_html('<script src="https://cdn.tailwindcss.com"></script>')
    ui.add_head_html("<script>tailwind.config={darkMode:'class'}</script>")
    ui.add_head_html(HEAD_CSS)

    nav_links: dict[str, ui.element] = {}

    with ui.header(elevated=False).classes(
        "bg-gray-900 border-b border-gray-800 px-4 py-3"
    ):
        header_title = ui.label("hledger").classes(
            "text-lg font-semibold text-center w-full"
        )

    with ui.footer(elevated=False).classes(
        "bg-gray-900 border-t border-gray-800"
    ):
        with ui.row().classes(
            "w-full justify-around py-2 text-xs sm:py-3 sm:text-sm sm:justify-center sm:gap-8"
        ):
            for label, href, key, icon_path in NAV_ITEMS:
                link = ui.element("a").classes(
                    "flex flex-col items-center gap-1 text-gray-400 no-underline cursor-pointer"
                )
                link.on("click", lambda h=href: ui.navigate.to(h))
                nav_links[key] = link
                with link:
                    ui.html(
                        f'<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                        f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{icon_path}"/></svg>'
                    )
                    ui.label(label).classes("text-inherit")

    with ui.element("div").classes(
        "bg-gray-950 text-gray-100 dark w-full min-h-screen overflow-x-hidden"
    ):
        with ui.element("main").classes(
            "max-w-2xl lg:max-w-4xl xl:max-w-5xl mx-auto px-4 py-4 w-full min-w-0 overflow-x-hidden"
        ):
            ui.sub_pages(
                {
                    "/": lambda title, nav: ui.navigate.to("/transactions"),
                    "/transactions": _transactions_sub,
                    "/balances": _balances_sub,
                    "/incomestatement": _is_sub,
                    "/balancesheet": _bs_sub,
                    "/register": _register_sub,
                },
                data={"title": header_title, "nav": nav_links},
            )


# ── Run ────────────────────────────────────────────────────────────────

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="hledger", dark=True, port=8001, reload=True)
