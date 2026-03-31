"""Main application window for CNAB PIX.

Dashboard view with file list table, status/date filters,
and 'Importar Planilha' primary CTA button.
Menu bar with import, audit log, settings, and logout actions.
Status bar shows logged-in user.
"""
from datetime import date, datetime, timedelta

from PySide6.QtWidgets import (
    QMainWindow, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QDateEdit, QPushButton,
    QSpacerItem, QSizePolicy, QProgressDialog, QMessageBox,
    QFileDialog, QApplication,
)
from PySide6.QtCore import Qt, QDate, QSettings, QStandardPaths
from PySide6.QtGui import QAction
from pathlib import Path

from ui.import_preview_dialog import ImportPreviewDialog
from ui.styles import (
    get_app_stylesheet, COLOR_ACTIVE, COLOR_INACTIVE, COLOR_DESTRUCTIVE,
    COLOR_BG, SPACING_LG, SPACING_MD,
)
from app.models import CnabFile, Company


def _format_value_brl(cents: int) -> str:
    """Convert integer cents to 'R$ 1.500,50' format string."""
    value = cents / 100
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


class MainWindow(QMainWindow):
    """Main application window with dashboard file list.

    Constructor:
        session: SQLAlchemy session
        current_user: Logged-in User object

    Dashboard:
        - Toolbar with 'Importar Planilha' button and status/date filters
        - QTableWidget showing generated CNAB files
        - Empty state label when no files exist

    Menu bar:
        - 'Importar Planilha' -- opens import dialog
        - 'Log de Auditoria' -- opens audit log (Plan 02)
        - 'Configuracoes' -- opens settings
        - 'Sair' -- logout and close
    """

    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self._session = session
        self._current_user = current_user
        self._file_records = []

        self.setWindowTitle("CNAB PIX")
        self.setMinimumSize(800, 600)

        self._build_menu()
        self._build_status_bar()
        self._build_central_widget()

    def _build_menu(self):
        """Build the menu bar with import, audit, settings, and logout actions."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("Arquivo")

        import_action = QAction("Importar Planilha", self)
        import_action.triggered.connect(self._open_import)
        file_menu.addAction(import_action)

        audit_action = QAction("Log de Auditoria", self)
        audit_action.triggered.connect(self._open_audit_log)
        file_menu.addAction(audit_action)

        file_menu.addSeparator()

        settings_action = QAction("Configura\u00e7\u00f5es", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        logout_action = QAction("Sair", self)
        logout_action.triggered.connect(self._logout_and_close)
        file_menu.addAction(logout_action)

    def _build_status_bar(self):
        """Build status bar with logged-in user info."""
        role_display = "Administrador" if self._current_user.role == "admin" else "Usu\u00e1rio"
        status_text = f"Logado como: {self._current_user.display_name} ({role_display})"
        self.statusBar().showMessage(status_text)

    def _build_central_widget(self):
        """Build dashboard central widget with toolbar, file table, and empty state."""
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # --- Toolbar row ---
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        import_btn = QPushButton("Importar Planilha")
        import_btn.setObjectName("primary")
        import_btn.clicked.connect(self._open_import)
        toolbar_layout.addWidget(import_btn)

        toolbar_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        # Status filter
        status_label = QLabel("Status:")
        toolbar_layout.addWidget(status_label)

        self._status_filter = QComboBox()
        self._status_filter.addItems(["Todos", "Criado", "Transmitido", "Erro"])
        self._status_filter.currentIndexChanged.connect(self._refresh_table)
        toolbar_layout.addWidget(self._status_filter)

        # Date range filters
        date_from_label = QLabel("De:")
        toolbar_layout.addWidget(date_from_label)

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_from.dateChanged.connect(self._refresh_table)
        toolbar_layout.addWidget(self._date_from)

        date_to_label = QLabel("Ate:")
        toolbar_layout.addWidget(date_to_label)

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.dateChanged.connect(self._refresh_table)
        toolbar_layout.addWidget(self._date_to)

        layout.addWidget(toolbar)

        # --- File list table ---
        self._file_table = QTableWidget()
        self._file_table.setColumnCount(5)
        self._file_table.setHorizontalHeaderLabels(
            ["Data", "Arquivo", "Status", "Pagamentos", "Valor"]
        )

        header = self._file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self._file_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._file_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._file_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self._file_table.doubleClicked.connect(self._open_file_detail)

        layout.addWidget(self._file_table)

        # --- Empty state label ---
        self._empty_label = QLabel(
            "Nenhum arquivo gerado\n\n"
            "Importe uma planilha para iniciar o processo de geracao CNAB."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {COLOR_INACTIVE}; font-size: 15px;")
        layout.addWidget(self._empty_label)

        self.setCentralWidget(central)

        # Initial table load
        self._refresh_table()

    def _refresh_table(self):
        """Query CnabFile records and refresh the dashboard table."""
        query = (
            self._session.query(CnabFile)
            .order_by(CnabFile.created_at.desc())
        )

        # Status filter
        status_text = self._status_filter.currentText()
        if status_text != "Todos":
            query = query.filter(CnabFile.status == status_text)

        # Date range filter
        from_date = self._date_from.date().toPython()
        to_date = self._date_to.date().toPython()
        from_dt = datetime(from_date.year, from_date.month, from_date.day)
        to_dt = datetime(to_date.year, to_date.month, to_date.day) + timedelta(days=1)
        query = query.filter(
            CnabFile.created_at >= from_dt,
            CnabFile.created_at < to_dt,
        )

        self._file_records = query.all()

        # Repopulate table
        self._file_table.setRowCount(len(self._file_records))
        for row_idx, cnab_file in enumerate(self._file_records):
            # Col 0: Data
            date_item = QTableWidgetItem(
                cnab_file.created_at.strftime('%d/%m/%Y %H:%M')
            )
            self._file_table.setItem(row_idx, 0, date_item)

            # Col 1: Arquivo
            name_item = QTableWidgetItem(cnab_file.filename)
            self._file_table.setItem(row_idx, 1, name_item)

            # Col 2: Status badge
            status_label = QLabel(cnab_file.status)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if cnab_file.status == 'Criado':
                status_label.setStyleSheet(f"color: {COLOR_INACTIVE}; font-weight: bold;")
            elif cnab_file.status == 'Transmitido':
                status_label.setStyleSheet(f"color: {COLOR_ACTIVE}; font-weight: bold;")
            elif cnab_file.status == 'Erro':
                status_label.setStyleSheet(f"color: {COLOR_DESTRUCTIVE}; font-weight: bold;")
            self._file_table.setCellWidget(row_idx, 2, status_label)

            # Col 3: Pagamentos (right-aligned)
            count_item = QTableWidgetItem(str(cnab_file.row_count))
            count_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._file_table.setItem(row_idx, 3, count_item)

            # Col 4: Valor (right-aligned)
            value_item = QTableWidgetItem(
                _format_value_brl(cnab_file.total_value_cents)
            )
            value_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._file_table.setItem(row_idx, 4, value_item)

        # Toggle empty state
        has_rows = len(self._file_records) > 0
        self._file_table.setVisible(has_rows)
        self._empty_label.setVisible(not has_rows)

    def _open_file_detail(self, index):
        """Open file detail dialog for the selected row."""
        row = index.row()
        if row < 0 or row >= len(self._file_records):
            return
        cnab_file = self._file_records[row]
        # Refresh from DB to ensure relationships are loaded
        self._session.refresh(cnab_file)
        from ui.file_detail_dialog import FileDetailDialog
        dialog = FileDetailDialog(cnab_file, self._session, self._current_user, parent=self)
        dialog.exec()
        if dialog.was_modified:
            self._refresh_table()

    def _open_import(self):
        """Open the import dialog and trigger CNAB generation on accept."""
        dialog = ImportPreviewDialog(self._session, self._current_user, parent=self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            valid_payments = dialog.valid_payments()
            if valid_payments:
                self._generate_cnab(valid_payments)

    def _generate_cnab(self, valid_payments):
        """Full CNAB generation pipeline: build, save to DB, Save As dialog, audit."""
        from app.cnab_service import generate_cnab_file, log_audit

        # Step 1-2: Show indeterminate progress
        progress = QProgressDialog("Aguarde...", None, 0, 0, self)
        progress.setWindowTitle("Gerando arquivo CNAB...")
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()

        # Step 3: Generate CNAB file
        company = self._session.query(Company).first()
        if not company:
            progress.close()
            QMessageBox.critical(
                self, "Erro",
                "Configuracao da empresa nao encontrada. Configure em Arquivo > Configuracoes."
            )
            return

        try:
            cnab_file = generate_cnab_file(
                session=self._session,
                payments=valid_payments,
                company=company,
                user=self._current_user,
                payment_date=date.today(),
            )
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            progress.close()
            QMessageBox.critical(
                self, "Erro na geracao",
                f"Nao foi possivel gerar o arquivo CNAB. Detalhes: {e}"
            )
            return

        # Step 4: Close progress
        progress.close()

        # Step 5-6: Save As dialog
        settings = QSettings("PrettyNew", "CNAB-PIX")
        last_dir = settings.value(
            "last_save_dir",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation),
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar arquivo CNAB",
            str(Path(last_dir) / cnab_file.filename),
            "Arquivos CNAB (*.txt);;Todos os arquivos (*)",
        )

        if file_path:
            try:
                Path(file_path).write_bytes(cnab_file.file_content)
                settings.setValue("last_save_dir", str(Path(file_path).parent))
                # Log download audit entry
                log_audit(
                    self._session,
                    self._current_user.id,
                    'download',
                    f'{cnab_file.filename} salvo em {file_path}',
                    'cnab_file',
                    cnab_file.id,
                )
                self._session.commit()
            except Exception as e:
                QMessageBox.warning(
                    self, "Erro ao salvar",
                    "Nao foi possivel salvar o arquivo. Verifique permissoes e espaco em disco."
                )

        # Step 7-8: Success message
        QMessageBox.information(self, "Arquivo gerado", "CNAB gerado e salvo com sucesso.")

        # Step 9: Refresh dashboard
        self._refresh_table()

    def _open_audit_log(self):
        """Open the audit log dialog."""
        from ui.audit_log_dialog import AuditLogDialog
        dialog = AuditLogDialog(self._session, parent=self)
        dialog.exec()

    def _open_settings(self):
        """Open the settings window."""
        from ui.settings_window import SettingsWindow
        settings = SettingsWindow(self._session, self._current_user, parent=self)
        settings.exec()

    def _logout_and_close(self):
        """Log out and close the application."""
        from app.auth import logout
        logout()
        self.close()
