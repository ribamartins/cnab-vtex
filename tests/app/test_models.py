"""Tests for SQLAlchemy models and database initialization."""
import os
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def engine_and_session():
    """Create in-memory SQLite engine with all tables."""
    # Import here so PYTHONPATH is used correctly
    from app.models import Base
    from app.database import init_db

    os.environ['CNAB_DB_PATH'] = ':memory:'
    engine, Session = init_db(':memory:')
    session = Session()
    yield engine, session
    session.close()
    engine.dispose()


def test_creates_five_tables(engine_and_session):
    """init_db creates all five required tables."""
    engine, session = engine_and_session
    table_names = set(inspect(engine).get_table_names())
    assert 'companies' in table_names
    assert 'users' in table_names
    assert 'cnab_files' in table_names
    assert 'payments' in table_names
    assert 'audit_logs' in table_names
    assert len(table_names) == 5


def test_user_password_hashing(engine_and_session):
    """User.set_password stores hash, not plaintext."""
    engine, session = engine_and_session
    from app.models import User

    user = User(username='testuser', display_name='Test User', role='user')
    user.set_password('mysecretpassword')
    assert user.password_hash != 'mysecretpassword'
    assert user.password_hash is not None
    assert len(user.password_hash) > 20


def test_user_check_password_correct(engine_and_session):
    """User.check_password returns True for correct password."""
    engine, session = engine_and_session
    from app.models import User

    user = User(username='testuser', display_name='Test User', role='user')
    user.set_password('correctpassword123')
    assert user.check_password('correctpassword123') is True


def test_user_check_password_wrong(engine_and_session):
    """User.check_password returns False for wrong password."""
    engine, session = engine_and_session
    from app.models import User

    user = User(username='testuser', display_name='Test User', role='user')
    user.set_password('correctpassword123')
    assert user.check_password('wrongpassword') is False


def test_company_has_all_twelve_fields(engine_and_session):
    """Company model has all 12 fields matching CompanyConfig."""
    engine, session = engine_and_session
    from app.models import Company

    required_fields = [
        'cnpj', 'agency', 'account', 'dac', 'name', 'address',
        'address_number', 'complement', 'city', 'cep', 'state', 'tipo_pagamento'
    ]
    company = Company()
    for field in required_fields:
        assert hasattr(company, field), f"Company missing field: {field}"


def test_company_to_company_config(engine_and_session):
    """Company.to_company_config() returns a CompanyConfig dataclass."""
    engine, session = engine_and_session
    from app.models import Company
    from cnab.builder import CompanyConfig

    company = Company(
        cnpj='12345678000195',
        agency='1234',
        account='123456789012',
        dac='0',
        name='Test Company',
        address='Rua Teste',
        address_number='123',
        complement='Sala 1',
        city='Sao Paulo',
        cep='01310100',
        state='SP',
        tipo_pagamento=20
    )
    config = company.to_company_config()
    assert isinstance(config, CompanyConfig)
    assert config.cnpj == '12345678000195'
    assert config.agency == '1234'
    assert config.account == '123456789012'
    assert config.dac == '0'
    assert config.name == 'Test Company'
    assert config.address == 'Rua Teste'
    assert config.address_number == '123'
    assert config.complement == 'Sala 1'
    assert config.city == 'Sao Paulo'
    assert config.cep == '01310100'
    assert config.state == 'SP'
    assert config.tipo_pagamento == 20


def test_user_model_tablename(engine_and_session):
    """User model uses correct table name."""
    engine, session = engine_and_session
    from app.models import User
    assert User.__tablename__ == 'users'


def test_company_model_tablename(engine_and_session):
    """Company model uses correct table name."""
    engine, session = engine_and_session
    from app.models import Company
    assert Company.__tablename__ == 'companies'


def test_cnab_file_model_tablename(engine_and_session):
    """CnabFile model uses correct table name."""
    engine, session = engine_and_session
    from app.models import CnabFile
    assert CnabFile.__tablename__ == 'cnab_files'


def test_payment_model_tablename(engine_and_session):
    """Payment model uses correct table name."""
    engine, session = engine_and_session
    from app.models import Payment
    assert Payment.__tablename__ == 'payments'


def test_audit_log_model_tablename(engine_and_session):
    """AuditLog model uses correct table name."""
    engine, session = engine_and_session
    from app.models import AuditLog
    assert AuditLog.__tablename__ == 'audit_logs'


def test_user_default_role_is_user(engine_and_session):
    """User default role is 'user'."""
    engine, session = engine_and_session
    from app.models import User

    user = User(username='testuser', display_name='Test User')
    session.add(user)
    user.set_password('password123')
    session.flush()
    assert user.role == 'user'


def test_user_is_active_default(engine_and_session):
    """User is_active defaults to True."""
    engine, session = engine_and_session
    from app.models import User

    user = User(username='testuser', display_name='Test User', role='user')
    user.set_password('password123')
    session.add(user)
    session.flush()
    assert user.is_active is True
