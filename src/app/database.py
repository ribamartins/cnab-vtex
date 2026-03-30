"""Database initialization and session management.

Exports:
- get_db_path: returns configured database path
- init_db: creates engine and tables, returns (engine, Session)
- get_session: context manager yielding a session
"""
import os
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SASession


def get_db_path() -> Path:
    """Return the configured SQLite database path.

    Default: ~/.cnab-pix/data.db (per D-09)
    Override: CNAB_DB_PATH environment variable (for tests).
    """
    env_path = os.environ.get('CNAB_DB_PATH')
    if env_path:
        return Path(env_path)
    return Path.home() / '.cnab-pix' / 'data.db'


def init_db(db_path=None):
    """Initialize the database engine and create all tables.

    Args:
        db_path: Optional path override. If None, uses get_db_path().
                 Pass ':memory:' for in-memory SQLite (tests).

    Returns:
        Tuple of (engine, Session factory).
    """
    from app.models import Base

    if db_path is None:
        db_path = get_db_path()

    db_path_str = str(db_path)

    # For file-based DB, ensure parent directory exists
    if db_path_str != ':memory:':
        path_obj = Path(db_path_str)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        connect_url = f'sqlite:///{db_path_str}'
    else:
        connect_url = 'sqlite:///:memory:'

    engine = create_engine(
        connect_url,
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(engine)

    SessionFactory = sessionmaker(bind=engine)
    return engine, SessionFactory


@contextmanager
def get_session(SessionFactory):
    """Context manager yielding a SQLAlchemy session with auto commit/rollback.

    Usage:
        with get_session(Session) as session:
            session.add(obj)
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
