import os
import stat
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _bootstrap_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    key = os.urandom(32).hex()
    env_path = Path('.env')
    # Write with mode 0600 so only the owner can read it
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(env_path), flags, 0o600)
    try:
        os.write(fd, f'\nSECRET_KEY={key}\n'.encode())
    finally:
        os.close(fd)
    os.environ['SECRET_KEY'] = key
    return key

class Config:
    SECRET_KEY = _bootstrap_secret_key()
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///winpatch.db')
    WINRM_PORT = int(os.environ.get('WINRM_PORT', 5985))
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 10))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/var/lib/winpatch/uploads')

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key-32-bytes-exactly!'
    WTF_CSRF_ENABLED = False
