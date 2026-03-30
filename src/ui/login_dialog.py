"""Login dialog for CNAB PIX application.

Window title: "CNAB PIX — Acesso"
Fixed size 350x250, non-resizable, centered on screen.
Authenticates via login_with_session() from app.auth.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.styles import COLOR_DESTRUCTIVE, SPACING_MD, SPACING_SM


class LoginDialog(QDialog):
    """Login dialog with username/password fields and session persistence.

    Constructor:
        session: SQLAlchemy session used for authentication.

    On successful login:
        self.logged_in_user is set to the authenticated User object.
        self.accept() is called.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session = session
        self.logged_in_user = None

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._center_on_screen()

    def _setup_window(self):
        """Configure window properties per UI-SPEC interaction contract."""
        self.setWindowTitle("CNAB PIX \u2014 Acesso")
        self.setFixedSize(350, 280)
        # Remove resize/maximize — fixed size dialog
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )

    def _build_ui(self):
        """Build the login form layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        main_layout.setSpacing(SPACING_MD)

        # Title
        title_label = QLabel("CNAB PIX \u2014 Acesso")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Form layout for fields
        form_layout = QFormLayout()
        form_layout.setSpacing(SPACING_SM)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._username_field = QLineEdit()
        self._username_field.setPlaceholderText("Digite seu usuario")
        form_layout.addRow("Usu\u00e1rio:", self._username_field)

        self._password_field = QLineEdit()
        self._password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_field.setPlaceholderText("Digite sua senha")
        form_layout.addRow("Senha:", self._password_field)

        main_layout.addLayout(form_layout)

        # Error label — hidden initially
        self._error_label = QLabel("Usu\u00e1rio ou senha incorretos.")
        self._error_label.setStyleSheet(f"color: {COLOR_DESTRUCTIVE}; font-size: 12px;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setVisible(False)
        main_layout.addWidget(self._error_label)

        # Spacer
        main_layout.addStretch()

        # Login button
        self._login_btn = QPushButton("Entrar")
        self._login_btn.setObjectName("primary")
        self._login_btn.setMinimumHeight(36)
        main_layout.addWidget(self._login_btn)

    def _connect_signals(self):
        """Connect button and key press signals."""
        self._login_btn.clicked.connect(self._on_submit)
        # Enter key in password field triggers submit
        self._password_field.returnPressed.connect(self._on_submit)
        self._username_field.returnPressed.connect(self._password_field.setFocus)
        # Clear error on any keystroke
        self._username_field.textChanged.connect(self._clear_error)
        self._password_field.textChanged.connect(self._clear_error)

    def _center_on_screen(self):
        """Center dialog on screen per UI-SPEC interaction contract."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(screen_geo.x() + x, screen_geo.y() + y)

    def _clear_error(self):
        """Hide error label when user starts typing."""
        self._error_label.setVisible(False)

    def _set_loading(self, loading: bool):
        """Toggle loading state on the login button per UI-SPEC."""
        if loading:
            self._login_btn.setText("Verificando...")
            self._login_btn.setEnabled(False)
        else:
            self._login_btn.setText("Entrar")
            self._login_btn.setEnabled(True)

    def _on_submit(self):
        """Handle login form submission."""
        username = self._username_field.text().strip()
        password = self._password_field.text()

        if not username or not password:
            self._error_label.setVisible(True)
            return

        self._set_loading(True)
        self._error_label.setVisible(False)

        # Process events so UI updates before blocking call
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            from app.auth import login_with_session
            user, token = login_with_session(self._session, username, password)
        except Exception:
            user = None

        self._set_loading(False)

        if user is not None:
            self.logged_in_user = user
            self.accept()
        else:
            self._error_label.setVisible(True)
            self._password_field.setFocus()
            self._password_field.selectAll()
