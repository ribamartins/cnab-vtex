"""SQLAlchemy 2.0 models for all five CNAB PIX database tables.

Tables:
- companies: Company configuration (maps 1:1 to CompanyConfig dataclass)
- users: Application users with hashed passwords
- cnab_files: Generated CNAB file metadata and content
- payments: Individual payment records within a CNAB file
- audit_logs: Action audit trail
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, LargeBinary,
    String, Text
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from werkzeug.security import generate_password_hash, check_password_hash


class Base(DeclarativeBase):
    """Shared declarative base for all models."""
    pass


class Company(Base):
    """Company configuration -- maps 1:1 to CompanyConfig dataclass.

    Fields match exactly: cnpj, agency, account, dac, name, address,
    address_number, complement, city, cep, state, tipo_pagamento.
    VTEX credentials stored as Fernet ciphertext (D-03).
    """
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    agency: Mapped[str] = mapped_column(String(5), nullable=False)
    account: Mapped[str] = mapped_column(String(12), nullable=False)
    dac: Mapped[str] = mapped_column(String(1), nullable=False)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    address: Mapped[str] = mapped_column(String(30), nullable=False, default='')
    address_number: Mapped[str] = mapped_column(String(5), nullable=False, default='')
    complement: Mapped[str] = mapped_column(String(15), nullable=False, default='')
    city: Mapped[str] = mapped_column(String(20), nullable=False, default='')
    cep: Mapped[str] = mapped_column(String(8), nullable=False, default='')
    state: Mapped[str] = mapped_column(String(2), nullable=False, default='')
    tipo_pagamento: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    # VTEX credentials stored encrypted (Fernet ciphertext per D-03)
    vtex_app_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vtex_app_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cnab_files: Mapped[List['CnabFile']] = relationship('CnabFile', back_populates='company')

    def to_company_config(self):
        """Return a CompanyConfig dataclass instance populated from this model.

        Used to pass company settings to build_cnab().
        """
        from cnab.builder import CompanyConfig
        return CompanyConfig(
            cnpj=self.cnpj,
            agency=self.agency,
            account=self.account,
            dac=self.dac,
            name=self.name,
            address=self.address,
            address_number=self.address_number,
            complement=self.complement,
            city=self.city,
            cep=self.cep,
            state=self.state,
            tipo_pagamento=self.tipo_pagamento,
        )


class User(Base):
    """Application user with hashed password and role-based access (D-07).

    Roles: 'admin' (full access) or 'user' (import/generate/download only).
    Passwords hashed with Werkzeug PBKDF2-SHA256.
    """
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False, default='')
    role: Mapped[str] = mapped_column(String(10), nullable=False, default='user')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default='')

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cnab_files: Mapped[List['CnabFile']] = relationship(
        'CnabFile', back_populates='created_by'
    )
    audit_logs: Mapped[List['AuditLog']] = relationship(
        'AuditLog', back_populates='user'
    )

    def set_password(self, password: str) -> None:
        """Hash and store password using Werkzeug PBKDF2-SHA256."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against stored hash."""
        return check_password_hash(self.password_hash, password)


class CnabFile(Base):
    """Generated CNAB file metadata and raw content.

    Status values: 'Criado', 'Transmitido', 'Erro'.
    File content stored as raw bytes (LATIN-1 encoded CNAB).
    Values stored as integer cents to avoid float precision issues.
    """
    __tablename__ = 'cnab_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='Criado')
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_value_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id'), nullable=False
    )
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('companies.id'), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    transmitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    created_by: Mapped['User'] = relationship('User', back_populates='cnab_files')
    company: Mapped['Company'] = relationship('Company', back_populates='cnab_files')
    payments: Mapped[List['Payment']] = relationship('Payment', back_populates='cnab_file')


class Payment(Base):
    """Individual payment record within a CNAB file.

    Values stored as integer cents.
    Maps directly to PaymentInput dataclass fields.
    """
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cnab_file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('cnab_files.id'), nullable=False
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    document: Mapped[str] = mapped_column(String(14), nullable=False)
    pix_key: Mapped[str] = mapped_column(String(100), nullable=False)
    pix_key_type: Mapped[str] = mapped_column(String(2), nullable=False)
    value_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='Pendente')

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    cnab_file: Mapped['CnabFile'] = relationship('CnabFile', back_populates='payments')


class AuditLog(Base):
    """Action audit trail for all user-initiated operations.

    user_id is nullable to allow system-level audit entries.
    """
    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('users.id'), nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    user: Mapped[Optional['User']] = relationship('User', back_populates='audit_logs')
