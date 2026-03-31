"""Tests for VTEX enrichment service — TDD suite.

Tests enrich_payments(), _fetch_one(), and _map_to_payment() per Plan 03-01 Task 2.
Uses mocked httpx.Client so no real HTTP calls are made.
"""
import threading
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from vtex.enrichment import EnrichmentResult, enrich_payments


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

SAMPLE_VTEX_RESPONSE = [
    {
        "firstName": "Fabio",
        "lastName": "Michels",
        "document": "51300907134",
        "cpf": None,
        "pixKey": "51300907134",
        "email": "fabmichels@gmail.com",
        "homePhone": "5561999810561",
        "receiverName": "fabio michels",
        "referenceId": "802586",
    }
]

SAMPLE_VTEX_RESPONSE_EMAIL_KEY = [
    {
        "firstName": "Maria",
        "lastName": "Silva",
        "document": "98765432100",
        "cpf": None,
        "pixKey": "maria@example.com",
        "email": "maria@example.com",
        "homePhone": None,
        "receiverName": "Maria Silva",
        "referenceId": "111111",
    }
]


def make_parsed_row(codigo: str, valor: Decimal) -> SimpleNamespace:
    """Return a duck-typed object matching ParsedRow interface."""
    return SimpleNamespace(codigo=codigo, valor=valor, nome="Test User", original_valor=str(valor))


def make_mock_response(json_data, status_code: int = 200) -> MagicMock:
    """Create a mock httpx Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_resp,
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Tests: enrich_payments() — success path
# ---------------------------------------------------------------------------

def test_enrich_payments_success_returns_enrichment_result():
    """enrich_payments() returns list with EnrichmentResult on success."""
    rows = [make_parsed_row("802586", Decimal("1500.50"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response(SAMPLE_VTEX_RESPONSE)

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, EnrichmentResult)
    assert result.error is None
    assert result.payment is not None


def test_enrich_payments_success_populates_payment_fields():
    """enrich_payments() maps VTEX response fields to PaymentInput correctly."""
    rows = [make_parsed_row("802586", Decimal("1500.50"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response(SAMPLE_VTEX_RESPONSE)

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    payment = results[0].payment
    assert payment.name == "Fabio Michels"
    assert payment.document == "51300907134"
    assert payment.pix_key == "51300907134"
    assert payment.pix_key_type == "03"  # CPF detected
    assert payment.value == Decimal("1500.50")
    assert payment.reference_id == "802586"


# ---------------------------------------------------------------------------
# Tests: enrich_payments() — error paths
# ---------------------------------------------------------------------------

def test_enrich_payments_not_found_returns_error():
    """enrich_payments() returns error='Nao encontrado na VTEX' when list is empty."""
    rows = [make_parsed_row("999999", Decimal("100.00"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response([])

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    assert results[0].error == "Nao encontrado na VTEX"
    assert results[0].payment is None


def test_enrich_payments_timeout_returns_error():
    """enrich_payments() returns error='Timeout ao consultar VTEX' on timeout."""
    rows = [make_parsed_row("802586", Decimal("100.00"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = httpx.TimeoutException("timeout")

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    assert results[0].error == "Timeout ao consultar VTEX"
    assert results[0].payment is None


def test_enrich_payments_http_500_returns_error():
    """enrich_payments() returns error containing 'Erro HTTP 500' on HTTP error."""
    rows = [make_parsed_row("802586", Decimal("100.00"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response([], status_code=500)

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    assert "Erro HTTP 500" in results[0].error
    assert results[0].payment is None


def test_enrich_payments_missing_pix_key_returns_error():
    """enrich_payments() returns error='pixKey ausente no registro VTEX' when pixKey missing."""
    vtex_record = [{
        "firstName": "Test",
        "lastName": "User",
        "document": "12345678901",
        "cpf": None,
        "pixKey": None,
        "email": "test@example.com",
        "homePhone": None,
        "receiverName": "Test User",
        "referenceId": "802586",
    }]

    rows = [make_parsed_row("802586", Decimal("100.00"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response(vtex_record)

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    assert results[0].error == "pixKey ausente no registro VTEX"
    assert results[0].payment is None


# ---------------------------------------------------------------------------
# Tests: progress callback and cancellation
# ---------------------------------------------------------------------------

def test_enrich_payments_calls_on_progress_callback():
    """enrich_payments() calls on_progress(current, total) after each row."""
    rows = [
        make_parsed_row("802586", Decimal("100.00")),
        make_parsed_row("111111", Decimal("200.00")),
    ]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response(SAMPLE_VTEX_RESPONSE)

    progress_calls = []

    def on_progress(current, total):
        progress_calls.append((current, total))

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            enrich_payments(rows, app_key="key", app_token="token", on_progress=on_progress)

    assert progress_calls == [(1, 2), (2, 2)]


def test_enrich_payments_stops_early_when_cancel_flag_set():
    """enrich_payments() stops processing when cancel_flag.is_set() is True."""
    rows = [
        make_parsed_row("802586", Decimal("100.00")),
        make_parsed_row("111111", Decimal("200.00")),
        make_parsed_row("222222", Decimal("300.00")),
    ]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response(SAMPLE_VTEX_RESPONSE)

    cancel_flag = threading.Event()
    cancel_flag.set()  # Set immediately — should process 0 rows

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(
                rows, app_key="key", app_token="token", cancel_flag=cancel_flag
            )

    assert len(results) == 0
    mock_client.get.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: document field mapping
# ---------------------------------------------------------------------------

def test_enrich_payments_uses_document_with_cpf_fallback():
    """_map_to_payment() uses 'document' field; falls back to 'cpf' if absent."""
    vtex_record_cpf_fallback = [{
        "firstName": "Test",
        "lastName": "User",
        "document": None,
        "cpf": "12345678901",
        "pixKey": "test@example.com",
        "email": "test@example.com",
        "homePhone": None,
        "receiverName": "Test User",
        "referenceId": "111111",
    }]

    rows = [make_parsed_row("111111", Decimal("100.00"))]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = make_mock_response(vtex_record_cpf_fallback)

    with patch("vtex.enrichment.httpx.Client", return_value=mock_client):
        with patch("vtex.enrichment.time.sleep"):
            results = enrich_payments(rows, app_key="key", app_token="token")

    payment = results[0].payment
    assert payment is not None
    assert payment.document == "12345678901"
