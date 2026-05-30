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
