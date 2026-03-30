"""Tests for the authentication service functions."""
import os
import pytest
from unittest.mock import patch
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    """Create in-memory SQLite engine with session for auth tests."""
    # Set temp key path so crypto doesn't pollute home dir
    monkeypatch.setenv('CNAB_KEY_PATH', str(tmp_path / 'machine.key'))
    import app.crypto as crypto_module
    crypto_module._fernet_instance = None

    from app.models import Base
    from app.database import init_db

    engine, Session = init_db(':memory:')
    session = Session()
    yield session
    session.close()
    engine.dispose()
    crypto_module._fernet_instance = None


# ---------------------------------------------------------------------------
# authenticate_user tests
# ---------------------------------------------------------------------------

def test_authenticate_user_correct_password(db_session):
    """authenticate_user returns User for correct username/password."""
    from app.auth import create_user, authenticate_user

    create_user(db_session, 'admin', 'password123', 'Admin User', 'admin')
    db_session.commit()

    user = authenticate_user(db_session, 'admin', 'password123')
    assert user is not None
    assert user.username == 'admin'


def test_authenticate_user_wrong_password(db_session):
    """authenticate_user returns None for wrong password."""
    from app.auth import create_user, authenticate_user

    create_user(db_session, 'admin', 'password123', 'Admin User', 'admin')
    db_session.commit()

    result = authenticate_user(db_session, 'admin', 'wrongpassword')
    assert result is None


def test_authenticate_user_nonexistent(db_session):
    """authenticate_user returns None for nonexistent username."""
    from app.auth import authenticate_user

    result = authenticate_user(db_session, 'nonexistent', 'anypassword')
    assert result is None


def test_authenticate_user_inactive(db_session):
    """authenticate_user returns None for inactive user."""
    from app.auth import create_user, deactivate_user, authenticate_user

    user = create_user(db_session, 'inactive', 'password123', 'Inactive User', 'user')
    db_session.commit()
    deactivate_user(db_session, user.id)
    db_session.commit()

    result = authenticate_user(db_session, 'inactive', 'password123')
    assert result is None


# ---------------------------------------------------------------------------
# create_user tests
# ---------------------------------------------------------------------------

def test_create_user_success(db_session):
    """create_user creates user with hashed password and correct role."""
    from app.auth import create_user

    user = create_user(db_session, 'newuser', 'password123', 'New User', 'user')
    db_session.commit()

    assert user.username == 'newuser'
    assert user.role == 'user'
    assert user.password_hash != 'password123'
    assert user.display_name == 'New User'
    assert user.is_active is True


def test_create_user_duplicate_username_raises(db_session):
    """create_user raises ValueError for duplicate username."""
    from app.auth import create_user

    create_user(db_session, 'existing', 'password123', 'First User', 'user')
    db_session.commit()

    with pytest.raises(ValueError, match='usuario'):
        create_user(db_session, 'existing', 'otherpass123', 'Second User', 'user')


def test_create_user_short_password_raises(db_session):
    """create_user raises ValueError for password shorter than 8 chars."""
    from app.auth import create_user

    with pytest.raises(ValueError, match='8'):
        create_user(db_session, 'newuser', 'short', 'New User', 'user')


def test_create_user_invalid_role_raises(db_session):
    """create_user raises ValueError for invalid role."""
    from app.auth import create_user

    with pytest.raises(ValueError, match='[Pp]erfil|role|invalid'):
        create_user(db_session, 'newuser', 'password123', 'New User', 'superadmin')


def test_create_user_admin_role(db_session):
    """create_user creates admin user with role='admin'."""
    from app.auth import create_user

    user = create_user(db_session, 'admin', 'password123', 'Admin User', 'admin')
    db_session.commit()

    assert user.role == 'admin'


# ---------------------------------------------------------------------------
# update_user tests
# ---------------------------------------------------------------------------

def test_update_user_display_name(db_session):
    """update_user updates display_name."""
    from app.auth import create_user, update_user

    user = create_user(db_session, 'testuser', 'password123', 'Old Name', 'user')
    db_session.commit()

    updated = update_user(db_session, user.id, display_name='New Name')
    db_session.commit()

    assert updated.display_name == 'New Name'


def test_update_user_password(db_session):
    """update_user updates password correctly."""
    from app.auth import create_user, update_user, authenticate_user

    user = create_user(db_session, 'testuser', 'oldpassword', 'Test User', 'user')
    db_session.commit()

    update_user(db_session, user.id, password='newpassword123')
    db_session.commit()

    # Old password no longer works
    assert authenticate_user(db_session, 'testuser', 'oldpassword') is None
    # New password works
    assert authenticate_user(db_session, 'testuser', 'newpassword123') is not None


def test_update_user_short_password_raises(db_session):
    """update_user raises ValueError for password shorter than 8 chars."""
    from app.auth import create_user, update_user

    user = create_user(db_session, 'testuser', 'password123', 'Test User', 'user')
    db_session.commit()

    with pytest.raises(ValueError, match='8'):
        update_user(db_session, user.id, password='short')


# ---------------------------------------------------------------------------
# deactivate_user and reactivate_user tests
# ---------------------------------------------------------------------------

def test_deactivate_user(db_session):
    """deactivate_user sets is_active=False."""
    from app.auth import create_user, deactivate_user

    user = create_user(db_session, 'testuser', 'password123', 'Test User', 'user')
    db_session.commit()

    deactivated = deactivate_user(db_session, user.id)
    db_session.commit()

    assert deactivated.is_active is False


def test_deactivate_user_already_inactive_idempotent(db_session):
    """deactivate_user on already-inactive user is idempotent."""
    from app.auth import create_user, deactivate_user

    user = create_user(db_session, 'testuser', 'password123', 'Test User', 'user')
    db_session.commit()

    deactivate_user(db_session, user.id)
    db_session.commit()

    # Second call should not raise
    result = deactivate_user(db_session, user.id)
    db_session.commit()
    assert result.is_active is False


def test_reactivate_user(db_session):
    """reactivate_user sets is_active=True."""
    from app.auth import create_user, deactivate_user, reactivate_user

    user = create_user(db_session, 'testuser', 'password123', 'Test User', 'user')
    db_session.commit()
    deactivate_user(db_session, user.id)
    db_session.commit()

    reactivated = reactivate_user(db_session, user.id)
    db_session.commit()

    assert reactivated.is_active is True


# ---------------------------------------------------------------------------
# get_all_users and has_any_users tests
# ---------------------------------------------------------------------------

def test_get_all_users_returns_list(db_session):
    """get_all_users returns list of all users."""
    from app.auth import create_user, get_all_users

    create_user(db_session, 'user1', 'password123', 'User One', 'user')
    create_user(db_session, 'user2', 'password123', 'User Two', 'admin')
    db_session.commit()

    users = get_all_users(db_session)
    assert len(users) == 2
    usernames = {u.username for u in users}
    assert 'user1' in usernames
    assert 'user2' in usernames


def test_has_any_users_empty_db(db_session):
    """has_any_users returns False on empty database."""
    from app.auth import has_any_users

    assert has_any_users(db_session) is False


def test_has_any_users_with_user(db_session):
    """has_any_users returns True after creating a user."""
    from app.auth import create_user, has_any_users

    create_user(db_session, 'firstuser', 'password123', 'First User', 'admin')
    db_session.commit()

    assert has_any_users(db_session) is True


def test_get_user_by_id(db_session):
    """get_user_by_id returns correct user."""
    from app.auth import create_user, get_user_by_id

    user = create_user(db_session, 'testuser', 'password123', 'Test User', 'user')
    db_session.commit()

    found = get_user_by_id(db_session, user.id)
    assert found is not None
    assert found.username == 'testuser'


def test_get_user_by_id_not_found(db_session):
    """get_user_by_id returns None for nonexistent id."""
    from app.auth import get_user_by_id

    result = get_user_by_id(db_session, 99999)
    assert result is None


# ---------------------------------------------------------------------------
# login_with_session tests
# ---------------------------------------------------------------------------

def test_login_with_session_success(db_session, tmp_path, monkeypatch):
    """login_with_session returns (User, token) on successful login."""
    monkeypatch.setenv('CNAB_KEY_PATH', str(tmp_path / 'machine.key'))
    import app.crypto as crypto_module
    crypto_module._fernet_instance = None

    from app.auth import create_user, login_with_session
    from app.crypto import _get_session_path

    session_file = tmp_path / 'session.json'
    with patch('app.crypto._get_session_path', return_value=session_file):
        create_user(db_session, 'admin', 'password123', 'Admin User', 'admin')
        db_session.commit()

        user, token = login_with_session(db_session, 'admin', 'password123')

    assert user is not None
    assert user.username == 'admin'
    assert token is not None
    assert isinstance(token, str)
    crypto_module._fernet_instance = None


def test_login_with_session_wrong_password(db_session, tmp_path, monkeypatch):
    """login_with_session returns (None, None) on wrong password."""
    monkeypatch.setenv('CNAB_KEY_PATH', str(tmp_path / 'machine.key'))
    import app.crypto as crypto_module
    crypto_module._fernet_instance = None

    from app.auth import create_user, login_with_session

    session_file = tmp_path / 'session.json'
    with patch('app.crypto._get_session_path', return_value=session_file):
        create_user(db_session, 'admin', 'password123', 'Admin User', 'admin')
        db_session.commit()

        user, token = login_with_session(db_session, 'admin', 'wrongpassword')

    assert user is None
    assert token is None
    crypto_module._fernet_instance = None
