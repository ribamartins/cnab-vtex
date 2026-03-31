"""Excel parser module for CNAB PIX import pipeline.

Reads .xlsx files with exactly three required columns and returns
structured ParseResult objects with Decimal values.

Exports:
- REQUIRED_COLUMNS: list of required column header strings
- ParsedRow: dataclass for a single validated data row
- ParseResult: dataclass for the full parse output
- ExcelParseError: exception for structural parse failures
- parse_excel: main entry point
- _parse_valor: internal currency string parser (exposed for testing)
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import openpyxl


# Column names must match exactly (D-01) — case-sensitive, no fuzzy matching
REQUIRED_COLUMNS = ["Nome do Beneficiario", "Codigo", "Valor"]


class ExcelParseError(Exception):
    """Raised for structural problems in the Excel file (bad columns, invalid values)."""


@dataclass
class ParsedRow:
    """A single parsed and validated data row from the Excel file."""
    nome: str
    codigo: str
    valor: Decimal
    original_valor: str  # Preserves the raw string from Excel before parsing


@dataclass
class ParseResult:
    """Result of parsing the full Excel file."""
    rows: list[ParsedRow]
    total_value: Decimal
    filename: str


def parse_excel(path: Path) -> ParseResult:
    """Parse a .xlsx file with 3 required columns into a ParseResult.

    Args:
        path: Absolute or relative Path to the .xlsx file.

    Returns:
        ParseResult with validated rows, sum total, and filename.

    Raises:
        ExcelParseError: If a required column is missing or a value cannot
                         be parsed.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active

        # Read header row (D-02: header is always row 1)
        header_row = next(ws.iter_rows(min_row=1, max_row=1))
        headers = [
            str(cell.value).strip() if cell.value is not None else ""
            for cell in header_row
        ]

        # Validate all required columns are present
        for col in REQUIRED_COLUMNS:
            if col not in headers:
                raise ExcelParseError(f"Coluna obrigatoria ausente: '{col}'")

        # Build column-name-to-index map
        col_idx = {name: idx for idx, name in enumerate(headers)}

        # Iterate data rows (D-04: skip fully blank rows)
        parsed_rows: list[ParsedRow] = []
        for row_values in ws.iter_rows(min_row=2, values_only=True):
            nome_val = row_values[col_idx["Nome do Beneficiario"]]
            codigo_val = row_values[col_idx["Codigo"]]
            valor_val = row_values[col_idx["Valor"]]

            # Skip fully blank rows (all three values are None)
            if nome_val is None and codigo_val is None and valor_val is None:
                continue

            raw_valor = str(valor_val) if valor_val is not None else ""
            parsed_valor = _parse_valor(raw_valor)

            parsed_rows.append(ParsedRow(
                nome=str(nome_val).strip() if nome_val is not None else "",
                codigo=str(codigo_val).strip() if codigo_val is not None else "",
                valor=parsed_valor,
                original_valor=raw_valor,
            ))
    finally:
        wb.close()

    # Detect duplicate rows with same codigo + valor
    seen: dict[tuple[str, Decimal], int] = {}
    duplicates: list[str] = []
    for i, row in enumerate(parsed_rows):
        key = (row.codigo, row.valor)
        if key in seen:
            duplicates.append(
                f"Linha {i + 2} duplica linha {seen[key] + 2}: "
                f"codigo '{row.codigo}', valor '{row.original_valor}'"
            )
        else:
            seen[key] = i

    if duplicates:
        raise ExcelParseError(
            "Linhas duplicadas encontradas (mesmo codigo e valor):\n"
            + "\n".join(duplicates)
        )

    total_value = sum((row.valor for row in parsed_rows), Decimal("0"))
    return ParseResult(
        rows=parsed_rows,
        total_value=total_value,
        filename=Path(path).name,
    )


def _parse_valor(raw: str) -> Decimal:
    """Parse a Brazilian currency string to Decimal.

    Handles formats: 'R$ 1.500,50', 'R$ 100', 'R$50,00', '1.000,00', '0,50'.

    Args:
        raw: Raw string value from the Excel cell.

    Returns:
        Decimal value without float intermediary (D-03, CNAB-08).

    Raises:
        ExcelParseError: If the string cannot be parsed as a valid currency
                         amount.
    """
    # Strip currency symbol and surrounding whitespace
    cleaned = raw.replace("R$", "").strip()
    # Remove thousands separator (.), then replace decimal comma with dot
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise ExcelParseError(
            f"Valor invalido: '{raw}' (esperado formato 'R$ 1.500,50')"
        )
