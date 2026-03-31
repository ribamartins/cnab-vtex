"""Main application window for CNAB PIX.

Minimal shell window for Phase 2.
Menu bar with "Configuracoes" and "Sair" actions.
Status bar shows logged-in user.
Phase 4 will add dashboard content.
"""
from PySide6.QtWidgets import (
    QMainWindow, QLabel, QWidget, QVBoxLayout, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from ui.import_preview_dialog import ImportPreviewDialog


class MainWindow(QMainWindow):
    """Main application window shell.

    Constructor:
        session: SQLAlchemy session
        current_user: Logged-in User object

    Menu bar:
        - "Configuracoes" — opens SettingsWindow
        - "Sair" — logs out and closes the application
    Status bar:
        Shows "Logado como: {display_name} ({role})"
    """

    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self._session = session
        self._current_user = current_user

        self.setWindowTitle("CNAB PIX")
        self.setMinimumSize(800, 600)

        self._build_menu()
        self._build_status_bar()
        self._build_central_widget()

    def _build_menu(self):
        """Build the menu bar with settings and logout actions."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("Arquivo")

        import_action = QAction("Importar Planilha", self)
        import_action.triggered.connect(self._open_import)
        file_menu.addAction(import_action)

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
        """Build placeholder central widget for Phase 2."""
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder = QLabel(
            "CNAB PIX \u2014 Sistema de Pagamentos\n\n"
            "Funcionalidades de importa\u00e7\u00e3o e gera\u00e7\u00e3o de CNAB\n"
            "estar\u00e3o dispon\u00edveis nas pr\u00f3ximas fases."
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        layout.addWidget(placeholder)

        self.setCentralWidget(central)

    def _open_import(self):
        """Open the import dialog to import an Excel file for VTEX enrichment."""
        dialog = ImportPreviewDialog(self._session, self._current_user, parent=self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            valid_payments = dialog.valid_payments()
            # Phase 4 will use valid_payments to generate CNAB file
            # For now, store reference for Phase 4 integration
            self._last_valid_payments = valid_payments

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
