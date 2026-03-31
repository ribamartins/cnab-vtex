"""Transmission confirmation dialog.

Displays payment count and total value, warns the action is irreversible,
and provides Cancelar / Confirmar Transmissao buttons.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Qt

from ui.styles import get_app_stylesheet, COLOR_INACTIVE, SPACING_MD


def _format_value_brl(cents: int) -> str:
    """Convert integer cents to 'R$ 1.500,50' format string."""
    value = cents / 100
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


class TransmissionConfirmDialog(QDialog):
    """Confirmation dialog before mock transmission.

    Shows payment count and total value with an irreversibility warning.
    Fixed size 400x200 per UI-SPEC.

    Args:
        payment_count: Number of payments in the file
        total_value_cents: Total value in integer cents
        parent: Parent widget
    """

    def __init__(self, payment_count: int, total_value_cents: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirmar Transmissao")
        self.setFixedSize(400, 200)
        self.setStyleSheet(get_app_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        # Line 1: confirmation question
        question_label = QLabel(
            f"Transmitir {payment_count} pagamento(s) no valor de "
            f"{_format_value_brl(total_value_cents)}?"
        )
        question_label.setWordWrap(True)
        layout.addWidget(question_label)

        # Line 2: irreversibility warning
        warning_label = QLabel("Esta acao nao pode ser desfeita.")
        warning_label.setStyleSheet(
            f"color: {COLOR_INACTIVE}; font-size: 13px;"
        )
        layout.addWidget(warning_label)

        # Stretch to push buttons to bottom
        layout.addStretch()

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirmar Transmissao")
        confirm_btn.setObjectName("primary")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)
