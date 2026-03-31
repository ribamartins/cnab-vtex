"""Validation Report Dialog for CNAB PIX.

Shows consolidated results after VTEX enrichment:
  - Summary bar: X prontos | Y com erros | Z total | R$ value valido
  - Optional warning when some rows will be excluded from CNAB generation
  - Error-rows-only table (VTEX errors + CNAB validation errors)
  - "Gerar CNAB" button (enabled only if >= 1 valid row)
  - "Cancelar" button to discard all results

Merges VTEX enrichment errors with validate_payments() CNAB validation errors
into a single consolidated view (D-13, D-14, D-15, D-16).

Exports:
- ValidationReportDialog: QDialog for the consolidated validation report
"""
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from PySide6.QtGui import QFont

from cnab.validator import validate_payments
from ui.styles import (
    get_app_stylesheet,
    COLOR_DESTRUCTIVE, SPACING_MD, SPACING_SM,
)


def _format_brl(value: Decimal) -> str:
    """Format Decimal as Brazilian currency: R$ 1.500,50"""
    s = f"{value:,.2f}"          # "1,500.50"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # "1.500,50"
    return f"R$ {s}"


class ValidationReportDialog(QDialog):
    """Dialog showing the consolidated enrichment + validation report.

    Constructor:
        results: list[EnrichmentResult] from the VTEX enrichment worker
        session: SQLAlchemy session (passed through, not used internally)

    Validation merge (D-16):
        1. Separate VTEX errors (r.payment is None) from enriched rows
        2. Run validate_payments() on the enriched PaymentInput list
        3. Build valid_rows = enriched rows that had no CNAB validation error
        4. "Gerar CNAB" is enabled iff valid_count >= 1 (D-14)

    Error table contains:
        - VTEX errors (row_index+1, reference_id, error message)
        - CNAB validation errors (enriched row mapped back to 1-based index,
          reference_id, field + message)
    """

    def __init__(self, results: list, session, parent=None):
        super().__init__(parent)
        self._session = session

        # --- Validation merge (D-16) ---
        vtex_errors = [r for r in results if r.payment is None]
        enriched = [r for r in results if r.payment is not None]
        enriched_payments = [r.payment for r in enriched]

        validation_errors = validate_payments(enriched_payments)
        validation_error_indices = {ve.row for ve in validation_errors}

        valid_rows = [
            p for i, p in enumerate(enriched_payments)
            if i not in validation_error_indices
        ]
        self._valid_payments = valid_rows

        # Summary counts
        valid_count = len(valid_rows)
        error_count = len(vtex_errors) + len(validation_errors)
        total_count = len(results)
        valid_total = sum((p.value for p in valid_rows), Decimal("0"))

        # Store for _build_ui
        self._valid_count = valid_count
        self._error_count = error_count
        self._total_count = total_count
        self._valid_total = valid_total
        self._vtex_errors = vtex_errors
        self._validation_errors = validation_errors
        self._enriched = enriched

        self.setWindowTitle("Resultado da Validacao")
        self.setMinimumSize(700, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(get_app_stylesheet())
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build the validation report layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        main_layout.setSpacing(SPACING_SM)

        # --- Summary bar (D-13) ---
        summary_font = QFont()
        summary_font.setPointSize(14)
        summary_font.setWeight(QFont.Weight.Bold)

        summary_label = QLabel(
            f"{self._valid_count} prontos  |  "
            f"{self._error_count} com erros  |  "
            f"{self._total_count} total  |  "
            f"{_format_brl(self._valid_total)} valor valido"
        )
        summary_label.setFont(summary_font)
        summary_label.setWordWrap(True)
        main_layout.addWidget(summary_label)

        # --- Warning label when rows will be excluded (D-15) ---
        excluded = self._total_count - self._valid_count
        if excluded > 0:
            warn_label = QLabel(
                f"{excluded} registro(s) serao excluidos da geracao CNAB"
            )
            warn_label.setStyleSheet(
                f"color: {COLOR_DESTRUCTIVE}; font-size: 13px; font-weight: bold;"
            )
            warn_label.setWordWrap(True)
            main_layout.addWidget(warn_label)

        # --- Error rows table (D-13) ---
        if self._error_count > 0:
            error_label = QLabel("Registros com erro:")
            main_layout.addWidget(error_label)

            error_table = QTableWidget()
            error_table.setColumnCount(4)
            error_table.setHorizontalHeaderLabels(
                ["Linha", "Nome do Beneficiario", "Codigo", "Erro"]
            )
            error_table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.ResizeToContents
            )
            error_table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.Stretch
            )
            error_table.horizontalHeader().setSectionResizeMode(
                2, QHeaderView.ResizeMode.ResizeToContents
            )
            error_table.horizontalHeader().setSectionResizeMode(
                3, QHeaderView.ResizeMode.Stretch
            )
            error_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            error_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            error_table.verticalHeader().setVisible(False)

            # Populate: VTEX errors first
            all_error_rows = []

            for r in self._vtex_errors:
                all_error_rows.append((
                    str(r.row_index + 1),    # 1-based line number
                    r.nome,
                    r.reference_id,
                    r.error or "Erro desconhecido",
                ))

            # Then CNAB validation errors
            for ve in self._validation_errors:
                # ve.row is an index into enriched_payments / self._enriched
                enriched_result = self._enriched[ve.row]
                all_error_rows.append((
                    str(enriched_result.row_index + 1),   # 1-based original line
                    enriched_result.nome,
                    enriched_result.reference_id,
                    f"{ve.field}: {ve.message}",
                ))

            error_table.setRowCount(len(all_error_rows))
            for row_idx, (line, nome, codigo, message) in enumerate(all_error_rows):
                error_table.setItem(row_idx, 0, QTableWidgetItem(line))
                error_table.setItem(row_idx, 1, QTableWidgetItem(nome))
                error_table.setItem(row_idx, 2, QTableWidgetItem(codigo))
                error_table.setItem(row_idx, 3, QTableWidgetItem(message))

            main_layout.addWidget(error_table)
        else:
            # No errors — show a clean all-ok label
            ok_label = QLabel("Todos os registros estao prontos para geracao CNAB.")
            ok_label.setStyleSheet("color: #2E7D32; font-size: 13px;")
            main_layout.addWidget(ok_label)

        main_layout.addStretch()

        # --- Bottom button row (D-14) ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        generate_btn = QPushButton("Gerar CNAB")
        generate_btn.setObjectName("primary")
        generate_btn.setEnabled(self._valid_count >= 1)
        generate_btn.clicked.connect(self.accept)
        btn_layout.addWidget(generate_btn)

        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def valid_payments(self) -> list:
        """Return the list of PaymentInput objects that passed all validation."""
        return self._valid_payments
