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
