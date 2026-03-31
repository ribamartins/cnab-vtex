"""CNAB generation service layer.

Provides file generation, audit logging, and mock transmission.

Exports:
- generate_filename: sequential CNAB filename for today
- generate_cnab_file: full generation pipeline (build, persist, audit)
- log_audit: generic audit log entry creator
- mock_transmit: simulated bank transmission (always succeeds)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models import CnabFile, Payment, AuditLog, Company, User
from cnab.builder import build_cnab, PaymentInput


def _format_value_brl(cents: int) -> str:
    """Convert integer cents to 'R$ 1.500,50' format string."""
    value = cents / 100
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def generate_filename(session) -> str:
    """Generate sequential CNAB filename for today: CNAB_YYYYMMDD_NNN.txt.

    NNN is a zero-padded 3-digit sequential number based on how many
    files were already created today.
    """
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    tomorrow_start = today_start + timedelta(days=1)

    count = (
        session.query(CnabFile)
        .filter(CnabFile.created_at >= today_start)
        .filter(CnabFile.created_at < tomorrow_start)
        .count()
    )
    seq = count + 1
    return f"CNAB_{today.strftime('%Y%m%d')}_{seq:03d}.txt"


def generate_cnab_file(
    session,
    payments: list[PaymentInput],
    company: Company,
    user: User,
    payment_date: date,
) -> CnabFile:
    """Generate a CNAB file from validated payments.

    Steps:
    1. Build CNAB bytes via builder
    2. Create CnabFile record with status 'Criado'
    3. Create Payment records for each PaymentInput
    4. Log audit entry for generation
    5. Flush to get IDs

    Does NOT commit -- caller controls the transaction.
    """
    config = company.to_company_config()
    cnab_bytes = build_cnab(payments, config, payment_date)

    filename = generate_filename(session)
    total_value_cents = sum(int(p.value * 100) for p in payments)

    cnab_file = CnabFile(
        filename=filename,
        file_content=cnab_bytes,
        status='Criado',
        row_count=len(payments),
        total_value_cents=total_value_cents,
        created_by_id=user.id,
        company_id=company.id,
    )
    session.add(cnab_file)

    for p in payments:
        payment_record = Payment(
            name=p.name,
            document=p.document,
            pix_key=p.pix_key,
            pix_key_type=p.pix_key_type,
            value_cents=int(p.value * 100),
            reference_id=p.reference_id,
            cnab_file=cnab_file,
        )
        session.add(payment_record)

    session.flush()

    log_audit(
        session,
        user.id,
        'geracao',
        f'{filename}, {len(payments)} pagamentos, {_format_value_brl(total_value_cents)}',
        'cnab_file',
        cnab_file.id,
    )

    return cnab_file


def log_audit(
    session,
    user_id: int,
    action: str,
    details: str,
    target_type: str = None,
    target_id: int = None,
) -> None:
    """Create an audit log entry.

    Does NOT commit -- caller controls the transaction.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        target_type=target_type,
        target_id=target_id,
    )
    session.add(entry)


def mock_transmit(session, cnab_file: CnabFile, user_id: int) -> None:
    """Simulate bank transmission (always succeeds per D-09).

    Sets status to 'Transmitido' and records transmitted_at timestamp.
    Does NOT commit -- caller controls the transaction.
    """
    cnab_file.status = 'Transmitido'
    cnab_file.transmitted_at = datetime.utcnow()

    log_audit(
        session,
        user_id,
        'transmissao_ok',
        f'{cnab_file.filename} transmitido com sucesso',
        'cnab_file',
        cnab_file.id,
    )


def delete_cnab_file(session, cnab_file: CnabFile, user_id: int) -> None:
    """Delete a CNAB file and its payments. Only allowed for Criado/Erro status.

    Logs an audit entry before deletion.
    Does NOT commit -- caller controls the transaction.
    """
    if cnab_file.status not in ('Criado', 'Erro'):
        raise ValueError(
            f"Apenas arquivos com status Criado ou Erro podem ser excluidos. "
            f"Status atual: {cnab_file.status}"
        )

    filename = cnab_file.filename
    file_id = cnab_file.id

    log_audit(
        session,
        user_id,
        'exclusao',
        f'{filename} excluido ({cnab_file.row_count} pagamentos, '
        f'{_format_value_brl(cnab_file.total_value_cents)})',
        'cnab_file',
        file_id,
    )

    for payment in cnab_file.payments:
        session.delete(payment)
    session.delete(cnab_file)
