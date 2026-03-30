"""Fernet encryption/decryption and session token management.

Exports:
- encrypt_value: encrypt a plaintext string
- decrypt_value: decrypt a Fernet ciphertext string
- create_session_token: create a signed session token with 30-day expiry
- validate_session_token: validate and decode a session token
- save_session_to_disk: persist token to ~/.cnab-pix/session.json
- load_session_from_disk: load token from disk
- clear_session_from_disk: delete session file
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

# Module-level cache for Fernet instance (reset in tests via _fernet_instance = None)
_fernet_instance = None


def _get_key_path() -> Path:
    """Return the machine-specific encryption key file path.

    Default: ~/.cnab-pix/machine.key (per D-04)
    Override: CNAB_KEY_PATH environment variable (for tests).
    """
    env_path = os.environ.get('CNAB_KEY_PATH')
    if env_path:
        return Path(env_path)
    return Path.home() / '.cnab-pix' / 'machine.key'


def _get_session_path() -> Path:
    """Return the session token file path."""
    return Path.home() / '.cnab-pix' / 'session.json'


def _get_or_create_key() -> bytes:
    """Load existing machine key or generate and persist a new one.

    Machine-specific key auto-generated on first run (D-04).
    """
    key_path = _get_key_path()
    if key_path.exists():
        return key_path.read_bytes()

    # Generate new key and persist
    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    return key


def _get_fernet() -> Fernet:
    """Return cached Fernet instance, creating it if needed."""
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_get_or_create_key())
    return _fernet_instance


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string using the machine Fernet key.

    Returns base64-encoded ciphertext string (ASCII safe).
    """
    return _get_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet ciphertext string.

    Returns original plaintext string.
    Raises InvalidToken if ciphertext is tampered or key mismatch.
    """
    return _get_fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')


def create_session_token(user_id: int) -> str:
    """Create a signed session token encoding user_id with 30-day expiry.

    Token is Fernet-encrypted JSON payload (D-01, D-02).
    """
    now = datetime.utcnow()
    payload = {
        'user_id': user_id,
        'created_at': now.isoformat(),
        'expires_at': (now + timedelta(days=30)).isoformat(),
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    return _get_fernet().encrypt(payload_bytes).decode('ascii')


def validate_session_token(token: str) -> int | None:
    """Validate a session token and return user_id, or None if invalid/expired.

    Returns None if:
    - Token is tampered or cannot be decrypted
    - Token has expired (expires_at <= now)
    - Token format is invalid
    """
    try:
        payload_bytes = _get_fernet().decrypt(token.encode('ascii'))
        payload = json.loads(payload_bytes.decode('utf-8'))
        expires_at = datetime.fromisoformat(payload['expires_at'])
        if expires_at <= datetime.utcnow():
            return None
        return int(payload['user_id'])
    except (InvalidToken, KeyError, ValueError, json.JSONDecodeError, Exception):
        return None


def save_session_to_disk(token: str) -> None:
    """Persist session token to ~/.cnab-pix/session.json."""
    session_path = _get_session_path()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps({'token': token}), encoding='utf-8')


def load_session_from_disk() -> str | None:
    """Load session token from disk, returning None if file missing."""
    session_path = _get_session_path()
    if not session_path.exists():
        return None
    try:
        data = json.loads(session_path.read_text(encoding='utf-8'))
        return data.get('token')
    except (json.JSONDecodeError, KeyError):
        return None


def clear_session_from_disk() -> None:
    """Delete the session token file if it exists."""
    session_path = _get_session_path()
    if session_path.exists():
        session_path.unlink()
