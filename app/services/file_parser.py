from pathlib import Path
import pandas as pd
from .restart_window import parse_restart_window

REQUIRED_COLUMNS = {'server_name', 'ip_address', 'restart_window'}
_NAN_VALUES = {'nan', 'none', 'null', 'n/a', ''}

def _clean_optional(value) -> str | None:
    """Convert pandas cell value to str or None, treating NaN and empty as None."""
    if value is None:
        return None
    s = str(value).strip()
    return None if s.lower() in _NAN_VALUES else s

def parse_server_file(filepath: str) -> list[dict]:
    """Parse xlsx or csv file. Returns list of server dicts. Raises ValueError on bad format."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == '.csv':
        df = pd.read_csv(filepath, dtype=str)
    elif suffix in ('.xlsx', '.xls'):
        df = pd.read_excel(filepath, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {suffix!r}. Use .csv or .xlsx")

    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    servers = []
    for _, row in df.iterrows():
        servers.append({
            'server_name': str(row['server_name']).strip(),
            'ip_address': str(row['ip_address']).strip(),
            'restart_window': str(row['restart_window']).strip(),
            'username': _clean_optional(row.get('username')),
            'password': _clean_optional(row.get('password')),
        })

    return servers


def validate_restart_windows(servers: list[dict]) -> list[str]:
    """Returns list of error strings for servers with unparseable restart windows."""
    errors = []
    for s in servers:
        try:
            parse_restart_window(s['restart_window'])
        except ValueError as e:
            errors.append(f"{s['server_name']}: {e}")
    return errors
