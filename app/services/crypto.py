import os
from cryptography.fernet import Fernet

def _get_fernet() -> Fernet:
    key = os.environ.get('SECRET_KEY', '')
    if not key:
        raise RuntimeError('SECRET_KEY environment variable is not set')
    try:
        return Fernet(key.encode())
    except Exception:
        raise RuntimeError(
            'SECRET_KEY is not a valid Fernet key. '
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ''
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
