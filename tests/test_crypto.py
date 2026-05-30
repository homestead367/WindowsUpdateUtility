import os
import pytest
from cryptography.fernet import Fernet

os.environ['SECRET_KEY'] = Fernet.generate_key().decode()

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

def test_decrypt_empty_string_raises():
    with pytest.raises(Exception):
        decrypt('')

def test_different_values_produce_different_ciphertext():
    assert encrypt('abc') != encrypt('xyz')
