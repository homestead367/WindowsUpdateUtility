import pytest
from app.services.file_parser import parse_server_file, validate_restart_windows

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

def test_parse_csv_empty_optional_columns_return_none(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text(
        'server_name,ip_address,restart_window,username,password\n'
        'WEB-01,192.168.1.10,Sunday 02:00,,\n'
    )
    result = parse_server_file(str(csv))
    assert result[0]['username'] is None
    assert result[0]['password'] is None

def test_parse_csv_whitespace_optional_columns_return_none(tmp_path):
    csv = tmp_path / 'servers.csv'
    csv.write_text(
        'server_name,ip_address,restart_window,username,password\n'
        'WEB-01,192.168.1.10,Sunday 02:00,   ,   \n'
    )
    result = parse_server_file(str(csv))
    assert result[0]['username'] is None
    assert result[0]['password'] is None
