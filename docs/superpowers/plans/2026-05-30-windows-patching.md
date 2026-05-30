# Windows Patch Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Flask web app that reads server lists from Excel/CSV, pushes all Windows updates via WinRM/PowerShell, and schedules per-server controlled restart windows.

**Architecture:** Flask app with SQLAlchemy/SQLite for state, pywinrm for WinRM/NTLM connections, ThreadPoolExecutor for concurrent server workers, Bootstrap 5 frontend with JS polling for live status updates.

**Tech Stack:** Python 3.12, Flask, pywinrm, pandas, openpyxl, SQLAlchemy, cryptography, Bootstrap 5, pytest

---

## File Structure

```
/project/windowsPatching/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Config class + SECRET_KEY bootstrap
│   ├── database.py          # SQLAlchemy engine, session factory, Base
│   ├── models.py            # Job, Server, AppSettings ORM models
│   ├── executor.py          # Module-level ThreadPoolExecutor singleton
│   ├── routes/
│   │   ├── __init__.py      # empty
│   │   ├── dashboard.py     # GET /
│   │   ├── jobs.py          # GET/POST /jobs/new, GET /jobs/<id>
│   │   ├── api.py           # /api/jobs/<id>, /api/servers/<id>/action
│   │   └── settings.py      # GET/POST /settings
│   ├── services/
│   │   ├── __init__.py      # empty
│   │   ├── crypto.py        # Fernet encrypt/decrypt for credentials
│   │   ├── file_parser.py   # Parse xlsx/csv → list[dict]
│   │   ├── restart_window.py # Parse restart window string → datetime
│   │   └── winrm_worker.py  # Per-server WinRM patching worker
│   ├── templates/
│   │   ├── base.html        # Bootstrap 5 base layout
│   │   ├── dashboard.html   # Job list
│   │   ├── new_job.html     # Upload form + file preview
│   │   ├── job_detail.html  # Live per-server status table
│   │   └── settings.html    # Credentials + WinRM config
│   └── static/
│       ├── sample_servers.csv
│       └── app.js           # Polling + action button handlers
├── tests/
│   ├── conftest.py          # Fixtures: test Flask app, in-memory DB
│   ├── test_crypto.py
│   ├── test_restart_window.py
│   ├── test_file_parser.py
│   └── test_api.py
├── requirements.txt
├── run.py                   # Entry point
├── .env.example
└── docker-compose.yml
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `run.py`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/database.py`
- Create: `app/executor.py`
- Create: `app/routes/__init__.py`
- Create: `app/services/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
flask==3.0.3
pywinrm==0.4.3
pandas==2.2.2
openpyxl==3.1.2
sqlalchemy==2.0.30
cryptography==42.0.8
python-dotenv==1.0.1
requests-kerberos==0.15.0
pytest==8.2.2
pytest-flask==1.3.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install --break-system-packages -r requirements.txt`
Expected: All packages install without errors.

- [ ] **Step 3: Create app/config.py**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _bootstrap_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    key = os.urandom(32).hex()
    env_path = Path('.env')
    if env_path.exists():
        content = env_path.read_text()
        if 'SECRET_KEY' not in content:
            with open(env_path, 'a') as f:
                f.write(f'\nSECRET_KEY={key}\n')
    else:
        env_path.write_text(f'SECRET_KEY={key}\n')
    os.environ['SECRET_KEY'] = key
    return key

class Config:
    SECRET_KEY = _bootstrap_secret_key()
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///winpatch.db')
    WINRM_PORT = int(os.environ.get('WINRM_PORT', 5985))
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 10))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/winpatch_uploads')

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key-32-bytes-exactly!'
    WTF_CSRF_ENABLED = False
```

- [ ] **Step 4: Create app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

engine = None
SessionLocal = None

def init_db(app):
    global engine, SessionLocal
    engine = create_engine(
        app.config['DATABASE_URL'],
        connect_args={'check_same_thread': False}
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()
```

- [ ] **Step 5: Create app/executor.py**

```python
from concurrent.futures import ThreadPoolExecutor

_executor = None

def get_executor(max_workers=10):
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor
```

- [ ] **Step 6: Create app/__init__.py**

```python
import os
from flask import Flask
from .config import Config
from .database import init_db

def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db(app)

    from .routes.dashboard import bp as dashboard_bp
    from .routes.jobs import bp as jobs_bp
    from .routes.api import bp as api_bp
    from .routes.settings import bp as settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    return app
```

- [ ] **Step 7: Create stub route files and run.py**

`app/routes/__init__.py` — empty file.

`app/services/__init__.py` — empty file.

`run.py`:
```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

`.env.example`:
```
SECRET_KEY=
DATABASE_URL=sqlite:///winpatch.db
WINRM_PORT=5985
MAX_WORKERS=10
UPLOAD_FOLDER=/tmp/winpatch_uploads
```

- [ ] **Step 8: Verify scaffold runs**

First create stub blueprints (one-liner each) so the app can import:

`app/routes/dashboard.py`:
```python
from flask import Blueprint
bp = Blueprint('dashboard', __name__)
```

`app/routes/jobs.py`:
```python
from flask import Blueprint
bp = Blueprint('jobs', __name__)
```

`app/routes/api.py`:
```python
from flask import Blueprint
bp = Blueprint('api', __name__)
```

`app/routes/settings.py`:
```python
from flask import Blueprint
bp = Blueprint('settings', __name__)
```

Run: `python run.py`
Expected: Flask starts on port 5000 without ImportError.
Stop with Ctrl-C.

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: project scaffold — Flask app factory, config, database, executor"
```

---

## Task 2: Database Models

**Files:**
- Create: `app/models.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing model test**

`tests/conftest.py`:
```python
import pytest
from app import create_app
from app.config import TestConfig
from app.database import Base, engine

@pytest.fixture
def app():
    application = create_app(TestConfig.__dict__)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def session(app):
    from app.database import get_session
    s = get_session()
    yield s
    s.close()
```

`tests/test_models.py`:
```python
from datetime import datetime
from app.models import Job, Server, AppSettings
from app.database import get_session

def test_create_job(session):
    job = Job(filename='servers.csv')
    session.add(job)
    session.commit()
    assert job.id is not None
    assert job.status == 'pending'
    assert isinstance(job.created_at, datetime)

def test_create_server(session):
    job = Job(filename='servers.csv')
    session.add(job)
    session.flush()
    server = Server(
        job_id=job.id,
        server_name='PROD-WEB-01',
        ip_address='192.168.1.10',
        restart_window='Sunday 02:00',
    )
    session.add(server)
    session.commit()
    assert server.id is not None
    assert server.status == 'pending'
    assert server.updates_installed == 0

def test_job_servers_relationship(session):
    job = Job(filename='servers.csv')
    session.add(job)
    session.flush()
    session.add(Server(job_id=job.id, server_name='A', ip_address='1.1.1.1', restart_window='Sun 02:00'))
    session.add(Server(job_id=job.id, server_name='B', ip_address='1.1.1.2', restart_window='Sun 02:00'))
    session.commit()
    session.refresh(job)
    assert len(job.servers) == 2

def test_app_settings_defaults(session):
    from app.models import get_or_create_settings
    settings = get_or_create_settings(session)
    assert settings.winrm_port == 5985
    assert settings.max_workers == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Job' from 'app.models'`

- [ ] **Step 3: Implement app/models.py**

```python
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Job(Base):
    __tablename__ = 'jobs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default='pending')

    servers: Mapped[list['Server']] = relationship(
        'Server', back_populates='job', cascade='all, delete-orphan'
    )

    def progress(self) -> dict:
        total = len(self.servers)
        if total == 0:
            return {'total': 0, 'done': 0, 'pct': 0}
        done = sum(1 for s in self.servers if s.status in (
            'up_to_date', 'restart_scheduled', 'error'
        ))
        return {'total': total, 'done': done, 'pct': int(done / total * 100)}


class Server(Base):
    __tablename__ = 'servers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey('jobs.id'), nullable=False)
    server_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    restart_window: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(100), default='pending')
    updates_installed: Mapped[int] = mapped_column(Integer, default=0)
    restart_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    log_output: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped['Job'] = relationship('Job', back_populates='servers')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'server_name': self.server_name,
            'ip_address': self.ip_address,
            'restart_window': self.restart_window,
            'status': self.status,
            'updates_installed': self.updates_installed,
            'restart_scheduled_at': self.restart_scheduled_at.isoformat() if self.restart_scheduled_at else None,
            'error_message': self.error_message,
        }


class AppSettings(Base):
    __tablename__ = 'app_settings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_username_enc: Mapped[str | None] = mapped_column(String(512))
    default_password_enc: Mapped[str | None] = mapped_column(String(512))
    winrm_port: Mapped[int] = mapped_column(Integer, default=5985)
    max_workers: Mapped[int] = mapped_column(Integer, default=10)


def get_or_create_settings(session) -> AppSettings:
    settings = session.get(AppSettings, 1)
    if not settings:
        settings = AppSettings(id=1, winrm_port=5985, max_workers=10)
        session.add(settings)
        session.commit()
    return settings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/conftest.py tests/test_models.py
git commit -m "feat: SQLAlchemy models — Job, Server, AppSettings"
```

---

## Task 3: Crypto Service

**Files:**
- Create: `app/services/crypto.py`
- Create: `tests/test_crypto.py`

- [ ] **Step 1: Write failing test**

`tests/test_crypto.py`:
```python
import os
os.environ['SECRET_KEY'] = 'test-secret-key-32-bytes-exactly!'

from app.services.crypto import encrypt, decrypt

def test_encrypt_returns_non_empty_string():
    result = encrypt('mypassword')
    assert isinstance(result, str)
    assert len(result) > 0
    assert result != 'mypassword'

def test_decrypt_round_trips():
    original = 'P@ssw0rd!123'
    assert decrypt(encrypt(original)) == original

def test_encrypt_empty_string_returns_empty():
    assert encrypt('') == ''

def test_decrypt_empty_string_returns_empty():
    assert decrypt('') == ''

def test_different_values_produce_different_ciphertext():
    assert encrypt('abc') != encrypt('xyz')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crypto.py -v`
Expected: FAIL with `ImportError: cannot import name 'encrypt'`

- [ ] **Step 3: Implement app/services/crypto.py**

```python
import os
import base64
import hashlib
from cryptography.fernet import Fernet

def _get_fernet() -> Fernet:
    key = os.environ.get('SECRET_KEY', '')
    if not key:
        raise RuntimeError('SECRET_KEY environment variable is not set')
    derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
    return Fernet(derived)

def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ''
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    return _get_fernet().decrypt(ciphertext.encode()).decode()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_crypto.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/crypto.py tests/test_crypto.py
git commit -m "feat: Fernet encrypt/decrypt service for credential storage"
```

---

## Task 4: Restart Window Parser

**Files:**
- Create: `app/services/restart_window.py`
- Create: `tests/test_restart_window.py`

- [ ] **Step 1: Write failing tests**

`tests/test_restart_window.py`:
```python
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch
from app.services.restart_window import parse_restart_window

FAKE_NOW = datetime(2026, 5, 30, 10, 0, 0)  # Saturday 10:00 AM

@patch('app.services.restart_window.datetime')
def test_exact_datetime_format(mock_dt):
    mock_dt.now.return_value = FAKE_NOW
    mock_dt.strptime.side_effect = lambda *a, **k: datetime.strptime(*a, **k)
    result = parse_restart_window('2026-06-15 02:00')
    assert result == datetime(2026, 6, 15, 2, 0, 0)

@patch('app.services.restart_window.datetime')
def test_next_sunday_from_saturday(mock_dt):
    mock_dt.now.return_value = FAKE_NOW  # Saturday
    mock_dt.strptime.side_effect = lambda *a, **k: datetime.strptime(*a, **k)
    result = parse_restart_window('Sunday 02:00')
    assert result == datetime(2026, 5, 31, 2, 0, 0)

@patch('app.services.restart_window.datetime')
def test_same_day_future_time(mock_dt):
    mock_dt.now.return_value = FAKE_NOW  # Saturday 10:00
    mock_dt.strptime.side_effect = lambda *a, **k: datetime.strptime(*a, **k)
    result = parse_restart_window('Saturday 23:00')
    assert result == datetime(2026, 5, 30, 23, 0, 0)

@patch('app.services.restart_window.datetime')
def test_same_day_past_time_advances_one_week(mock_dt):
    mock_dt.now.return_value = FAKE_NOW  # Saturday 10:00
    mock_dt.strptime.side_effect = lambda *a, **k: datetime.strptime(*a, **k)
    result = parse_restart_window('Saturday 09:00')
    assert result == datetime(2026, 6, 6, 9, 0, 0)

@patch('app.services.restart_window.datetime')
def test_abbreviated_day_name(mock_dt):
    mock_dt.now.return_value = FAKE_NOW
    mock_dt.strptime.side_effect = lambda *a, **k: datetime.strptime(*a, **k)
    result = parse_restart_window('Sun 02:00')
    assert result == datetime(2026, 5, 31, 2, 0, 0)

def test_invalid_format_raises():
    with pytest.raises(ValueError, match='Cannot parse restart window'):
        parse_restart_window('tomorrow morning')

def test_past_exact_datetime_raises():
    with pytest.raises(ValueError, match='in the past'):
        parse_restart_window('2020-01-01 02:00')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_restart_window.py -v`
Expected: FAIL with `ImportError: cannot import name 'parse_restart_window'`

- [ ] **Step 3: Implement app/services/restart_window.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_restart_window.py -v`
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/restart_window.py tests/test_restart_window.py
git commit -m "feat: restart window parser — day+time and exact datetime formats"
```

---

## Task 5: File Parser Service

**Files:**
- Create: `app/services/file_parser.py`
- Create: `tests/test_file_parser.py`
- Create: `app/static/sample_servers.csv`

- [ ] **Step 1: Create sample CSV for tests**

`app/static/sample_servers.csv`:
```csv
server_name,ip_address,restart_window,username,password
PROD-WEB-01,192.168.1.10,Sunday 02:00,DOMAIN\svcpatch,
PROD-DB-01,192.168.1.11,Sunday 02:00,,
DEV-APP-01,192.168.1.20,Saturday 03:00,DOMAIN\devsvc,DevPass123
```

- [ ] **Step 2: Write failing tests**

`tests/test_file_parser.py`:
```python
import io
import pytest
import pandas as pd
from unittest.mock import patch
from app.services.file_parser import parse_server_file, validate_restart_windows

def _make_csv(content: str) -> str:
    import tempfile, os
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    f.write(content)
    f.close()
    return f.name

def test_parse_valid_csv(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text(
        'server_name,ip_address,restart_window\n'
        'WEB-01,192.168.1.10,Sunday 02:00\n'
        'DB-01,192.168.1.11,Saturday 03:00\n'
    )
    result = parse_server_file(str(csv))
    assert len(result) == 2
    assert result[0]['server_name'] == 'WEB-01'
    assert result[0]['ip_address'] == '192.168.1.10'
    assert result[0]['restart_window'] == 'Sunday 02:00'
    assert result[0]['username'] is None
    assert result[0]['password'] is None

def test_parse_csv_with_optional_columns(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text(
        'server_name,ip_address,restart_window,username,password\n'
        'WEB-01,192.168.1.10,Sunday 02:00,DOMAIN\\svc,secret\n'
    )
    result = parse_server_file(str(csv))
    assert result[0]['username'] == 'DOMAIN\\svc'
    assert result[0]['password'] == 'secret'

def test_parse_csv_column_names_case_insensitive(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text(
        'Server_Name,IP_Address,Restart_Window\n'
        'WEB-01,192.168.1.10,Sunday 02:00\n'
    )
    result = parse_server_file(str(csv))
    assert result[0]['server_name'] == 'WEB-01'

def test_parse_csv_extra_columns_ignored(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text(
        'server_name,ip_address,restart_window,notes,owner\n'
        'WEB-01,192.168.1.10,Sunday 02:00,primary,alice\n'
    )
    result = parse_server_file(str(csv))
    assert 'notes' not in result[0]
    assert 'owner' not in result[0]

def test_parse_csv_missing_required_column_raises(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text('server_name,ip_address\nWEB-01,192.168.1.10\n')
    with pytest.raises(ValueError, match='Missing required columns'):
        parse_server_file(str(csv))

def test_parse_unsupported_extension_raises(tmp_path):
    f = tmp_path / 'servers.txt'
    f.write_text('data')
    with pytest.raises(ValueError, match='Unsupported file format'):
        parse_server_file(str(f))

def test_validate_restart_windows_valid():
    servers = [
        {'server_name': 'A', 'restart_window': 'Sunday 02:00'},
        {'server_name': 'B', 'restart_window': '2030-01-01 02:00'},
    ]
    errors = validate_restart_windows(servers)
    assert errors == []

def test_validate_restart_windows_invalid():
    servers = [{'server_name': 'A', 'restart_window': 'garbage value'}]
    errors = validate_restart_windows(servers)
    assert len(errors) == 1
    assert 'A' in errors[0]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_file_parser.py -v`
Expected: FAIL with `ImportError: cannot import name 'parse_server_file'`

- [ ] **Step 4: Implement app/services/file_parser.py**

```python
from pathlib import Path
import pandas as pd
from .restart_window import parse_restart_window

REQUIRED_COLUMNS = {'server_name', 'ip_address', 'restart_window'}

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
        username = str(row.get('username', '') or '').strip() or None
        password = str(row.get('password', '') or '').strip() or None
        servers.append({
            'server_name': str(row['server_name']).strip(),
            'ip_address': str(row['ip_address']).strip(),
            'restart_window': str(row['restart_window']).strip(),
            'username': username,
            'password': password,
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_file_parser.py -v`
Expected: 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/file_parser.py app/static/sample_servers.csv tests/test_file_parser.py
git commit -m "feat: file parser for xlsx/csv server lists with restart window validation"
```

---

## Task 6: WinRM Worker

**Files:**
- Create: `app/services/winrm_worker.py`

- [ ] **Step 1: Implement app/services/winrm_worker.py**

```python
import winrm
from datetime import datetime
from .restart_window import parse_restart_window

PS_ENSURE_MODULE = r"""
$module = Get-Module -ListAvailable -Name PSWindowsUpdate
if (-not $module) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -ErrorAction SilentlyContinue
    Install-Module -Name PSWindowsUpdate -Force -Confirm:$false
}
Write-Output "OK"
"""

PS_LIST_UPDATES = r"""
Import-Module PSWindowsUpdate -Force
$updates = Get-WUList -ErrorAction Stop
Write-Output ($updates | Measure-Object).Count
"""

PS_INSTALL_UPDATES = r"""
Import-Module PSWindowsUpdate -Force
$result = Install-WindowsUpdate -AcceptAll -AutoReboot:$false -Confirm:$false -ErrorAction Stop
Write-Output ($result | Where-Object { $_.Result -eq 'Installed' } | Measure-Object).Count
"""

PS_SCHEDULE_RESTART = r"""
param([string]$RestartAt)
$action = New-ScheduledTaskAction -Execute "shutdown.exe" -Argument "/r /f /t 60 /c `"Scheduled maintenance restart`""
$trigger = New-ScheduledTaskTrigger -Once -At $RestartAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "WinPatchRestart" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
Write-Output "OK"
"""

PS_DELETE_TASK = r"""
$task = Get-ScheduledTask -TaskName "WinPatchRestart" -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName "WinPatchRestart" -Confirm:$false
    Write-Output "DELETED"
} else {
    Write-Output "NOT_FOUND"
}
"""

PS_IMMEDIATE_RESTART = r'shutdown /r /f /t 60'


def _run_ps(session: winrm.Session, script: str):
    return session.run_ps(script)


def _update_server(server_id: int, **kwargs):
    from app.database import get_session
    from app.models import Server
    s = get_session()
    try:
        server = s.get(Server, server_id)
        for k, v in kwargs.items():
            setattr(server, k, v)
        server.updated_at = datetime.utcnow()
        s.commit()
    finally:
        s.close()


def run_server_worker(server_id: int, default_username: str, default_password: str,
                      per_server_password: str | None, winrm_port: int):
    """
    Worker function executed in a thread for a single server.
    per_server_password is passed in-memory; never written to DB.
    """
    from app.database import get_session
    from app.models import Server

    s = get_session()
    try:
        server = s.get(Server, server_id)
        username = server.username or default_username
        password = per_server_password or default_password
        ip = server.ip_address
    finally:
        s.close()

    _update_server(server_id, status='connecting')

    try:
        session = winrm.Session(
            f'http://{ip}:{winrm_port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        result = _run_ps(session, 'Write-Output "ping"')
        if result.status_code != 0:
            raise ConnectionError(result.std_err.decode(errors='replace'))
    except Exception as e:
        _update_server(server_id, status='error', error_message=f'WinRM unreachable: {e}')
        return

    _update_server(server_id, status='checking_module')
    result = _run_ps(session, PS_ENSURE_MODULE)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='PSWindowsUpdate install failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    _update_server(server_id, status='checking_updates')
    result = _run_ps(session, PS_LIST_UPDATES)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Get-WUList failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    update_count = int(result.std_out.decode(errors='replace').strip() or '0')
    if update_count == 0:
        _update_server(server_id, status='up_to_date', updates_installed=0)
        return

    _update_server(server_id, status='installing')
    result = _run_ps(session, PS_INSTALL_UPDATES)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Install failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    installed = int(result.std_out.decode(errors='replace').strip() or '0')

    _update_server(server_id, status='scheduling_restart', updates_installed=installed)

    try:
        from app.database import get_session as gs
        s2 = gs()
        srv = s2.get(Server, server_id)
        restart_window = srv.restart_window
        s2.close()
        restart_dt = parse_restart_window(restart_window)
    except ValueError as e:
        _update_server(server_id, status='error', error_message=str(e),
                       updates_installed=installed)
        return

    restart_iso = restart_dt.strftime('%Y-%m-%dT%H:%M:%S')
    script = PS_SCHEDULE_RESTART.replace(
        'param([string]$RestartAt)\n', ''
    ).replace('$RestartAt', f'"{restart_iso}"')
    result = _run_ps(session, script)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Schedule task failed: ' +
                       result.std_err.decode(errors='replace'),
                       updates_installed=installed)
        return

    _update_server(server_id, status='restart_scheduled',
                   updates_installed=installed, restart_scheduled_at=restart_dt)


def test_connection(ip: str, port: int, username: str, password: str) -> tuple[bool, str]:
    """Test WinRM connectivity. Returns (success, message)."""
    try:
        session = winrm.Session(
            f'http://{ip}:{port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        result = session.run_ps('Write-Output "OK"')
        if result.status_code == 0:
            return True, 'Connected successfully'
        return False, result.std_err.decode(errors='replace')
    except Exception as e:
        return False, str(e)


def immediate_restart(ip: str, port: int, username: str, password: str) -> tuple[bool, str]:
    """Delete scheduled task and issue immediate restart."""
    try:
        session = winrm.Session(
            f'http://{ip}:{port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        _run_ps(session, PS_DELETE_TASK)
        result = _run_ps(session, PS_IMMEDIATE_RESTART)
        return True, 'Restart initiated'
    except Exception as e:
        return False, str(e)


def reschedule_restart(ip: str, port: int, username: str, password: str,
                       new_window: str) -> tuple[bool, str]:
    """Delete old task and register new restart task."""
    try:
        restart_dt = parse_restart_window(new_window)
    except ValueError as e:
        return False, str(e)

    try:
        session = winrm.Session(
            f'http://{ip}:{port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        _run_ps(session, PS_DELETE_TASK)
        restart_iso = restart_dt.strftime('%Y-%m-%dT%H:%M:%S')
        script = PS_SCHEDULE_RESTART.replace(
            'param([string]$RestartAt)\n', ''
        ).replace('$RestartAt', f'"{restart_iso}"')
        result = _run_ps(session, script)
        if result.status_code != 0:
            return False, result.std_err.decode(errors='replace')
        return True, restart_dt.isoformat()
    except Exception as e:
        return False, str(e)
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from app.services.winrm_worker import run_server_worker; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/services/winrm_worker.py
git commit -m "feat: WinRM worker — patch install, restart scheduling, immediate restart"
```

---

## Task 7: Dashboard Route + Base Templates

**Files:**
- Create: `app/routes/dashboard.py`
- Create: `app/templates/base.html`
- Create: `app/templates/dashboard.html`

- [ ] **Step 1: Implement app/routes/dashboard.py**

```python
from flask import Blueprint, render_template
from app.database import get_session
from app.models import Job

bp = Blueprint('dashboard', __name__)

@bp.get('/')
def index():
    session = get_session()
    try:
        jobs = session.query(Job).order_by(Job.created_at.desc()).all()
        jobs_data = []
        for job in jobs:
            p = job.progress()
            jobs_data.append({
                'id': job.id,
                'filename': job.filename,
                'created_at': job.created_at.strftime('%Y-%m-%d %H:%M'),
                'status': job.status,
                'total': p['total'],
                'done': p['done'],
                'pct': p['pct'],
            })
    finally:
        session.close()
    return render_template('dashboard.html', jobs=jobs_data)
```

- [ ] **Step 2: Create app/templates/base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}WinPatch{% endblock %} — Windows Patch Manager</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet"
        integrity="sha384-tViUnnbplkXTnGNichM77j0h7pMRxcm6skQGiIl2C9JEFkGPTxPhLT9ZBVK0/A9" crossorigin="anonymous">
  <style>
    body { background: #f8f9fa; }
    .navbar-brand { font-weight: 700; letter-spacing: -0.5px; }
    .badge-pending { background-color: #6c757d; }
    .badge-connecting, .badge-checking_module, .badge-checking_updates,
    .badge-installing, .badge-scheduling_restart { background-color: #0d6efd; }
    .badge-up_to_date, .badge-restart_scheduled { background-color: #198754; }
    .badge-error { background-color: #dc3545; }
  </style>
</head>
<body>
  <nav class="navbar navbar-dark bg-dark mb-4">
    <div class="container">
      <a class="navbar-brand" href="/"><i class="bi bi-shield-check me-2"></i>WinPatch</a>
      <div class="d-flex gap-3">
        <a href="/jobs/new" class="btn btn-sm btn-success">New Job</a>
        <a href="/settings" class="btn btn-sm btn-outline-light">Settings</a>
      </div>
    </div>
  </nav>
  <div class="container pb-5">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
          integrity="sha384-YvpcrYf0tY3lHB60NNkmXc4s9bIOgUxi8T/jzmTt6fDUc6KNpf8EsJI0cA3nqKM" crossorigin="anonymous"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Create app/templates/dashboard.html**

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h2 class="mb-0">Patch Jobs</h2>
  <a href="/jobs/new" class="btn btn-success"><i class="bi bi-plus-lg me-1"></i>New Job</a>
</div>
{% if jobs %}
<div class="card shadow-sm">
  <table class="table table-hover mb-0">
    <thead class="table-dark">
      <tr>
        <th>#</th><th>File</th><th>Started</th><th>Servers</th><th>Progress</th><th>Status</th><th></th>
      </tr>
    </thead>
    <tbody>
      {% for job in jobs %}
      <tr>
        <td class="text-muted">{{ job.id }}</td>
        <td><i class="bi bi-file-earmark-spreadsheet me-1 text-success"></i>{{ job.filename }}</td>
        <td>{{ job.created_at }}</td>
        <td>{{ job.done }} / {{ job.total }}</td>
        <td style="min-width:120px">
          <div class="progress" style="height:8px">
            <div class="progress-bar" style="width:{{ job.pct }}%"></div>
          </div>
        </td>
        <td><span class="badge badge-{{ job.status }} text-white">{{ job.status }}</span></td>
        <td><a href="/jobs/{{ job.id }}" class="btn btn-sm btn-outline-primary">View</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% else %}
<div class="text-center py-5 text-muted">
  <i class="bi bi-inbox fs-1"></i>
  <p class="mt-3">No patch jobs yet. <a href="/jobs/new">Create one</a>.</p>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Smoke-test the dashboard**

Run: `python run.py`
Visit: `http://localhost:5000/`
Expected: Dashboard loads showing "No patch jobs yet."

- [ ] **Step 5: Commit**

```bash
git add app/routes/dashboard.py app/templates/base.html app/templates/dashboard.html
git commit -m "feat: dashboard page — job list with progress bars"
```

---

## Task 8: New Job Route + Template

**Files:**
- Modify: `app/routes/jobs.py`
- Create: `app/templates/new_job.html`

- [ ] **Step 1: Implement /jobs/new in app/routes/jobs.py**

```python
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from app.database import get_session
from app.models import Job, Server, AppSettings, get_or_create_settings
from app.services.file_parser import parse_server_file, validate_restart_windows
from app.services.winrm_worker import run_server_worker
from app.executor import get_executor

bp = Blueprint('jobs', __name__)

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

@bp.get('/jobs/new')
def new_job_form():
    db = get_session()
    try:
        settings = get_or_create_settings(db)
        from app.services.crypto import decrypt
        default_user = decrypt(settings.default_username_enc or '') or ''
    finally:
        db.close()
    return render_template('new_job.html', default_username=default_user)


@bp.post('/jobs/new/preview')
def preview_file():
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    f = request.files['file']
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f'Unsupported file type: {ext}. Use .csv or .xlsx', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    upload_dir = os.environ.get('UPLOAD_FOLDER', '/tmp/winpatch_uploads')
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f.filename)
    filepath = os.path.join(upload_dir, filename)
    f.save(filepath)

    try:
        servers = parse_server_file(filepath)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('jobs.new_job_form'))

    errors = validate_restart_windows(servers)
    session['preview_filepath'] = filepath
    session['preview_filename'] = filename

    return render_template(
        'new_job.html',
        servers=servers,
        errors=errors,
        default_username=request.form.get('default_username', ''),
        filepath=filepath,
        filename=filename,
    )


@bp.post('/jobs/new/start')
def start_job():
    filepath = request.form.get('filepath')
    filename = request.form.get('filename')
    default_username = request.form.get('default_username', '').strip()
    default_password = request.form.get('default_password', '').strip()

    if not filepath or not os.path.exists(filepath):
        flash('Upload the file again to start a job.', 'danger')
        return redirect(url_for('jobs.new_job_form'))

    try:
        servers = parse_server_file(filepath)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('jobs.new_job_form'))

    db = get_session()
    try:
        job = Job(filename=filename, status='running')
        db.add(job)
        db.flush()

        server_records = []
        per_server_passwords = {}
        for s in servers:
            record = Server(
                job_id=job.id,
                server_name=s['server_name'],
                ip_address=s['ip_address'],
                restart_window=s['restart_window'],
                username=s['username'],
            )
            db.add(record)
            db.flush()
            server_records.append(record)
            per_server_passwords[record.id] = s['password']

        db.commit()
        job_id = job.id

        settings = get_or_create_settings(db)
        winrm_port = settings.winrm_port
        max_workers = settings.max_workers
    finally:
        db.close()

    executor = get_executor(max_workers)
    for record in server_records:
        executor.submit(
            run_server_worker,
            record.id,
            default_username,
            default_password,
            per_server_passwords.get(record.id),
            winrm_port,
        )

    flash(f'Job started for {len(server_records)} servers.', 'success')
    return redirect(url_for('jobs.job_detail', job_id=job_id))


@bp.get('/jobs/<int:job_id>')
def job_detail(job_id):
    db = get_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            flash('Job not found.', 'danger')
            return redirect(url_for('dashboard.index'))
        servers = [s.to_dict() for s in job.servers]
        progress = job.progress()
    finally:
        db.close()
    return render_template('job_detail.html', job_id=job_id,
                           filename=job.filename, servers=servers,
                           progress=progress, created_at=job.created_at)
```

- [ ] **Step 2: Create app/templates/new_job.html**

```html
{% extends "base.html" %}
{% block title %}New Patch Job{% endblock %}
{% block content %}
<h2 class="mb-4">New Patch Job</h2>

<div class="row">
  <div class="col-lg-7">
    <!-- Upload form -->
    <div class="card shadow-sm mb-4">
      <div class="card-header"><strong>1. Upload Server List</strong></div>
      <div class="card-body">
        <form method="post" action="/jobs/new/preview" enctype="multipart/form-data">
          <div class="mb-3">
            <label class="form-label">Server file (.csv or .xlsx)</label>
            <input type="file" class="form-control" name="file" accept=".csv,.xlsx,.xls" required>
            <div class="form-text">
              <a href="/static/sample_servers.csv" download>Download sample template</a>
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label">Default Username</label>
            <input type="text" class="form-control" name="default_username"
                   placeholder="DOMAIN\svcpatch" value="{{ default_username or '' }}">
          </div>
          <button type="submit" class="btn btn-primary">Preview Servers</button>
        </form>
      </div>
    </div>

    {% if servers %}
    <!-- Preview + confirm -->
    <div class="card shadow-sm border-success">
      <div class="card-header bg-success text-white">
        <strong>2. Confirm — {{ servers|length }} server(s) found</strong>
      </div>
      <div class="card-body p-0">
        {% if errors %}
        <div class="alert alert-danger m-3">
          <strong>Restart window errors (fix before starting):</strong>
          <ul class="mb-0">{% for e in errors %}<li>{{ e }}</li>{% endfor %}</ul>
        </div>
        {% endif %}
        <div class="table-responsive">
          <table class="table table-sm mb-0">
            <thead class="table-light">
              <tr><th>Server</th><th>IP</th><th>Restart Window</th><th>Custom User</th></tr>
            </thead>
            <tbody>
              {% for s in servers %}
              <tr>
                <td>{{ s.server_name }}</td>
                <td><code>{{ s.ip_address }}</code></td>
                <td>{{ s.restart_window }}</td>
                <td>{{ s.username or '<em class="text-muted">default</em>'|safe }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
      {% if not errors %}
      <div class="card-footer">
        <form method="post" action="/jobs/new/start">
          <input type="hidden" name="filepath" value="{{ filepath }}">
          <input type="hidden" name="filename" value="{{ filename }}">
          <input type="hidden" name="default_username" value="{{ default_username or '' }}">
          <div class="mb-3">
            <label class="form-label">Default Password</label>
            <input type="password" class="form-control" name="default_password"
                   placeholder="Enter WinRM password" required>
          </div>
          <button type="submit" class="btn btn-success btn-lg">
            <i class="bi bi-play-fill me-1"></i>Start Patching
          </button>
        </form>
      </div>
      {% endif %}
    </div>
    {% endif %}
  </div>

  <div class="col-lg-5">
    <div class="card shadow-sm">
      <div class="card-header">Required Spreadsheet Columns</div>
      <div class="card-body">
        <table class="table table-sm">
          <thead><tr><th>Column</th><th>Required</th><th>Example</th></tr></thead>
          <tbody>
            <tr><td><code>server_name</code></td><td>Yes</td><td>PROD-WEB-01</td></tr>
            <tr><td><code>ip_address</code></td><td>Yes</td><td>192.168.1.10</td></tr>
            <tr><td><code>restart_window</code></td><td>Yes</td><td>Sunday 02:00</td></tr>
            <tr><td><code>username</code></td><td>No</td><td>DOMAIN\svc</td></tr>
            <tr><td><code>password</code></td><td>No</td><td>(per-server)</td></tr>
          </tbody>
        </table>
        <p class="text-muted small mb-0">
          Restart window formats: <code>Sunday 02:00</code>, <code>Sat 03:30</code>,
          or <code>2026-06-15 02:00</code>
        </p>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Smoke-test the new job page**

Run: `python run.py`
Visit: `http://localhost:5000/jobs/new`
Expected: Upload form renders, sample template link is present.

- [ ] **Step 4: Commit**

```bash
git add app/routes/jobs.py app/templates/new_job.html
git commit -m "feat: new job route — file upload, preview, and job dispatch"
```

---

## Task 9: Job Detail Template + Polling JS

**Files:**
- Create: `app/templates/job_detail.html`
- Create: `app/static/app.js`

- [ ] **Step 1: Create app/templates/job_detail.html**

```html
{% extends "base.html" %}
{% block title %}Job #{{ job_id }}{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-start mb-4">
  <div>
    <h2 class="mb-1">Job #{{ job_id }} — {{ filename }}</h2>
    <small class="text-muted">Started {{ created_at.strftime('%Y-%m-%d %H:%M') }}</small>
  </div>
  <a href="/" class="btn btn-outline-secondary">← All Jobs</a>
</div>

<div class="mb-4">
  <div class="d-flex justify-content-between mb-1">
    <span id="progress-label">{{ progress.done }} / {{ progress.total }} servers complete</span>
    <span id="progress-pct">{{ progress.pct }}%</span>
  </div>
  <div class="progress" style="height:12px">
    <div id="progress-bar" class="progress-bar progress-bar-striped progress-bar-animated"
         style="width:{{ progress.pct }}%"></div>
  </div>
</div>

<div class="card shadow-sm">
  <div class="table-responsive">
    <table class="table table-hover mb-0" id="server-table">
      <thead class="table-dark">
        <tr>
          <th>Server</th><th>IP</th><th>Status</th>
          <th>Updates</th><th>Restart Scheduled</th><th>Actions</th>
        </tr>
      </thead>
      <tbody id="server-tbody">
        {% for s in servers %}
        <tr id="row-{{ s.id }}">
          <td>{{ s.server_name }}</td>
          <td><code>{{ s.ip_address }}</code></td>
          <td>
            <span class="badge badge-{{ s.status }} text-white status-badge">
              {{ s.status | replace('_', ' ') }}
            </span>
            {% if s.error_message %}
            <i class="bi bi-exclamation-circle text-danger ms-1"
               title="{{ s.error_message }}" data-bs-toggle="tooltip"></i>
            {% endif %}
          </td>
          <td>{{ s.updates_installed if s.updates_installed else '—' }}</td>
          <td>{{ s.restart_scheduled_at or '—' }}</td>
          <td>
            <button class="btn btn-sm btn-outline-info me-1"
                    onclick="testConnection({{ s.id }})">Test</button>
            <button class="btn btn-sm btn-outline-warning me-1"
                    onclick="reschedule({{ s.id }})">Reschedule</button>
            <button class="btn btn-sm btn-outline-danger"
                    onclick="manualRestart({{ s.id }})">Restart Now</button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script>
  const JOB_ID = {{ job_id }};
</script>
<script src="/static/app.js"></script>
{% endblock %}
```

- [ ] **Step 2: Create app/static/app.js**

```javascript
const STATUS_COLORS = {
  pending: 'secondary',
  connecting: 'primary',
  checking_module: 'primary',
  checking_updates: 'primary',
  installing: 'primary',
  scheduling_restart: 'primary',
  up_to_date: 'success',
  restart_scheduled: 'success',
  error: 'danger',
};

const STATUS_LABELS = {
  pending: 'Pending',
  connecting: 'Connecting...',
  checking_module: 'Checking module...',
  checking_updates: 'Checking updates...',
  installing: 'Installing updates...',
  scheduling_restart: 'Scheduling restart...',
  up_to_date: 'Up to date',
  restart_scheduled: 'Restart scheduled',
  error: 'Error',
};

let pollInterval = null;

function startPolling() {
  pollInterval = setInterval(pollStatus, 5000);
}

async function pollStatus() {
  try {
    const res = await fetch(`/api/jobs/${JOB_ID}`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('progress-label').textContent =
      `${data.progress.done} / ${data.progress.total} servers complete`;
    document.getElementById('progress-pct').textContent = `${data.progress.pct}%`;
    document.getElementById('progress-bar').style.width = `${data.progress.pct}%`;

    for (const server of data.servers) {
      updateRow(server);
    }

    if (data.progress.pct === 100) {
      clearInterval(pollInterval);
      document.getElementById('progress-bar').classList.remove(
        'progress-bar-striped', 'progress-bar-animated'
      );
    }
  } catch (e) {
    console.error('Poll failed', e);
  }
}

function updateRow(s) {
  const row = document.getElementById(`row-${s.id}`);
  if (!row) return;

  const badge = row.querySelector('.status-badge');
  const color = STATUS_COLORS[s.status] || 'secondary';
  badge.className = `badge text-white status-badge bg-${color}`;
  badge.textContent = STATUS_LABELS[s.status] || s.status.replace(/_/g, ' ');

  const cells = row.querySelectorAll('td');
  cells[3].textContent = s.updates_installed || '—';
  cells[4].textContent = s.restart_scheduled_at
    ? s.restart_scheduled_at.replace('T', ' ').substring(0, 16)
    : '—';
}

async function testConnection(serverId) {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = 'Testing...';
  try {
    const res = await fetch(`/api/servers/${serverId}/test`, { method: 'POST' });
    const data = await res.json();
    alert(data.success ? `Connected: ${data.message}` : `Failed: ${data.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Test';
  }
}

async function manualRestart(serverId) {
  if (!confirm('Trigger an immediate restart on this server?')) return;
  const res = await fetch(`/api/servers/${serverId}/restart`, { method: 'POST' });
  const data = await res.json();
  alert(data.success ? 'Restart initiated.' : `Error: ${data.message}`);
  pollStatus();
}

async function reschedule(serverId) {
  const newWindow = prompt('New restart window (e.g. "Sunday 02:00" or "2026-06-15 02:00"):');
  if (!newWindow) return;
  const res = await fetch(`/api/servers/${serverId}/reschedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ restart_window: newWindow }),
  });
  const data = await res.json();
  alert(data.success ? `Rescheduled for ${data.restart_at}` : `Error: ${data.message}`);
  pollStatus();
}

document.addEventListener('DOMContentLoaded', () => {
  startPolling();
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(el => new bootstrap.Tooltip(el));
});
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/job_detail.html app/static/app.js
git commit -m "feat: job detail page with live polling and server action buttons"
```

---

## Task 10: API Routes

**Files:**
- Modify: `app/routes/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

`tests/test_api.py`:
```python
import pytest
from unittest.mock import patch
from app import create_app
from app.config import TestConfig
from app.database import get_session, Base, engine
from app.models import Job, Server

@pytest.fixture
def app():
    application = create_app(TestConfig.__dict__)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def job_with_server(app):
    s = get_session()
    job = Job(filename='test.csv', status='running')
    s.add(job)
    s.flush()
    server = Server(
        job_id=job.id,
        server_name='TEST-01',
        ip_address='10.0.0.1',
        restart_window='Sunday 02:00',
        status='restart_scheduled',
        updates_installed=5,
    )
    s.add(server)
    s.commit()
    yield {'job_id': job.id, 'server_id': server.id}
    s.delete(server)
    s.delete(job)
    s.commit()
    s.close()

def test_get_job_status(client, job_with_server):
    res = client.get(f'/api/jobs/{job_with_server["job_id"]}')
    assert res.status_code == 200
    data = res.get_json()
    assert 'servers' in data
    assert 'progress' in data
    assert data['servers'][0]['server_name'] == 'TEST-01'

def test_get_job_not_found(client):
    res = client.get('/api/jobs/99999')
    assert res.status_code == 404

def test_test_connection_endpoint_exists(client, job_with_server):
    with patch('app.routes.api.test_connection', return_value=(True, 'Connected')):
        res = client.post(f'/api/servers/{job_with_server["server_id"]}/test')
    assert res.status_code == 200
    assert res.get_json()['success'] is True

def test_reschedule_endpoint_bad_window(client, job_with_server):
    with patch('app.routes.api.reschedule_restart', return_value=(False, 'bad window')):
        res = client.post(
            f'/api/servers/{job_with_server["server_id"]}/reschedule',
            json={'restart_window': 'garbage'}
        )
    assert res.status_code == 200
    assert res.get_json()['success'] is False
```

- [ ] **Step 2: Run to verify tests fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL — routes return 404 or import errors.

- [ ] **Step 3: Implement app/routes/api.py**

```python
from flask import Blueprint, jsonify, request
from app.database import get_session
from app.models import Job, Server, get_or_create_settings
from app.services.crypto import decrypt
from app.services.winrm_worker import test_connection, immediate_restart, reschedule_restart

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.get('/jobs/<int:job_id>')
def job_status(job_id):
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'id': job.id,
            'status': job.status,
            'progress': job.progress(),
            'servers': [s.to_dict() for s in job.servers],
        })
    finally:
        session.close()


def _get_default_credentials(session):
    settings = get_or_create_settings(session)
    username = decrypt(settings.default_username_enc or '') or ''
    password = decrypt(settings.default_password_enc or '') or ''
    return username, password, settings.winrm_port


@bp.post('/servers/<int:server_id>/test')
def test_server_connection(server_id):
    session = get_session()
    try:
        server = session.get(Server, server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404
        username, password, port = _get_default_credentials(session)
        actual_user = server.username or username
    finally:
        session.close()

    success, message = test_connection(server.ip_address, port, actual_user, password)
    return jsonify({'success': success, 'message': message})


@bp.post('/servers/<int:server_id>/restart')
def manual_restart(server_id):
    session = get_session()
    try:
        server = session.get(Server, server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404
        username, password, port = _get_default_credentials(session)
        actual_user = server.username or username
        ip = server.ip_address
    finally:
        session.close()

    success, message = immediate_restart(ip, port, actual_user, password)
    if success:
        session2 = get_session()
        try:
            srv = session2.get(Server, server_id)
            srv.status = 'restarting'
            srv.restart_scheduled_at = None
            session2.commit()
        finally:
            session2.close()
    return jsonify({'success': success, 'message': message})


@bp.post('/servers/<int:server_id>/reschedule')
def reschedule_server(server_id):
    data = request.get_json(silent=True) or {}
    new_window = data.get('restart_window', '').strip()
    if not new_window:
        return jsonify({'success': False, 'message': 'restart_window is required'})

    session = get_session()
    try:
        server = session.get(Server, server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404
        username, password, port = _get_default_credentials(session)
        actual_user = server.username or username
        ip = server.ip_address
    finally:
        session.close()

    success, result = reschedule_restart(ip, port, actual_user, password, new_window)
    if success:
        from datetime import datetime
        session2 = get_session()
        try:
            srv = session2.get(Server, server_id)
            srv.restart_window = new_window
            srv.restart_scheduled_at = datetime.fromisoformat(result)
            srv.status = 'restart_scheduled'
            session2.commit()
        finally:
            session2.close()
        return jsonify({'success': True, 'restart_at': result})
    return jsonify({'success': False, 'message': result})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes/api.py tests/test_api.py
git commit -m "feat: API routes — job status polling, test/restart/reschedule actions"
```

---

## Task 11: Settings Route + Template

**Files:**
- Modify: `app/routes/settings.py`
- Create: `app/templates/settings.html`

- [ ] **Step 1: Implement app/routes/settings.py**

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import get_session
from app.models import AppSettings, get_or_create_settings
from app.services.crypto import encrypt, decrypt

bp = Blueprint('settings', __name__)

@bp.get('/settings')
def settings_form():
    session = get_session()
    try:
        s = get_or_create_settings(session)
        username = decrypt(s.default_username_enc or '') or ''
        return render_template('settings.html',
                               username=username,
                               winrm_port=s.winrm_port,
                               max_workers=s.max_workers)
    finally:
        session.close()


@bp.post('/settings')
def save_settings():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    winrm_port = int(request.form.get('winrm_port', 5985))
    max_workers = int(request.form.get('max_workers', 10))

    session = get_session()
    try:
        s = get_or_create_settings(session)
        s.default_username_enc = encrypt(username) if username else s.default_username_enc
        if password:
            s.default_password_enc = encrypt(password)
        s.winrm_port = winrm_port
        s.max_workers = max_workers
        session.commit()
    finally:
        session.close()

    flash('Settings saved.', 'success')
    return redirect(url_for('settings.settings_form'))
```

- [ ] **Step 2: Create app/templates/settings.html**

```html
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-lg-6">
    <h2 class="mb-4">Settings</h2>
    <div class="card shadow-sm">
      <div class="card-header"><strong>Default WinRM Credentials</strong></div>
      <div class="card-body">
        <form method="post" action="/settings">
          <div class="mb-3">
            <label class="form-label">Default Username</label>
            <input type="text" class="form-control" name="username"
                   value="{{ username }}" placeholder="DOMAIN\svcpatch">
            <div class="form-text">Used when no per-server username is in the spreadsheet.</div>
          </div>
          <div class="mb-3">
            <label class="form-label">Default Password</label>
            <input type="password" class="form-control" name="password"
                   placeholder="Leave blank to keep existing password">
            <div class="form-text">Stored encrypted. Leave blank to keep the current password.</div>
          </div>
          <hr>
          <h6 class="mb-3">WinRM Configuration</h6>
          <div class="row">
            <div class="col-md-6 mb-3">
              <label class="form-label">WinRM Port</label>
              <input type="number" class="form-control" name="winrm_port"
                     value="{{ winrm_port }}" min="1" max="65535">
              <div class="form-text">Default: 5985 (HTTP). Use 5986 for HTTPS.</div>
            </div>
            <div class="col-md-6 mb-3">
              <label class="form-label">Max Concurrent Connections</label>
              <input type="number" class="form-control" name="max_workers"
                     value="{{ max_workers }}" min="1" max="50">
              <div class="form-text">Servers patched in parallel.</div>
            </div>
          </div>
          <button type="submit" class="btn btn-primary">Save Settings</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Smoke-test settings page**

Run: `python run.py`
Visit: `http://localhost:5000/settings`
Expected: Form renders with default values (port 5985, workers 10). Save shows success flash.

- [ ] **Step 4: Commit**

```bash
git add app/routes/settings.py app/templates/settings.html
git commit -m "feat: settings page — default credentials and WinRM configuration"
```

---

## Task 12: Docker + Sample Files

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV UPLOAD_FOLDER=/data/uploads
ENV DATABASE_URL=sqlite:////data/winpatch.db

EXPOSE 5000

CMD ["python", "run.py"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
services:
  winpatch:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - winpatch_data:/data
    environment:
      - DATABASE_URL=sqlite:////data/winpatch.db
      - UPLOAD_FOLDER=/data/uploads
    restart: unless-stopped
    security_opt:
      - apparmor=unconfined

volumes:
  winpatch_data:
```

- [ ] **Step 3: Create .gitignore**

```
.env
*.db
__pycache__/
*.pyc
.pytest_cache/
/tmp/
```

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Final commit and push**

```bash
git add .
git commit -m "feat: Dockerfile and docker-compose for containerized deployment"
git remote set-url origin https://<TOKEN>@github.com/homestead367/WindowsUpdateUtility.git
git push origin main
```

---

## Task 13: WinRM Pre-requisites Note

This is a documentation step — no code, just a note added to the repo so operators know what to do on the Windows side.

- [ ] **Step 1: Create SETUP.md**

`SETUP.md`:
```markdown
# Windows Server Prerequisites

Before running WinPatch against a Windows server, WinRM must be enabled on each target.

## Enable WinRM (run as Administrator on each Windows server)

```powershell
# Enable WinRM with default settings
winrm quickconfig -q

# Allow unencrypted auth over HTTP (required for NTLM on HTTP)
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'

# Open firewall port 5985
netsh advfirewall firewall add rule name="WinRM HTTP" dir=in action=allow protocol=TCP localport=5985
```

## Service Account Requirements

The account used (default credential or per-server) must be a local Administrator
or domain admin on each target server. PSWindowsUpdate requires elevated rights.

## Verify from Linux

```bash
curl -s -o /dev/null -w "%{http_code}" http://<SERVER_IP>:5985/wsman
# Expected: 200
```
```

- [ ] **Step 2: Commit**

```bash
git add SETUP.md
git commit -m "docs: WinRM setup prerequisites for target Windows servers"
```
