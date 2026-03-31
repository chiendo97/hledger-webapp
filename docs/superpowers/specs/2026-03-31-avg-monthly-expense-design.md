# Average Monthly Expense/Revenue View

**Date:** 2026-03-31
**Status:** Design approved

## Overview

Add a toggle to the existing budget page that switches between the current per-month budget view and a new "Averages" view showing average monthly expense and revenue across a selected year. The average is computed as year-to-date total divided by months elapsed.

## Data Layer

### New function: `hledger.avg_monthly(file, year)`

- Runs `hledger is -b {year}-01 -e {next_month_start} -O json --flat` where `next_month_start` is `{year+1}-01` for past years, or first day of next month for current year
- Reuses `_parse_compound_report()` to get a `CompoundReport` with Revenue and Expenses subreports
- Computes `months_elapsed`: if `year == current_year`, use current month number (e.g. March 2026 = 3); otherwise 12
- Divides each row's VND total by `months_elapsed`, formats as display string
- Sorts rows by average amount descending

### New models

```python
class AvgRow(BaseModel):
    name: str           # Account name (e.g. "expense:food")
    avg_amount: str     # Formatted average (e.g. "1,500,000 vnd")
    total: str          # Formatted year-to-date total

class AvgMonthlyReport(BaseModel):
    year: int
    months_elapsed: int
    revenue_rows: list[AvgRow]
    expense_rows: list[AvgRow]
    revenue_total: str   # Averaged grand total
    expense_total: str   # Averaged grand total
```

## UI & Routing

### Toggle on budget page

- Toggle bar between the picker and content area: two buttons — "Budget" (default) and "Averages"
- Active button uses `text-accent-text` / distinct background; inactive uses `text-text-muted`
- Smooth transition between states
- Toggle state is URL-driven via `view=budget|avg` query param (default: `budget`)

### When "Budget" is active (existing behavior)

- Month picker visible
- Budget content loaded via `/budget/partial?month=...`

### When "Averages" is active

- Month picker replaced by **year picker** (left/right arrows with year label, same visual style as month picker)
- Content loaded via `/budget/avg/partial?year=2026`

### New routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/budget/avg/partial` | GET | HTMX partial, accepts `year` query param, returns averages content |

The existing `/budget` route gains a `view` query param to control which toggle is active on initial load.

### Template: `partials/avg_content.html`

**Hero section:**
- Subtitle: "Based on {months_elapsed} months" in `.text-text-muted`

**Two sections — Expenses, then Revenue:**
- Each row: account name (left, linked to `/register?account=...&begin={year}-01&end={end}`), average amount (right)
- Section total at bottom with divider line above
- Sorted by average amount descending
- Colors: `.text-negative` for expenses, `.text-positive` for revenue
- No progress bars (no budget baseline to compare)

**Empty state:**
- "No transactions found for {year}." using `.empty-state` class

### Year picker

- Same visual style as existing month picker (arrows + label)
- 44px minimum touch targets on arrows
- Triggers HTMX swap of `#page-content` with `/budget/avg/partial?year={year}`
- Updates URL query param for bookmarkability

## Design Constraints

- Follow existing patterns: full page route + HTMX partial, same card/section styling
- Reuse `_parse_compound_report()` and `CompoundReport` model from income statement
- All colors from `style.css` semantic tokens — no new tokens needed
- Mobile-first, monospace, dark theme consistent with rest of app
- Toggle must feel seamless — consistent spacing between views so content doesn't jump

## Out of Scope

- Savings category (only expense and revenue)
- Month-by-month breakdown / charts
- Comparison between years
- Budget vs average comparison
