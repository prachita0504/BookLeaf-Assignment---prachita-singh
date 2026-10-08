"""Date helpers, e.g. the quarterly royalty payout schedule (quarter end + 45 days)."""

from datetime import UTC, date, datetime, timedelta

PAYOUT_DAYS_AFTER_QUARTER = 45


def utcnow() -> datetime:
    return datetime.now(UTC)


def _quarter_end(year: int, quarter: int) -> date:
    month = quarter * 3
    next_month_first = date(year + (month == 12), (month % 12) + 1, 1)
    return next_month_first - timedelta(days=1)


def next_payout(today: date) -> dict:
    """The next royalty payout deadline on or after `today`.

    Royalties for a quarter are paid within 45 days of it ending. E.g. on 7 Oct 2026 the next
    payout is for Jul–Sep 2026 (Q3), due by 14 Nov 2026.
    """
    year, quarter = today.year, (today.month - 1) // 3 + 1
    # Walk back one quarter (the one most recently ended), then forward until the deadline is not past.
    year, quarter = (year, quarter - 1) if quarter > 1 else (year - 1, 4)
    while True:
        end = _quarter_end(year, quarter)
        deadline = end + timedelta(days=PAYOUT_DAYS_AFTER_QUARTER)
        if deadline >= today:
            return {"quarter": f"Q{quarter} {year}", "quarter_end": end, "pay_by": deadline}
        year, quarter = (year, quarter + 1) if quarter < 4 else (year + 1, 1)


def days_between(earlier: date, later: date) -> int:
    return (later - earlier).days


def parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def fmt_date(value: date | None) -> str:
    """Human format used in prompts and emails: 14 Nov 2026."""
    return value.strftime("%d %b %Y").lstrip("0") if value else "n/a"
