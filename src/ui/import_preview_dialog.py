"""Import Preview Dialog for CNAB PIX.

Two-step dialog:
  1. User selects an .xlsx file — shows filename, row count, total value, and
     a preview of the first 10 rows.
  2. User clicks "Continuar" — launches VTEX enrichment in a background QThread
     with a live progress bar. Cancellable at any point.

After enrichment, opens ValidationReportDialog. If accepted, stores valid
PaymentInput list and accepts itself (D-06, D-07, D-10, D-11).

Exports:
- EnrichmentWorker: QThread subclass that runs enrich_payments()
- ImportPreviewDialog: QDialog for file selection, preview, and enrichment
"""
import threading
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QProgressBar, QFileDialog, QMessageBox, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtGui import QFont

from app.excel_parser import parse_excel, ExcelParseError
from app.models import Company
from app.crypto import decrypt_value
from vtex.enrichment import enrich_payments
from ui.styles import (
    get_app_stylesheet,
    COLOR_DESTRUCTIVE, SPACING_MD, SPACING_SM,
)


# ---------------------------------------------------------------------------
# Currency formatting helper
# ---------------------------------------------------------------------------

def _format_brl(value: Decimal) -> str:
    """Format Decimal as Brazilian currency: R$ 1.500,50"""
    s = f"{value:,.2f}"          # "1,500.50"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # "1.500,50"
    return f"R$ {s}"


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class EnrichmentWorker(QThread):
    """QThread that runs enrich_payments() and emits progress / results.

    Signals:
        progress(current: int, total: int)  -- emitted after each row
        finished_signal(results: list)      -- emitted when done (or cancelled)
    """

    progress = Signal(int, int)
    finished_signal = Signal(list)

    def __init__(self, rows, app_key: str, app_token: str, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._app_key = app_key
        self._app_token = app_token
        self._cancel = threading.Event()

    def cancel(self):
        """Signal the worker to stop after the current row."""
        self._cancel.set()

    def run(self):
        """Execute enrichment in a background thread."""
        results = enrich_payments(
            self._rows,
            self._app_key,
            self._app_token,
            on_progress=lambda cur, tot: self.progress.emit(cur, tot),
            cancel_flag=self._cancel,
        )
        self.finished_signal.emit(results)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class ImportPreviewDialog(QDialog):
    """Dialog for Excel import, preview, and VTEX enrichment.

    Constructor:
        session: SQLAlchemy session (used to read Company VTEX credentials)
        current_user: Logged-in User object (unused directly, kept for pattern)

    Flow:
        1. User clicks "Importar Planilha" -> QFileDialog -> parse_excel()
        2. Summary label + preview table are shown; "Continuar" becomes enabled
        3. "Continuar" -> reads Company credentials -> starts EnrichmentWorker
        4. Progress bar updates live; "Cancelar" stops the worker
        5. On completion -> opens ValidationReportDialog
        6. If validated and accepted -> stores valid_payments and accepts self
    """

    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self._session = session
        self._current_user = current_user
        self._worker = None
        self._parse_result = None
        self._valid_payments = []

        self.setWindowTitle("Importar Planilha")
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
        """Build dialog layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        main_layout.setSpacing(SPACING_SM)

        # --- Top: import button ---
        self._import_btn = QPushButton("Importar Planilha")
        self._import_btn.setObjectName("primary")
        self._import_btn.clicked.connect(self._on_import_clicked)
        main_layout.addWidget(self._import_btn)

        # --- Summary label (hidden until file loaded) ---
        self._summary_label = QLabel()
        self._summary_label.setWordWrap(True)
        summary_font = QFont()
        summary_font.setPointSize(11)
        self._summary_label.setFont(summary_font)
        self._summary_label.setVisible(False)
        main_layout.addWidget(self._summary_label)

        # --- Preview table (hidden until file loaded) ---
        self._preview_table = QTableWidget()
        self._preview_table.setColumnCount(4)
        self._preview_table.setHorizontalHeaderLabels(
            ["#", "Nome do Beneficiario", "Codigo", "Valor"]
        )
        self._preview_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._preview_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._preview_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._preview_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._preview_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.setVisible(False)
        main_layout.addWidget(self._preview_table)

        # --- Progress bar (hidden until enrichment starts) ---
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        main_layout.addWidget(self._progress_bar)

        # --- Progress text label (hidden until enrichment starts) ---
        self._progress_label = QLabel()
        self._progress_label.setVisible(False)
        main_layout.addWidget(self._progress_label)

        main_layout.addStretch()

        # --- Bottom button row ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self._cancel_btn)

        self._continue_btn = QPushButton("Continuar")
        self._continue_btn.setObjectName("primary")
        self._continue_btn.setEnabled(False)
        self._continue_btn.clicked.connect(self._on_continue_clicked)
        btn_layout.addWidget(self._continue_btn)

        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_import_clicked(self):
        """Open file picker, parse selected Excel file, show preview."""
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Planilha",
            "",
            "Arquivos Excel (*.xlsx)"
        )
        if not path_str:
            return

        try:
            result = parse_excel(Path(path_str))
        except ExcelParseError as e:
            QMessageBox.warning(self, "Erro na Planilha", str(e))
            return

        self._parse_result = result

        # Update summary label
        self._summary_label.setText(
            f"Arquivo: {result.filename}  |  "
            f"{len(result.rows)} linha(s)  |  "
            f"Total: {_format_brl(result.total_value)}"
        )
        self._summary_label.setVisible(True)

        # Populate preview table (all rows)
        self._preview_table.setRowCount(len(result.rows))
        for row_idx, parsed_row in enumerate(result.rows):
            self._preview_table.setItem(
                row_idx, 0,
                QTableWidgetItem(str(row_idx + 1))
            )
            self._preview_table.setItem(
                row_idx, 1,
                QTableWidgetItem(parsed_row.nome)
            )
            self._preview_table.setItem(
                row_idx, 2,
                QTableWidgetItem(parsed_row.codigo)
            )
            self._preview_table.setItem(
                row_idx, 3,
                QTableWidgetItem(_format_brl(parsed_row.valor))
            )
        self._preview_table.setVisible(True)

        # Enable continue button
        self._continue_btn.setEnabled(True)

    def _on_continue_clicked(self):
        """Read VTEX credentials, launch enrichment worker."""
        company = self._session.query(Company).first()
        if company is None or company.vtex_app_key_encrypted is None:
            QMessageBox.warning(
                self,
                "Credenciais VTEX",
                "Configure as credenciais VTEX em Configuracoes antes de continuar."
            )
            return

        try:
            app_key = decrypt_value(company.vtex_app_key_encrypted)
            app_token = decrypt_value(company.vtex_app_token_encrypted)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Credenciais VTEX",
                f"Nao foi possivel descriptografar as credenciais VTEX: {e}"
            )
            return

        # Prepare progress UI
        self._continue_btn.setEnabled(False)
        total = len(self._parse_result.rows)
        self._progress_bar.setRange(0, total)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._progress_label.setText(f"Consultando VTEX: 0/{total}")
        self._progress_label.setVisible(True)

        # Start worker
        self._worker = EnrichmentWorker(
            self._parse_result.rows,
            app_key,
            app_token,
            parent=self
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_signal.connect(self._on_enrichment_done)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        """Update progress bar and text label."""
        self._progress_bar.setValue(current)
        self._progress_label.setText(f"Consultando VTEX: {current}/{total}")

    def _on_enrichment_done(self, results: list):
        """Open validation report dialog with enrichment results."""
        # Reset progress UI
        self._progress_bar.setVisible(False)
        self._progress_label.setVisible(False)

        from ui.validation_report_dialog import ValidationReportDialog
        report_dialog = ValidationReportDialog(results, self._session, parent=self)
        if report_dialog.exec() == QDialog.DialogCode.Accepted:
            self._valid_payments = report_dialog.valid_payments()
            self.accept()
        else:
            # User cancelled from validation — re-enable continue
            self._continue_btn.setEnabled(True)

    def _on_cancel_clicked(self):
        """Cancel enrichment if running, then close dialog."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()   # Pitfall 4: wait before closing
        self.reject()

    def reject(self):
        """Override to ensure worker is stopped before closing (Pitfall 4)."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()   # Pitfall 4: wait before closing
        super().reject()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def valid_payments(self) -> list:
        """Return the validated PaymentInput list after successful acceptance."""
        return self._valid_payments
