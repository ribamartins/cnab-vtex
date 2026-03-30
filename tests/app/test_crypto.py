"""Tests for Fernet encryption and session token management."""
import os
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_key_dir(tmp_path, monkeypatch):
    """Use a temp directory for key file to avoid polluting home dir."""
    key_path = tmp_path / 'machine.key'
    monkeypatch.setenv('CNAB_KEY_PATH', str(key_path))
    # Reset the cached fernet instance in the module
    import importlib
    import app.crypto as crypto_module
    crypto_module._fernet_instance = None
    yield tmp_path
    # Cleanup: reset cached instance
    crypto_module._fernet_instance = None


def test_encrypt_decrypt_round_trip(temp_key_dir):
    """encrypt_value followed by decrypt_value returns original string."""
    from app.crypto import encrypt_value, decrypt_value

    plaintext = 'my-secret-vtex-key'
    encrypted = encrypt_value(plaintext)
    decrypted = decrypt_value(encrypted)
    assert decrypted == plaintext


def test_encrypt_produces_different_ciphertext(temp_key_dir):
    """encrypt_value output is different from plaintext input."""
    from app.crypto import encrypt_value

    plaintext = 'my-secret-vtex-key'
    encrypted = encrypt_value(plaintext)
    assert encrypted != plaintext


def test_encrypt_unicode_round_trip(temp_key_dir):
    """encrypt/decrypt works with unicode characters."""
    from app.crypto import encrypt_value, decrypt_value

    plaintext = 'chave-com-acentos-ção'
    encrypted = encrypt_value(plaintext)
    decrypted = decrypt_value(encrypted)
    assert decrypted == plaintext


def test_session_token_create_and_validate(temp_key_dir):
    """create_session_token(1) returns token; validate returns user_id=1."""
    from app.crypto import create_session_token, validate_session_token

    token = create_session_token(user_id=1)
    assert isinstance(token, str)
    assert len(token) > 0

    user_id = validate_session_token(token)
    assert user_id == 1


def test_session_token_expired_returns_none(temp_key_dir):
    """validate_session_token returns None for token with past expiry."""
    from app.crypto import create_session_token, validate_session_token

    # Create token with past expiry by patching datetime
    past_time = datetime.utcnow() - timedelta(days=31)
    with patch('app.crypto.datetime') as mock_dt:
        mock_dt.utcnow.return_value = past_time
        # Also patch timedelta usage
        token = create_session_token(user_id=42)

    # Now validate (should fail because token already expired)
    result = validate_session_token(token)
    assert result is None


def test_session_token_tampered_returns_none(temp_key_dir):
    """validate_session_token returns None for tampered token."""
    from app.crypto import validate_session_token

    # Feed garbage data as token
    result = validate_session_token('this-is-not-a-valid-token')
    assert result is None


def test_session_token_contains_30_day_expiry(temp_key_dir):
    """Session token encodes 30-day expiry."""
    from app.crypto import create_session_token, _get_fernet
    import json
    import base64

    token = create_session_token(user_id=5)
    fernet = _get_fernet()
    # Decrypt and parse payload
    payload = json.loads(fernet.decrypt(token.encode('ascii')).decode('utf-8'))
    assert 'expires_at' in payload
    assert 'created_at' in payload

    created = datetime.fromisoformat(payload['created_at'])
    expires = datetime.fromisoformat(payload['expires_at'])
    delta = expires - created
    # Should be approximately 30 days (within 1 second tolerance)
    assert 29 * 86400 < delta.total_seconds() <= 30 * 86400 + 1


def test_key_file_auto_created(tmp_path, monkeypatch):
    """Machine key file is auto-created on first call."""
    key_path = tmp_path / 'new_machine.key'
    monkeypatch.setenv('CNAB_KEY_PATH', str(key_path))

    import app.crypto as crypto_module
    crypto_module._fernet_instance = None

    from app.crypto import _get_or_create_key
    assert not key_path.exists()
    key = _get_or_create_key()
    assert key_path.exists()
    assert len(key) > 0
    crypto_module._fernet_instance = None


def test_key_file_reused(tmp_path, monkeypatch):
    """Same key is returned on subsequent calls."""
    key_path = tmp_path / 'stable.key'
    monkeypatch.setenv('CNAB_KEY_PATH', str(key_path))

    import app.crypto as crypto_module
    crypto_module._fernet_instance = None

    from app.crypto import _get_or_create_key
    key1 = _get_or_create_key()
    crypto_module._fernet_instance = None
    key2 = _get_or_create_key()
    assert key1 == key2
    crypto_module._fernet_instance = None


def test_save_load_clear_session(tmp_path, monkeypatch):
    """Session can be saved to disk, loaded back, and cleared."""
    session_path = tmp_path / 'session.json'
    monkeypatch.setenv('CNAB_KEY_PATH', str(tmp_path / 'machine.key'))

    import app.crypto as crypto_module
    crypto_module._fernet_instance = None

    from app.crypto import save_session_to_disk, load_session_from_disk, clear_session_from_disk

    # Patch _get_session_path to use temp dir
    with patch('app.crypto._get_session_path', return_value=session_path):
        save_session_to_disk('mytoken123')
        loaded = load_session_from_disk()
        assert loaded == 'mytoken123'

        clear_session_from_disk()
        loaded_after_clear = load_session_from_disk()
        assert loaded_after_clear is None

    crypto_module._fernet_instance = None


def test_load_session_missing_file(tmp_path, monkeypatch):
    """load_session_from_disk returns None if session file doesn't exist."""
    session_path = tmp_path / 'nonexistent_session.json'

    from app.crypto import load_session_from_disk
    with patch('app.crypto._get_session_path', return_value=session_path):
        result = load_session_from_disk()
        assert result is None
