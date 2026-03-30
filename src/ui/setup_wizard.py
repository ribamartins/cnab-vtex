"""First-run setup wizard for CNAB PIX application.

Window title: "Configuracao Inicial"
Two-step flow via QStackedWidget:
  Step 1: Create admin user (username, password, confirm password, display name)
  Step 2: Company data (all 12 CompanyConfig fields)

Creates admin user via create_user() and Company record on completion.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QStackedWidget,
    QComboBox, QWidget, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.styles import COLOR_DESTRUCTIVE, COLOR_BG, SPACING_MD, SPACING_SM, SPACING_LG


# Brazilian state abbreviations
BR_STATES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]


class SetupWizard(QDialog):
    """First-run wizard to create admin user and company configuration.

    Constructor:
        session: SQLAlchemy session for creating user and company records.

    On successful completion:
        Admin user and Company are created and committed.
        self.accept() is called.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session = session
        self._admin_data = {}  # Stores step 1 data for step 2 use

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._validate_step1()  # Set initial button state

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Configura\u00e7\u00e3o Inicial")
        self.setMinimumSize(500, 600)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )

    def _build_ui(self):
        """Build the two-step wizard layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        main_layout.setSpacing(SPACING_MD)

        # Header
        title_label = QLabel("Configura\u00e7\u00e3o Inicial")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        subtitle_label = QLabel(
            "Configure o administrador e os dados da empresa para come\u00e7ar."
        )
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)
        main_layout.addWidget(subtitle_label)

        # Step indicator
        self._step_label = QLabel("Passo 1 de 2: Criar Administrador")
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_label.setStyleSheet("color: #616161; font-size: 12px;")
        main_layout.addWidget(self._step_label)

        # Stacked widget for two steps
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, 1)

        # Build both steps
        self._step1_widget = self._build_step1()
        self._step2_widget = self._build_step2()
        self._stack.addWidget(self._step1_widget)
        self._stack.addWidget(self._step2_widget)
        self._stack.setCurrentIndex(0)

    def _build_step1(self) -> QWidget:
        """Build Step 1 — Create Admin form."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        form = QFormLayout()
        form.setSpacing(SPACING_SM)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._s1_display_name = QLineEdit()
        self._s1_display_name.setPlaceholderText("Ex: Jo\u00e3o da Silva")
        form.addRow("Nome Completo:", self._s1_display_name)
        self._s1_display_name_error = self._make_error_label()
        form.addRow("", self._s1_display_name_error)

        self._s1_username = QLineEdit()
        self._s1_username.setPlaceholderText("Ex: joao.silva")
        form.addRow("Usu\u00e1rio:", self._s1_username)
        self._s1_username_error = self._make_error_label()
        form.addRow("", self._s1_username_error)

        self._s1_password = QLineEdit()
        self._s1_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._s1_password.setPlaceholderText("M\u00ednimo 8 caracteres")
        form.addRow("Senha:", self._s1_password)
        self._s1_password_error = self._make_error_label()
        form.addRow("", self._s1_password_error)

        self._s1_confirm_password = QLineEdit()
        self._s1_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._s1_confirm_password.setPlaceholderText("Repita a senha")
        form.addRow("Confirmar Senha:", self._s1_confirm_password)
        self._s1_confirm_error = self._make_error_label()
        form.addRow("", self._s1_confirm_error)

        layout.addLayout(form)
        layout.addStretch()

        # Next button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._next_btn = QPushButton("Pr\u00f3ximo")
        self._next_btn.setObjectName("primary")
        self._next_btn.setMinimumWidth(120)
        btn_layout.addWidget(self._next_btn)
        layout.addLayout(btn_layout)

        return widget

    def _build_step2(self) -> QWidget:
        """Build Step 2 — Company Data form."""
        # Use scroll area for long form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        form = QFormLayout()
        form.setSpacing(SPACING_SM)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._s2_cnpj = QLineEdit()
        self._s2_cnpj.setPlaceholderText("14 d\u00edgitos sem pontua\u00e7\u00e3o")
        self._s2_cnpj.setMaxLength(14)
        form.addRow("CNPJ:", self._s2_cnpj)
        self._s2_cnpj_error = self._make_error_label()
        form.addRow("", self._s2_cnpj_error)

        self._s2_agency = QLineEdit()
        self._s2_agency.setPlaceholderText("At\u00e9 5 d\u00edgitos")
        self._s2_agency.setMaxLength(5)
        form.addRow("Ag\u00eancia:", self._s2_agency)

        self._s2_account = QLineEdit()
        self._s2_account.setPlaceholderText("At\u00e9 12 d\u00edgitos")
        self._s2_account.setMaxLength(12)
        form.addRow("Conta:", self._s2_account)

        self._s2_dac = QLineEdit()
        self._s2_dac.setPlaceholderText("1 d\u00edgito")
        self._s2_dac.setMaxLength(1)
        form.addRow("DAC:", self._s2_dac)

        self._s2_name = QLineEdit()
        self._s2_name.setPlaceholderText("Nome da empresa (m\u00e1x. 30 chars)")
        self._s2_name.setMaxLength(30)
        form.addRow("Nome da Empresa:", self._s2_name)

        self._s2_address = QLineEdit()
        self._s2_address.setPlaceholderText("Rua/Avenida (m\u00e1x. 30 chars)")
        self._s2_address.setMaxLength(30)
        form.addRow("Endere\u00e7o:", self._s2_address)

        self._s2_address_number = QLineEdit()
        self._s2_address_number.setPlaceholderText("N\u00famero")
        self._s2_address_number.setMaxLength(5)
        form.addRow("N\u00famero:", self._s2_address_number)

        self._s2_complement = QLineEdit()
        self._s2_complement.setPlaceholderText("Apto, sala, etc. (m\u00e1x. 15 chars)")
        self._s2_complement.setMaxLength(15)
        form.addRow("Complemento:", self._s2_complement)

        self._s2_city = QLineEdit()
        self._s2_city.setPlaceholderText("Cidade (m\u00e1x. 20 chars)")
        self._s2_city.setMaxLength(20)
        form.addRow("Cidade:", self._s2_city)

        self._s2_cep = QLineEdit()
        self._s2_cep.setPlaceholderText("8 d\u00edgitos sem h\u00edfen")
        self._s2_cep.setMaxLength(8)
        form.addRow("CEP:", self._s2_cep)

        self._s2_state = QComboBox()
        self._s2_state.addItems(BR_STATES)
        self._s2_state.setCurrentText("SP")
        form.addRow("Estado:", self._s2_state)

        self._s2_tipo_pagamento = QComboBox()
        self._s2_tipo_pagamento.addItem("Fornecedores (20)", 20)
        self._s2_tipo_pagamento.addItem("Diversos (98)", 98)
        form.addRow("Tipo de Pagamento:", self._s2_tipo_pagamento)

        layout.addLayout(form)
        layout.addStretch()

        # General error label
        self._s2_general_error = self._make_error_label()
        layout.addWidget(self._s2_general_error)

        # Submit button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._create_btn = QPushButton("Criar Administrador")
        self._create_btn.setObjectName("primary")
        self._create_btn.setMinimumWidth(160)
        btn_layout.addWidget(self._create_btn)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        return scroll

    def _make_error_label(self) -> QLabel:
        """Create a hidden error label with standard styling."""
        label = QLabel()
        label.setStyleSheet(f"color: {COLOR_DESTRUCTIVE}; font-size: 12px;")
        label.setVisible(False)
        return label

    def _connect_signals(self):
        """Connect all signals."""
        self._next_btn.clicked.connect(self._go_to_step2)
        self._create_btn.clicked.connect(self._on_create)

        # Real-time validation for step 1
        self._s1_display_name.textChanged.connect(self._validate_step1)
        self._s1_username.textChanged.connect(self._validate_step1)
        self._s1_password.textChanged.connect(self._validate_step1)
        self._s1_confirm_password.textChanged.connect(self._validate_step1)

        # Confirm password blur validation
        self._s1_confirm_password.editingFinished.connect(self._validate_confirm_password)
        self._s1_password.editingFinished.connect(self._validate_password_length)

    def _validate_step1(self):
        """Enable/disable Next button based on step 1 validation."""
        display_name = self._s1_display_name.text().strip()
        username = self._s1_username.text().strip()
        password = self._s1_password.text()
        confirm = self._s1_confirm_password.text()

        all_filled = bool(display_name and username and password and confirm)
        passwords_match = password == confirm
        password_long_enough = len(password) >= 8

        is_valid = all_filled and passwords_match and password_long_enough
        self._next_btn.setEnabled(is_valid)

    def _validate_password_length(self):
        """Show password length error on blur."""
        password = self._s1_password.text()
        if password and len(password) < 8:
            self._s1_password_error.setText("A senha deve ter pelo menos 8 caracteres.")
            self._s1_password_error.setVisible(True)
        else:
            self._s1_password_error.setVisible(False)

    def _validate_confirm_password(self):
        """Show password mismatch error on blur per UI-SPEC."""
        password = self._s1_password.text()
        confirm = self._s1_confirm_password.text()
        if confirm and password != confirm:
            self._s1_confirm_error.setText("As senhas n\u00e3o coincidem.")
            self._s1_confirm_error.setVisible(True)
        else:
            self._s1_confirm_error.setVisible(False)

    def _go_to_step2(self):
        """Advance to step 2 after saving step 1 data."""
        # Store step 1 data
        self._admin_data = {
            'display_name': self._s1_display_name.text().strip(),
            'username': self._s1_username.text().strip(),
            'password': self._s1_password.text(),
        }
        self._step_label.setText("Passo 2 de 2: Dados da Empresa")
        self._stack.setCurrentIndex(1)

    def _on_create(self):
        """Create admin user and company, then close wizard."""
        # Validate required company fields
        errors = self._validate_step2()
        if errors:
            self._s2_general_error.setText("\n".join(errors))
            self._s2_general_error.setVisible(True)
            return

        self._s2_general_error.setVisible(False)
        self._create_btn.setEnabled(False)
        self._create_btn.setText("Criando...")

        try:
            from app.auth import create_user
            from app.models import Company

            # Create admin user
            create_user(
                self._session,
                username=self._admin_data['username'],
                password=self._admin_data['password'],
                display_name=self._admin_data['display_name'],
                role='admin'
            )

            # Create company record
            tipo_pagamento = self._s2_tipo_pagamento.currentData()
            company = Company(
                cnpj=self._s2_cnpj.text().strip(),
                agency=self._s2_agency.text().strip(),
                account=self._s2_account.text().strip(),
                dac=self._s2_dac.text().strip(),
                name=self._s2_name.text().strip(),
                address=self._s2_address.text().strip(),
                address_number=self._s2_address_number.text().strip(),
                complement=self._s2_complement.text().strip(),
                city=self._s2_city.text().strip(),
                cep=self._s2_cep.text().strip(),
                state=self._s2_state.currentText(),
                tipo_pagamento=tipo_pagamento,
            )
            self._session.add(company)
            self._session.commit()
            self.accept()

        except ValueError as e:
            self._s2_general_error.setText(str(e))
            self._s2_general_error.setVisible(True)
            self._create_btn.setEnabled(True)
            self._create_btn.setText("Criar Administrador")
        except Exception as e:
            self._s2_general_error.setText(
                "Erro ao salvar. Verifique os dados e tente novamente."
            )
            self._s2_general_error.setVisible(True)
            self._create_btn.setEnabled(True)
            self._create_btn.setText("Criar Administrador")

    def _validate_step2(self) -> list:
        """Validate step 2 required fields. Returns list of error messages."""
        errors = []

        required_fields = [
            (self._s2_cnpj, "CNPJ"),
            (self._s2_agency, "Ag\u00eancia"),
            (self._s2_account, "Conta"),
            (self._s2_dac, "DAC"),
            (self._s2_name, "Nome da Empresa"),
        ]

        for field, label in required_fields:
            if not field.text().strip():
                errors.append(f"{label}: Este campo \u00e9 obrigat\u00f3rio.")

        # CNPJ format validation
        cnpj = self._s2_cnpj.text().strip()
        if cnpj and (not cnpj.isdigit() or len(cnpj) != 14):
            errors.append("CNPJ inv\u00e1lido. Informe 14 d\u00edgitos sem pontua\u00e7\u00e3o.")

        return errors
