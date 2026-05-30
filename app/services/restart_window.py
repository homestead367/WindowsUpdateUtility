from datetime import datetime, timedelta

WEEKDAYS = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6,
}

def parse_restart_window(value: str) -> datetime:
    """Parse 'Sunday 02:00' or '2026-06-01 02:00' into a future datetime."""
    value = value.strip()

    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M'):
        try:
            dt = datetime.strptime(value, fmt)
            if dt < datetime.now():
                raise ValueError(f"Restart window {value!r} is in the past")
            return dt
        except ValueError as e:
            if 'in the past' in str(e):
                raise
            continue

    parts = value.split(None, 1)
    if len(parts) == 2:
        day_str, time_str = parts
        day_num = WEEKDAYS.get(day_str.lower())
        if day_num is not None:
            try:
                hour, minute = map(int, time_str.split(':'))
            except ValueError:
                pass
            else:
                now = datetime.now()
                days_ahead = (day_num - now.weekday()) % 7
                if days_ahead == 0 and (now.hour, now.minute) >= (hour, minute):
                    days_ahead = 7
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                target += timedelta(days=days_ahead)
                return target

    raise ValueError(
        f"Cannot parse restart window: {value!r}. "
        "Use 'Sunday 02:00', 'Sat 03:30', or '2026-06-15 02:00'."
    )
