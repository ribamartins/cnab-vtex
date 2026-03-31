"""Audit log viewer dialog with action type and date range filters.

Shows all AuditLog entries in a read-only table with immediate filter refresh.
"""
from datetime import datetime, timedelta, date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Qt, QDate

from ui.styles import get_app_stylesheet, SPACING_MD, SPACING_SM
from app.models import AuditLog


# Map combo display text to DB action values
_ACTION_MAP = {
    "Todas": None,
    "Geracao": "geracao",
    "Download": "download",
    "Transmissao": "transmissao_ok",
    "Erro": "transmissao_erro",
}

# Map DB action values to display text
_ACTION_DISPLAY = {
    "geracao": "Geracao",
    "download": "Download",
    "transmissao_ok": "Transmissao",
    "transmissao_erro": "Erro",
}


class AuditLogDialog(QDialog):
    """Audit log viewer with action and date range filters.

    Args:
        session: SQLAlchemy session
        parent: Parent widget
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session = session

        self.setWindowTitle("Log de Auditoria")
        self.setMinimumSize(800, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(get_app_stylesheet())
        self._build_ui()
        self._refresh_log()

    def _build_ui(self):
        """Build dialog layout: filter row, log table, close button."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        # --- Filter row ---
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Acao:"))
        self._action_filter = QComboBox()
        self._action_filter.addItems(["Todas", "Geracao", "Download", "Transmissao", "Erro"])
        self._action_filter.currentIndexChanged.connect(self._refresh_log)
        filter_row.addWidget(self._action_filter)

        filter_row.addWidget(QLabel("De:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_from.dateChanged.connect(self._refresh_log)
        filter_row.addWidget(self._date_from)

        filter_row.addWidget(QLabel("Ate:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.dateChanged.connect(self._refresh_log)
        filter_row.addWidget(self._date_to)

        filter_row.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        layout.addLayout(filter_row)

        # --- Log table ---
        self._log_table = QTableWidget()
        self._log_table.setColumnCount(4)
        self._log_table.setHorizontalHeaderLabels(
            ["Data/Hora", "Usuario", "Acao", "Detalhes"]
        )

        header = self._log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self._log_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._log_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._log_table.verticalHeader().setVisible(False)

        layout.addWidget(self._log_table)

        # --- Close button row ---
        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _refresh_log(self):
        """Query AuditLog with current filters and repopulate the table."""
        query = (
            self._session.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
        )

        # Action filter
        action_text = self._action_filter.currentText()
        action_value = _ACTION_MAP.get(action_text)
        if action_value is not None:
            query = query.filter(AuditLog.action == action_value)

        # Date range filter
        from_date = self._date_from.date().toPython()
        to_date = self._date_to.date().toPython()
        from_dt = datetime(from_date.year, from_date.month, from_date.day)
        to_dt = datetime(to_date.year, to_date.month, to_date.day) + timedelta(days=1)
        query = query.filter(
            AuditLog.created_at >= from_dt,
            AuditLog.created_at < to_dt,
        )

        entries = query.all()

        # Repopulate table
        self._log_table.setRowCount(len(entries))
        for row_idx, entry in enumerate(entries):
            # Col 0: Data/Hora
            dt_item = QTableWidgetItem(
                entry.created_at.strftime('%d/%m/%Y %H:%M:%S')
            )
            self._log_table.setItem(row_idx, 0, dt_item)

            # Col 1: Usuario
            user_name = entry.user.display_name if entry.user else "Sistema"
            user_item = QTableWidgetItem(user_name)
            self._log_table.setItem(row_idx, 1, user_item)

            # Col 2: Acao (mapped to display)
            action_display = _ACTION_DISPLAY.get(entry.action, entry.action)
            action_item = QTableWidgetItem(action_display)
            self._log_table.setItem(row_idx, 2, action_item)

            # Col 3: Detalhes
            details_item = QTableWidgetItem(entry.details or "")
            self._log_table.setItem(row_idx, 3, details_item)
