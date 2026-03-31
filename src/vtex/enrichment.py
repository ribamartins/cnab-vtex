"""VTEX MasterData enrichment service.

Queries the VTEX MasterData API (entity VV) for each referenceId in the
parsed Excel rows and maps the response to PaymentInput objects.

Exports:
- EnrichmentResult: dataclass for per-row enrichment outcome
- enrich_payments: main entry point for sequential enrichment
"""
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Optional

import httpx

from cnab.builder import PaymentInput
from cnab.pix_key import detect_pix_key_type

# ---------------------------------------------------------------------------
# Constants (D-08)
# ---------------------------------------------------------------------------

VTEX_BASE_URL = "https://prettynew.myvtex.com"
VTEX_SEARCH_PATH = "/api/dataentities/VV/search"
REQUEST_TIMEOUT = 10.0   # seconds
THROTTLE_DELAY = 0.3     # 300ms — within D-08 range of 200-500ms


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentResult:
    """Per-row outcome from the VTEX enrichment service.

    Exactly one of payment or error will be set; the other will be None.
    """
    row_index: int
    reference_id: str
    nome: str
    payment: Optional[PaymentInput]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_payments(
    rows,
    app_key: str,
    app_token: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel_flag=None,
) -> list[EnrichmentResult]:
    """Sequentially query VTEX for each row's referenceId.

    Args:
        rows: list of ParsedRow (or duck-typed objects with .codigo and .valor).
        app_key: VTEX X-VTEX-API-AppKey credential.
        app_token: VTEX X-VTEX-API-AppToken credential.
        on_progress: Optional callback(current: int, total: int) called after
                     each row is processed (D-10).
        cancel_flag: Optional threading.Event; if set, stops processing (D-11).

    Returns:
        list[EnrichmentResult] — one per row processed before cancel or end.
    """
    headers = {
        "X-VTEX-API-AppKey": app_key,
        "X-VTEX-API-AppToken": app_token,
        "Accept": "application/json",
    }
    total = len(rows)
    results: list[EnrichmentResult] = []

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        for idx, row in enumerate(rows):
            # Check cancellation before each request (D-11)
            if cancel_flag and cancel_flag.is_set():
                break

            result = _fetch_one(client, headers, idx, row)
            results.append(result)

            # Progress callback (D-10)
            if on_progress is not None:
                on_progress(idx + 1, total)

            # Throttle between requests — skip sleep after last row (D-08)
            if idx < total - 1:
                time.sleep(THROTTLE_DELAY)

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_one(client: httpx.Client, headers: dict, idx: int, row) -> EnrichmentResult:
    """Perform a single VTEX API call for one row.

    Returns EnrichmentResult with payment on success or error string on failure.
    """
    try:
        resp = client.get(
            VTEX_BASE_URL + VTEX_SEARCH_PATH,
            params={"_fields": "_all", "_where": f"referenceId={row.codigo}"},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()  # VTEX /search returns a LIST (Pitfall 1)

        if not data:
            # No records found for this referenceId (D-09, Pitfall 2)
            return EnrichmentResult(
                row_index=idx,
                reference_id=row.codigo,
                nome=row.nome,
                payment=None,
                error="Nao encontrado na VTEX",
            )

        record = data[0]
        return _map_to_payment(idx, row.codigo, row.nome, record, row.valor)

    except httpx.TimeoutException:
        return EnrichmentResult(
            row_index=idx,
            reference_id=row.codigo,
            nome=row.nome,
            payment=None,
            error="Timeout ao consultar VTEX",
        )
    except httpx.HTTPStatusError as exc:
        return EnrichmentResult(
            row_index=idx,
            reference_id=row.codigo,
            nome=row.nome,
            payment=None,
            error=f"Erro HTTP {exc.response.status_code}",
        )
    except Exception as exc:
        return EnrichmentResult(
            row_index=idx,
            reference_id=row.codigo,
            nome=row.nome,
            payment=None,
            error=f"Erro inesperado: {exc}",
        )


def _map_to_payment(
    idx: int,
    ref_id: str,
    nome: str,
    record: dict,
    valor: Decimal,
) -> EnrichmentResult:
    """Map a VTEX record dict to a PaymentInput dataclass.

    Args:
        idx: Row index (0-based).
        ref_id: The referenceId used for the search.
        record: First element of the VTEX search response list.
        valor: Payment amount (Decimal) from the parsed Excel row.

    Returns:
        EnrichmentResult with payment set, or error if mapping fails.
    """
    pix_key = record.get("pixKey") or ""
    if not pix_key:
        return EnrichmentResult(
            row_index=idx,
            reference_id=ref_id,
            nome=nome,
            payment=None,
            error="pixKey ausente no registro VTEX",
        )

    try:
        pix_key_type = detect_pix_key_type(pix_key)
    except ValueError as exc:
        return EnrichmentResult(
            row_index=idx,
            reference_id=ref_id,
            nome=nome,
            payment=None,
            error=f"Tipo de chave PIX nao reconhecido: {pix_key!r}",
        )

    # Build beneficiary name (Pitfall 7: firstName + lastName, fall back to receiverName)
    first = record.get("firstName") or ""
    last = record.get("lastName") or ""
    name = f"{first} {last}".strip() or record.get("receiverName") or ""

    # Prefer 'document', fall back to 'cpf' (Pitfall 7)
    document = record.get("document") or record.get("cpf") or ""

    payment = PaymentInput(
        name=name,
        document=document,
        pix_key=pix_key,
        pix_key_type=pix_key_type,
        value=valor,
        reference_id=ref_id,
    )

    return EnrichmentResult(
        row_index=idx,
        reference_id=ref_id,
        nome=nome,
        payment=payment,
        error=None,
    )
