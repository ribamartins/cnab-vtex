"""Authentication and user management service.

All functions accept a SQLAlchemy session parameter for testability.
No global session state.

Exports:
- authenticate_user: verify username/password, return User or None
- create_user: create new user with hashed password
- update_user: update user fields
- deactivate_user: set is_active=False (idempotent)
- reactivate_user: set is_active=True
- get_all_users: list all users ordered by display_name
- get_user_by_id: fetch single user by id
- has_any_users: detect empty database (first-run wizard per D-05)
- login_with_session: authenticate + create and save session token
- restore_session: load and validate persisted session token
- logout: clear session from disk
"""
from typing import Optional, Tuple

from app.models import User
from app.crypto import (
    create_session_token,
    save_session_to_disk,
    load_session_from_disk,
    validate_session_token,
    clear_session_from_disk,
)

_VALID_ROLES = ('admin', 'user')


def authenticate_user(session, username: str, password: str) -> Optional[User]:
    """Verify username/password and return User if valid and active.

    Returns None for wrong password, nonexistent user, or inactive user.
    Never reveals whether the username exists.
    """
    user = session.query(User).filter(
        User.username == username,
        User.is_active == True  # noqa: E712
    ).first()

    if user is None:
        return None

    if not user.check_password(password):
        return None

    return user


def create_user(
    session,
    username: str,
    password: str,
    display_name: str,
    role: str = 'user'
) -> User:
    """Create a new user with hashed password.

    Args:
        session: SQLAlchemy session
        username: Unique login name
        password: Plaintext password (min 8 chars)
        display_name: Human-readable name
        role: 'admin' or 'user'

    Returns:
        Newly created User object (not yet committed).

    Raises:
        ValueError: If password too short, username duplicate, or role invalid.
    """
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")

    if role not in _VALID_ROLES:
        raise ValueError(f"Perfil invalido. Use: {', '.join(_VALID_ROLES)}")

    existing = session.query(User).filter(User.username == username).first()
    if existing is not None:
        raise ValueError("Este nome de usuario ja esta em uso.")

    user = User(
        username=username,
        display_name=display_name,
        role=role,
    )
    user.set_password(password)
    session.add(user)
    session.flush()
    return user


def update_user(
    session,
    user_id: int,
    display_name: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
) -> User:
    """Update non-None fields of an existing user.

    Args:
        session: SQLAlchemy session
        user_id: ID of user to update
        display_name: New display name (or None to keep current)
        password: New password (min 8 chars, or None to keep current)
        role: New role (or None to keep current)

    Returns:
        Updated User object.

    Raises:
        ValueError: If password too short or role invalid.
        LookupError: If user_id not found.
    """
    user = session.get(User, user_id)
    if user is None:
        raise LookupError(f"Usuario com id={user_id} nao encontrado.")

    if display_name is not None:
        user.display_name = display_name

    if password is not None:
        if len(password) < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres.")
        user.set_password(password)

    if role is not None:
        if role not in _VALID_ROLES:
            raise ValueError(f"Perfil invalido. Use: {', '.join(_VALID_ROLES)}")
        user.role = role

    session.flush()
    return user


def deactivate_user(session, user_id: int) -> User:
    """Set user is_active=False. Idempotent — safe to call if already inactive.

    Returns:
        Updated User object.

    Raises:
        LookupError: If user_id not found.
    """
    user = session.get(User, user_id)
    if user is None:
        raise LookupError(f"Usuario com id={user_id} nao encontrado.")

    user.is_active = False
    session.flush()
    return user


def reactivate_user(session, user_id: int) -> User:
    """Set user is_active=True.

    Returns:
        Updated User object.

    Raises:
        LookupError: If user_id not found.
    """
    user = session.get(User, user_id)
    if user is None:
        raise LookupError(f"Usuario com id={user_id} nao encontrado.")

    user.is_active = True
    session.flush()
    return user


def get_all_users(session) -> list:
    """Return all users ordered by display_name."""
    return session.query(User).order_by(User.display_name).all()


def get_user_by_id(session, user_id: int) -> Optional[User]:
    """Return user by id, or None if not found."""
    return session.get(User, user_id)


def has_any_users(session) -> bool:
    """Return True if any users exist in the database.

    Used by first-run wizard (D-05) to detect empty database.
    """
    return session.query(User).first() is not None


def login_with_session(
    session,
    username: str,
    password: str,
) -> Tuple[Optional[User], Optional[str]]:
    """Authenticate user and persist session token to disk.

    Returns:
        (User, token_string) on success, (None, None) on failure.
    """
    user = authenticate_user(session, username, password)
    if user is None:
        return (None, None)

    token = create_session_token(user.id)
    save_session_to_disk(token)
    return (user, token)


def restore_session(session) -> Optional[User]:
    """Restore session from disk on app startup (D-01).

    Loads persisted session token, validates it, and returns the
    active User if valid. Returns None if no session or token invalid.
    """
    token = load_session_from_disk()
    if token is None:
        return None

    user_id = validate_session_token(token)
    if user_id is None:
        return None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return None

    return user


def logout() -> None:
    """Clear session token from disk (D-01)."""
    clear_session_from_disk()
