"""
Date utility: compute the previous full calendar week (Mon–Sun) in Moscow time.
"""
import datetime as _dt
from datetime import date, timedelta
import pytz


def get_previous_week_range() -> tuple[date, date]:
    """Return (monday, sunday) of the previous full calendar week (Mon–Sun).

    The calculation is performed in the Europe/Moscow timezone so that the cron
    job running at 17:00 UTC (20:00 MSK) on Wednesday always refers to the
    correct week.

    Examples:
        >>> # Today is Wednesday 2026-03-18 (MSK)
        >>> monday, sunday = get_previous_week_range()
        >>> monday
        datetime.date(2026, 3, 9)
        >>> sunday
        datetime.date(2026, 3, 15)

        The logic:
        - today.weekday() == 2 (Wednesday, 0=Monday)
        - days_since_last_monday = 2 + 7 = 9
        - monday = 2026-03-18 - 9 days = 2026-03-09  ✓
        - sunday = monday + 6 = 2026-03-15             ✓
    """
    moscow_tz = pytz.timezone("Europe/Moscow")
    now_moscow = _dt.datetime.now(moscow_tz)
    today = now_moscow.date()

    # weekday(): Monday=0, …, Sunday=6
    days_since_last_monday = today.weekday() + 7  # always go back at least a full week
    monday = today - timedelta(days=days_since_last_monday)
    sunday = monday + timedelta(days=6)
    return monday, sunday
