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
