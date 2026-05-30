import os
import stat
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

def _bootstrap_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    # Generate a proper Fernet key (32 random bytes, url-safe base64 encoded)
    key = Fernet.generate_key().decode()
    env_path = Path('.env')
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
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # set True when behind HTTPS reverse proxy

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    SECRET_KEY = Fernet.generate_key().decode()  # fresh valid key per test run
    WTF_CSRF_ENABLED = False
