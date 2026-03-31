"""File detail dialog showing CNAB file info, payments table, and action buttons.

Provides download (re-save file_content via Save As) and mock transmission
triggered through TransmissionConfirmDialog.
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QMessageBox, QProgressDialog,
    QApplication, QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Qt, QSettings, QStandardPaths

from ui.styles import (
    get_app_stylesheet, COLOR_ACTIVE, COLOR_INACTIVE, COLOR_DESTRUCTIVE,
    COLOR_BG, SPACING_MD, SPACING_SM,
)


def _format_value_brl(cents: int) -> str:
    """Convert integer cents to 'R$ 1.500,50' format string."""
    value = cents / 100
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


class FileDetailDialog(QDialog):
    """Detail dialog for a single CnabFile record.

    Shows file metadata, payments table, and action buttons:
    - Baixar .txt: re-download file via Save As
    - Transmitir: mock transmission (visible only for Criado status)
    - Fechar: close dialog

    Args:
        cnab_file: CnabFile model instance with payments relationship loaded
        session: SQLAlchemy session
        current_user: Logged-in User object
        parent: Parent widget
    """

    def __init__(self, cnab_file, session, current_user, parent=None):
        super().__init__(parent)
        self._cnab_file = cnab_file
        self._session = session
        self._current_user = current_user
        self._transmitted = False

        self.setWindowTitle(f"Detalhes do Arquivo \u2014 {cnab_file.filename}")
        self.setMinimumSize(700, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(get_app_stylesheet())
        self._build_ui()

    def _build_ui(self):
        """Build dialog layout: file info group, payments table, button row."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        # --- File info QGroupBox ---
        info_group = QGroupBox("Arquivo")
        info_form = QFormLayout(info_group)

        info_form.addRow("Arquivo:", QLabel(self._cnab_file.filename))

        # Status with color
        self._status_label = QLabel(self._cnab_file.status)
        self._status_label.setStyleSheet(self._status_style(self._cnab_file.status))
        info_form.addRow("Status:", self._status_label)

        info_form.addRow(
            "Data:",
            QLabel(self._cnab_file.created_at.strftime('%d/%m/%Y %H:%M')),
        )
        info_form.addRow(
            "Usuario:",
            QLabel(self._cnab_file.created_by.display_name),
        )
        info_form.addRow(
            "Pagamentos:",
            QLabel(str(self._cnab_file.row_count)),
        )
        info_form.addRow(
            "Valor total:",
            QLabel(_format_value_brl(self._cnab_file.total_value_cents)),
        )

        if self._cnab_file.error_details:
            error_label = QLabel(self._cnab_file.error_details)
            error_label.setStyleSheet(f"color: {COLOR_DESTRUCTIVE};")
            info_form.addRow("Erro:", error_label)

        if self._cnab_file.transmitted_at:
            self._transmitted_at_label = QLabel(
                self._cnab_file.transmitted_at.strftime('%d/%m/%Y %H:%M')
            )
            info_form.addRow("Transmitido em:", self._transmitted_at_label)
        else:
            self._transmitted_at_label = None

        layout.addWidget(info_group)

        # --- Payments table ---
        self._payments_table = QTableWidget()
        self._payments_table.setColumnCount(5)
        self._payments_table.setHorizontalHeaderLabels(
            ["#", "Nome", "Codigo", "Valor", "Chave PIX"]
        )

        header = self._payments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self._payments_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._payments_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._payments_table.verticalHeader().setVisible(False)

        # Populate payments
        payments = self._cnab_file.payments
        self._payments_table.setRowCount(len(payments))
        for idx, payment in enumerate(payments):
            # Col 0: row number (1-based)
            num_item = QTableWidgetItem(str(idx + 1))
            self._payments_table.setItem(idx, 0, num_item)

            # Col 1: name
            name_item = QTableWidgetItem(payment.name)
            self._payments_table.setItem(idx, 1, name_item)

            # Col 2: reference_id
            ref_item = QTableWidgetItem(payment.reference_id)
            self._payments_table.setItem(idx, 2, ref_item)

            # Col 3: value (right-aligned)
            value_item = QTableWidgetItem(_format_value_brl(payment.value_cents))
            value_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._payments_table.setItem(idx, 3, value_item)

            # Col 4: PIX key (truncated if > 40 chars)
            pix_key = payment.pix_key
            if len(pix_key) > 40:
                pix_key = pix_key[:40] + "..."
            pix_item = QTableWidgetItem(pix_key)
            self._payments_table.setItem(idx, 4, pix_item)

        layout.addWidget(self._payments_table)

        # --- Button row ---
        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        download_btn = QPushButton("Baixar .txt")
        download_btn.clicked.connect(self._download)
        btn_layout.addWidget(download_btn)

        self._transmit_btn = QPushButton("Transmitir")
        self._transmit_btn.setObjectName("primary")
        self._transmit_btn.clicked.connect(self._transmit)
        self._transmit_btn.setVisible(self._cnab_file.status == 'Criado')
        btn_layout.addWidget(self._transmit_btn)

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _status_style(self, status: str) -> str:
        """Return inline stylesheet for a status label."""
        if status == 'Criado':
            return f"color: {COLOR_INACTIVE}; font-weight: bold;"
        elif status == 'Transmitido':
            return f"color: {COLOR_ACTIVE}; font-weight: bold;"
        elif status == 'Erro':
            return f"color: {COLOR_DESTRUCTIVE}; font-weight: bold;"
        return ""

    def _download(self):
        """Save file_content bytes via native Save As dialog."""
        settings = QSettings("PrettyNew", "CNAB-PIX")
        last_dir = settings.value(
            "last_save_dir",
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            ),
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar arquivo CNAB",
            str(Path(last_dir) / self._cnab_file.filename),
            "Arquivos CNAB (*.txt);;Todos os arquivos (*)",
        )
        if file_path:
            try:
                Path(file_path).write_bytes(self._cnab_file.file_content)
                settings.setValue("last_save_dir", str(Path(file_path).parent))
                from app.cnab_service import log_audit
                log_audit(
                    self._session,
                    self._current_user.id,
                    'download',
                    f'{self._cnab_file.filename} salvo em {file_path}',
                    'cnab_file',
                    self._cnab_file.id,
                )
                self._session.commit()
            except Exception:
                QMessageBox.warning(
                    self,
                    "Erro ao salvar",
                    "Nao foi possivel salvar o arquivo. Verifique permissoes e espaco em disco.",
                )

    def _transmit(self):
        """Trigger mock transmission after user confirmation."""
        from ui.transmission_confirm_dialog import TransmissionConfirmDialog

        confirm = TransmissionConfirmDialog(
            self._cnab_file.row_count,
            self._cnab_file.total_value_cents,
            parent=self,
        )
        if confirm.exec() == QDialog.DialogCode.Accepted:
            progress = QProgressDialog("Aguarde...", None, 0, 0, self)
            progress.setWindowTitle("Transmitindo...")
            progress.setCancelButton(None)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            QApplication.processEvents()

            try:
                from app.cnab_service import mock_transmit
                mock_transmit(self._session, self._cnab_file, self._current_user.id)
                self._session.commit()

                progress.close()

                QMessageBox.information(
                    self,
                    "Transmissao concluida",
                    "Arquivo transmitido com sucesso.",
                )

                self._refresh_after_transmit()
            except Exception as e:
                self._session.rollback()
                progress.close()
                QMessageBox.critical(self, "Erro na transmissao", str(e))

    def _refresh_after_transmit(self):
        """Update UI after successful transmission."""
        self._session.refresh(self._cnab_file)
        self._status_label.setText(self._cnab_file.status)
        self._status_label.setStyleSheet(
            self._status_style(self._cnab_file.status)
        )
        self._transmit_btn.setVisible(False)
        self._transmitted = True

        # Add transmitted_at label if not already present
        if self._cnab_file.transmitted_at and self._transmitted_at_label is None:
            # Find the info form layout and add transmitted_at row
            info_group = self.findChild(QGroupBox, "")
            if info_group:
                form = info_group.layout()
                if form:
                    self._transmitted_at_label = QLabel(
                        self._cnab_file.transmitted_at.strftime('%d/%m/%Y %H:%M')
                    )
                    form.addRow("Transmitido em:", self._transmitted_at_label)

    @property
    def was_modified(self) -> bool:
        """Return True if transmission occurred during this dialog session."""
        return self._transmitted
