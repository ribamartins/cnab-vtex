"""Settings window for CNAB PIX application.

Window title: "Configuracoes"
Three tabs: "Dados da Empresa", "Usuarios", "Credenciais VTEX"

- Tab 1: Company data form (all 12 CompanyConfig fields), pre-populated from DB
- Tab 2: User management table with add/edit/deactivate actions
- Tab 3: VTEX credentials (AppKey, AppToken) with masked display and toggle
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QLineEdit, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QScrollArea, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from ui.styles import (
    COLOR_DESTRUCTIVE, COLOR_ACTIVE, COLOR_INACTIVE,
    COLOR_PANEL, SPACING_MD, SPACING_SM, SPACING_LG
)

# Brazilian state abbreviations
BR_STATES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]


class AddUserDialog(QDialog):
    """Modal dialog for adding or editing a user.

    Constructor:
        session: SQLAlchemy session
        user: Existing User object for edit mode, or None for add mode
        current_user: Logged-in user (for self-deactivation guard)
    """

    def __init__(self, session, user=None, parent=None):
        super().__init__(parent)
        self._session = session
        self._user = user  # None means add mode
        self._is_edit = user is not None

        self.setWindowTitle(
            "Editar Usu\u00e1rio" if self._is_edit else "Adicionar Usu\u00e1rio"
        )
        self.setFixedSize(400, 380)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )

        self._build_ui()
        if self._is_edit:
            self._populate_fields()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        title = QLabel(
            "Editar Usu\u00e1rio" if self._is_edit else "Adicionar Usu\u00e1rio"
        )
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(SPACING_SM)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._display_name_field = QLineEdit()
        form.addRow("Nome Completo:", self._display_name_field)

        self._username_field = QLineEdit()
        if self._is_edit:
            self._username_field.setEnabled(False)  # Username not editable
        form.addRow("Usu\u00e1rio:", self._username_field)

        self._password_field = QLineEdit()
        self._password_field.setEchoMode(QLineEdit.EchoMode.Password)
        if self._is_edit:
            self._password_field.setPlaceholderText("Deixe em branco para manter a senha atual")
        form.addRow("Senha:", self._password_field)

        self._confirm_field = QLineEdit()
        self._confirm_field.setEchoMode(QLineEdit.EchoMode.Password)
        if self._is_edit:
            self._confirm_field.setPlaceholderText("Confirme a nova senha")
        form.addRow("Confirmar Senha:", self._confirm_field)

        self._role_combo = QComboBox()
        self._role_combo.addItem("Usu\u00e1rio", "user")
        self._role_combo.addItem("Administrador", "admin")
        form.addRow("Perfil:", self._role_combo)

        layout.addLayout(form)

        # Error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {COLOR_DESTRUCTIVE}; font-size: 12px;")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._save_btn = QPushButton(
            "Salvar" if self._is_edit else "Adicionar Usu\u00e1rio"
        )
        self._save_btn.setObjectName("primary")
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        """Pre-populate fields for edit mode."""
        self._display_name_field.setText(self._user.display_name)
        self._username_field.setText(self._user.username)
        role_index = self._role_combo.findData(self._user.role)
        if role_index >= 0:
            self._role_combo.setCurrentIndex(role_index)

    def _on_save(self):
        """Validate and save the user."""
        display_name = self._display_name_field.text().strip()
        username = self._username_field.text().strip()
        password = self._password_field.text()
        confirm = self._confirm_field.text()
        role = self._role_combo.currentData()

        # Validate required fields
        if not display_name:
            self._show_error("Nome Completo: Este campo \u00e9 obrigat\u00f3rio.")
            return

        if not self._is_edit and not username:
            self._show_error("Usu\u00e1rio: Este campo \u00e9 obrigat\u00f3rio.")
            return

        if not self._is_edit and not password:
            self._show_error("Senha: Este campo \u00e9 obrigat\u00f3rio.")
            return

        # Password validation (only if provided)
        if password:
            if len(password) < 8:
                self._show_error("A senha deve ter pelo menos 8 caracteres.")
                return
            if password != confirm:
                self._show_error("As senhas n\u00e3o coincidem.")
                return

        try:
            if self._is_edit:
                from app.auth import update_user
                update_user(
                    self._session,
                    self._user.id,
                    display_name=display_name,
                    password=password if password else None,
                    role=role,
                )
                self._session.commit()
            else:
                from app.auth import create_user
                create_user(
                    self._session,
                    username=username,
                    password=password,
                    display_name=display_name,
                    role=role,
                )
                self._session.commit()

            self.accept()

        except ValueError as e:
            self._show_error(str(e))
        except Exception:
            self._show_error("Erro ao salvar. Verifique os dados e tente novamente.")

    def _show_error(self, message: str):
        """Show error message in error label."""
        self._error_label.setText(message)
        self._error_label.setVisible(True)


class SettingsWindow(QDialog):
    """Settings window with three tabs for company data, users, and VTEX credentials.

    Constructor:
        session: SQLAlchemy session
        current_user: Logged-in User object (for self-deactivation guard)

    Always opens on the "Dados da Empresa" tab per UI-SPEC.
    Unsaved changes guard: prompts before tab switch or window close.
    """

    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self._session = session
        self._current_user = current_user
        self._company = None
        self._has_unsaved_changes = False
        self._current_tab_index = 0
        self._show_timer = QTimer()
        self._show_timer.setSingleShot(True)

        self.setWindowTitle("Configura\u00e7\u00f5es")
        self.setMinimumSize(640, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )

        self._load_company()
        self._build_ui()
        self._connect_signals()
        self._populate_company_form()

    def _load_company(self):
        """Load company record from DB."""
        from app.models import Company
        self._company = self._session.query(Company).first()

    def _build_ui(self):
        """Build the tabbed settings layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_company_tab(), "Dados da Empresa")
        self._tabs.addTab(self._build_users_tab(), "Usu\u00e1rios")
        self._tabs.addTab(self._build_credentials_tab(), "Credenciais VTEX")
        self._tabs.setCurrentIndex(0)

        main_layout.addWidget(self._tabs)

    def _build_company_tab(self) -> QWidget:
        """Build the Dados da Empresa tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        form = QFormLayout()
        form.setSpacing(SPACING_SM)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._co_cnpj = QLineEdit()
        self._co_cnpj.setMaxLength(14)
        form.addRow("CNPJ:", self._co_cnpj)

        self._co_agency = QLineEdit()
        self._co_agency.setMaxLength(5)
        form.addRow("Ag\u00eancia:", self._co_agency)

        self._co_account = QLineEdit()
        self._co_account.setMaxLength(12)
        form.addRow("Conta:", self._co_account)

        self._co_dac = QLineEdit()
        self._co_dac.setMaxLength(1)
        form.addRow("DAC:", self._co_dac)

        self._co_name = QLineEdit()
        self._co_name.setMaxLength(30)
        form.addRow("Nome da Empresa:", self._co_name)

        self._co_address = QLineEdit()
        self._co_address.setMaxLength(30)
        form.addRow("Endere\u00e7o:", self._co_address)

        self._co_address_number = QLineEdit()
        self._co_address_number.setMaxLength(5)
        form.addRow("N\u00famero:", self._co_address_number)

        self._co_complement = QLineEdit()
        self._co_complement.setMaxLength(15)
        form.addRow("Complemento:", self._co_complement)

        self._co_city = QLineEdit()
        self._co_city.setMaxLength(20)
        form.addRow("Cidade:", self._co_city)

        self._co_cep = QLineEdit()
        self._co_cep.setMaxLength(8)
        form.addRow("CEP:", self._co_cep)

        self._co_state = QComboBox()
        self._co_state.addItems(BR_STATES)
        form.addRow("Estado:", self._co_state)

        self._co_tipo_pagamento = QComboBox()
        self._co_tipo_pagamento.addItem("Fornecedores (20)", 20)
        self._co_tipo_pagamento.addItem("Diversos (98)", 98)
        form.addRow("Tipo de Pagamento:", self._co_tipo_pagamento)

        layout.addLayout(form)

        # Error/success message label
        self._co_message_label = QLabel()
        self._co_message_label.setWordWrap(True)
        self._co_message_label.setVisible(False)
        layout.addWidget(self._co_message_label)

        layout.addStretch()

        # Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._co_save_btn = QPushButton("Salvar Configura\u00e7\u00f5es")
        self._co_save_btn.setObjectName("primary")
        btn_layout.addWidget(self._co_save_btn)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        return scroll

    def _build_users_tab(self) -> QWidget:
        """Build the Usuarios tab with user management table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        self._add_user_btn = QPushButton("Adicionar Usu\u00e1rio")
        self._add_user_btn.setObjectName("primary")
        toolbar.addWidget(self._add_user_btn)
        layout.addLayout(toolbar)

        # Users table
        self._users_table = QTableWidget()
        self._users_table.setColumnCount(5)
        self._users_table.setHorizontalHeaderLabels(
            ["Nome", "Usu\u00e1rio", "Perfil", "Status", "A\u00e7\u00f5es"]
        )
        self._users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._users_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._users_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._users_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._users_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._users_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._users_table.verticalHeader().setVisible(False)
        self._users_table.setAlternatingRowColors(False)
        self._users_table.setMinimumHeight(200)

        layout.addWidget(self._users_table)

        # Load users data
        self._reload_users_table()

        return widget

    def _build_credentials_tab(self) -> QWidget:
        """Build the Credenciais VTEX tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        description = QLabel(
            "As credenciais s\u00e3o armazenadas criptografadas localmente. "
            "N\u00e3o compartilhe estas chaves."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setSpacing(SPACING_SM)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # AppKey row
        appkey_layout = QHBoxLayout()
        self._vtex_appkey = QLineEdit()
        self._vtex_appkey.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self._vtex_appkey.setPlaceholderText("vtexappkey-xxxxx-XXXXXX")
        appkey_layout.addWidget(self._vtex_appkey)
        self._show_appkey_btn = QPushButton("Mostrar")
        self._show_appkey_btn.setFixedWidth(80)
        appkey_layout.addWidget(self._show_appkey_btn)
        form.addRow("AppKey:", appkey_layout)

        # AppToken row
        apptoken_layout = QHBoxLayout()
        self._vtex_apptoken = QLineEdit()
        self._vtex_apptoken.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self._vtex_apptoken.setPlaceholderText("XXXXXXXXXXXXX")
        apptoken_layout.addWidget(self._vtex_apptoken)
        self._show_apptoken_btn = QPushButton("Mostrar")
        self._show_apptoken_btn.setFixedWidth(80)
        apptoken_layout.addWidget(self._show_apptoken_btn)
        form.addRow("AppToken:", apptoken_layout)

        layout.addLayout(form)

        # Message label
        self._cred_message_label = QLabel()
        self._cred_message_label.setWordWrap(True)
        self._cred_message_label.setVisible(False)
        layout.addWidget(self._cred_message_label)

        layout.addStretch()

        # Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cred_save_btn = QPushButton("Salvar Configura\u00e7\u00f5es")
        self._cred_save_btn.setObjectName("primary")
        btn_layout.addWidget(self._cred_save_btn)
        layout.addLayout(btn_layout)

        # Load existing credentials
        self._populate_credentials()

        return widget

    def _populate_company_form(self):
        """Pre-populate company form from DB record."""
        if self._company is None:
            return

        self._co_cnpj.setText(self._company.cnpj or "")
        self._co_agency.setText(self._company.agency or "")
        self._co_account.setText(self._company.account or "")
        self._co_dac.setText(self._company.dac or "")
        self._co_name.setText(self._company.name or "")
        self._co_address.setText(self._company.address or "")
        self._co_address_number.setText(self._company.address_number or "")
        self._co_complement.setText(self._company.complement or "")
        self._co_city.setText(self._company.city or "")
        self._co_cep.setText(self._company.cep or "")

        state_index = self._co_state.findText(self._company.state or "SP")
        if state_index >= 0:
            self._co_state.setCurrentIndex(state_index)

        tipo_index = self._co_tipo_pagamento.findData(self._company.tipo_pagamento or 20)
        if tipo_index >= 0:
            self._co_tipo_pagamento.setCurrentIndex(tipo_index)

    def _populate_credentials(self):
        """Load and decrypt VTEX credentials from DB."""
        if self._company is None:
            return

        try:
            from app.crypto import decrypt_value
            if self._company.vtex_app_key_encrypted:
                self._vtex_appkey.setText(
                    decrypt_value(self._company.vtex_app_key_encrypted)
                )
            if self._company.vtex_app_token_encrypted:
                self._vtex_apptoken.setText(
                    decrypt_value(self._company.vtex_app_token_encrypted)
                )
        except Exception:
            pass  # If decryption fails, leave fields empty

    def _reload_users_table(self):
        """Load users from DB and populate the table."""
        from app.auth import get_all_users

        users = get_all_users(self._session)

        self._users_table.setRowCount(0)

        if not users:
            self._users_table.setRowCount(1)
            empty_item = QTableWidgetItem(
                'Nenhum usu\u00e1rio cadastrado. Clique em "Adicionar Usu\u00e1rio" para criar o primeiro acesso.'
            )
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._users_table.setItem(0, 0, empty_item)
            self._users_table.setSpan(0, 0, 1, 5)
            return

        self._users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            # Set minimum row height
            self._users_table.setRowHeight(row, 36)

            # Nome
            name_item = QTableWidgetItem(user.display_name)
            self._users_table.setItem(row, 0, name_item)

            # Usuario
            username_item = QTableWidgetItem(user.username)
            self._users_table.setItem(row, 1, username_item)

            # Perfil
            role_display = "Administrador" if user.role == "admin" else "Usu\u00e1rio"
            role_item = QTableWidgetItem(role_display)
            self._users_table.setItem(row, 2, role_item)

            # Status
            status_text = "Ativo" if user.is_active else "Inativo"
            status_item = QTableWidgetItem(status_text)
            if user.is_active:
                status_item.setForeground(QColor(COLOR_ACTIVE))
            else:
                status_item.setForeground(QColor(COLOR_INACTIVE))
            self._users_table.setItem(row, 3, status_item)

            # Actions cell
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            # Edit button
            edit_btn = QPushButton("Editar")
            edit_btn.setFixedHeight(28)
            edit_btn.setProperty("user_id", user.id)
            edit_btn.clicked.connect(lambda checked, uid=user.id: self._on_edit_user(uid))
            actions_layout.addWidget(edit_btn)

            # Deactivate/Reactivate button
            if user.is_active:
                deact_btn = QPushButton("Desativar")
                deact_btn.setObjectName("destructive")
                deact_btn.setFixedHeight(28)
                is_self = (user.id == self._current_user.id)
                if is_self:
                    deact_btn.setEnabled(False)
                    deact_btn.setToolTip("N\u00e3o \u00e9 poss\u00edvel desativar sua pr\u00f3pria conta.")
                else:
                    deact_btn.clicked.connect(
                        lambda checked, uid=user.id, name=user.display_name:
                        self._on_deactivate_user(uid, name)
                    )
                actions_layout.addWidget(deact_btn)
            else:
                react_btn = QPushButton("Reativar")
                react_btn.setFixedHeight(28)
                react_btn.clicked.connect(
                    lambda checked, uid=user.id: self._on_reactivate_user(uid)
                )
                actions_layout.addWidget(react_btn)

            actions_layout.addStretch()
            self._users_table.setCellWidget(row, 4, actions_widget)

    def _connect_signals(self):
        """Connect all signals."""
        # Company tab
        self._co_save_btn.clicked.connect(self._save_company)
        # Track changes for unsaved guard
        company_fields = [
            self._co_cnpj, self._co_agency, self._co_account, self._co_dac,
            self._co_name, self._co_address, self._co_address_number,
            self._co_complement, self._co_city, self._co_cep
        ]
        for field in company_fields:
            field.textChanged.connect(self._mark_company_changed)
        self._co_state.currentIndexChanged.connect(self._mark_company_changed)
        self._co_tipo_pagamento.currentIndexChanged.connect(self._mark_company_changed)

        # Users tab
        self._add_user_btn.clicked.connect(self._on_add_user)

        # Credentials tab
        self._cred_save_btn.clicked.connect(self._save_credentials)
        self._vtex_appkey.textChanged.connect(self._mark_cred_changed)
        self._vtex_apptoken.textChanged.connect(self._mark_cred_changed)

        # Show/hide credential fields
        self._show_appkey_btn.clicked.connect(
            lambda: self._toggle_credential_visibility(
                self._vtex_appkey, self._show_appkey_btn
            )
        )
        self._show_apptoken_btn.clicked.connect(
            lambda: self._toggle_credential_visibility(
                self._vtex_apptoken, self._show_apptoken_btn
            )
        )

        # Tab change guard
        self._tabs.currentChanged.connect(self._on_tab_changed)

    def _mark_company_changed(self):
        """Mark company tab as having unsaved changes."""
        self._has_unsaved_changes = True
        self._current_tab_index = 0

    def _mark_cred_changed(self):
        """Mark credentials tab as having unsaved changes."""
        self._has_unsaved_changes = True
        self._current_tab_index = 2

    def _on_tab_changed(self, new_index: int):
        """Guard against unsaved changes when switching tabs."""
        if not self._has_unsaved_changes:
            return

        result = QMessageBox.question(
            self,
            "Altera\u00e7\u00f5es n\u00e3o salvas",
            "H\u00e1 altera\u00e7\u00f5es n\u00e3o salvas. Deseja salvar antes de sair?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )

        if result == QMessageBox.StandardButton.Save:
            # Save current tab's data
            if self._current_tab_index == 0:
                self._save_company()
            elif self._current_tab_index == 2:
                self._save_credentials()
            self._has_unsaved_changes = False
        elif result == QMessageBox.StandardButton.Discard:
            self._has_unsaved_changes = False
        else:
            # Cancel — revert tab switch
            self._tabs.blockSignals(True)
            self._tabs.setCurrentIndex(self._current_tab_index)
            self._tabs.blockSignals(False)

    def closeEvent(self, event):
        """Guard unsaved changes on window close."""
        if self._has_unsaved_changes:
            result = QMessageBox.question(
                self,
                "Altera\u00e7\u00f5es n\u00e3o salvas",
                "H\u00e1 altera\u00e7\u00f5es n\u00e3o salvas. Deseja salvar antes de sair?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if result == QMessageBox.StandardButton.Save:
                if self._current_tab_index == 0:
                    self._save_company()
                elif self._current_tab_index == 2:
                    self._save_credentials()
                event.accept()
            elif result == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def _save_company(self):
        """Save company data to DB."""
        if self._company is None:
            from app.models import Company
            self._company = Company()
            self._session.add(self._company)

        # Validate CNPJ
        cnpj = self._co_cnpj.text().strip()
        if cnpj and (not cnpj.isdigit() or len(cnpj) != 14):
            self._show_company_message(
                "CNPJ inv\u00e1lido. Informe 14 d\u00edgitos sem pontua\u00e7\u00e3o.",
                error=True
            )
            return

        try:
            self._company.cnpj = cnpj
            self._company.agency = self._co_agency.text().strip()
            self._company.account = self._co_account.text().strip()
            self._company.dac = self._co_dac.text().strip()
            self._company.name = self._co_name.text().strip()
            self._company.address = self._co_address.text().strip()
            self._company.address_number = self._co_address_number.text().strip()
            self._company.complement = self._co_complement.text().strip()
            self._company.city = self._co_city.text().strip()
            self._company.cep = self._co_cep.text().strip()
            self._company.state = self._co_state.currentText()
            self._company.tipo_pagamento = self._co_tipo_pagamento.currentData()

            self._session.commit()
            self._has_unsaved_changes = False
            self._show_company_message("Configura\u00e7\u00f5es salvas com sucesso.", error=False)
        except Exception:
            self._session.rollback()
            self._show_company_message(
                "Erro ao salvar. Verifique os dados e tente novamente.",
                error=True
            )

    def _show_company_message(self, text: str, error: bool = False):
        """Show message in company tab."""
        if error:
            self._co_message_label.setStyleSheet(
                f"color: {COLOR_DESTRUCTIVE}; font-size: 12px;"
            )
        else:
            self._co_message_label.setStyleSheet(
                "color: #2E7D32; font-size: 12px;"
            )
        self._co_message_label.setText(text)
        self._co_message_label.setVisible(True)

    def _save_credentials(self):
        """Encrypt and save VTEX credentials to DB."""
        if self._company is None:
            self._show_cred_message("Salve primeiro os dados da empresa.", error=True)
            return

        try:
            from app.crypto import encrypt_value

            appkey = self._vtex_appkey.text().strip()
            apptoken = self._vtex_apptoken.text().strip()

            if appkey:
                self._company.vtex_app_key_encrypted = encrypt_value(appkey)
            else:
                self._company.vtex_app_key_encrypted = None

            if apptoken:
                self._company.vtex_app_token_encrypted = encrypt_value(apptoken)
            else:
                self._company.vtex_app_token_encrypted = None

            self._session.commit()
            self._has_unsaved_changes = False
            self._show_cred_message("Configura\u00e7\u00f5es salvas com sucesso.", error=False)
        except Exception:
            self._session.rollback()
            self._show_cred_message(
                "Erro ao salvar. Verifique os dados e tente novamente.",
                error=True
            )

    def _show_cred_message(self, text: str, error: bool = False):
        """Show message in credentials tab."""
        if error:
            self._cred_message_label.setStyleSheet(
                f"color: {COLOR_DESTRUCTIVE}; font-size: 12px;"
            )
        else:
            self._cred_message_label.setStyleSheet(
                "color: #2E7D32; font-size: 12px;"
            )
        self._cred_message_label.setText(text)
        self._cred_message_label.setVisible(True)

    def _toggle_credential_visibility(self, field: QLineEdit, btn: QPushButton):
        """Show credential field in plain text for 5 seconds then auto-re-mask per UI-SPEC."""
        field.setEchoMode(QLineEdit.EchoMode.Normal)
        btn.setEnabled(False)
        btn.setText("Ocultando...")

        # Auto re-mask after 5 seconds
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._re_mask_credential(field, btn))
        timer.start(5000)

    def _re_mask_credential(self, field: QLineEdit, btn: QPushButton):
        """Re-mask credential field after timeout."""
        field.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        btn.setEnabled(True)
        btn.setText("Mostrar")

    def _on_add_user(self):
        """Open add user dialog."""
        dialog = AddUserDialog(self._session, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload_users_table()

    def _on_edit_user(self, user_id: int):
        """Open edit user dialog."""
        from app.auth import get_user_by_id
        user = get_user_by_id(self._session, user_id)
        if user is None:
            return
        dialog = AddUserDialog(self._session, user=user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload_users_table()

    def _on_deactivate_user(self, user_id: int, display_name: str):
        """Confirm and deactivate a user per UI-SPEC."""
        result = QMessageBox.question(
            self,
            "Desativar usu\u00e1rio",
            f"Desativar usu\u00e1rio: Tem certeza que deseja desativar este acesso? "
            f"O usu\u00e1rio n\u00e3o conseguir\u00e1 mais entrar no sistema.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

        if result == QMessageBox.StandardButton.Yes:
            try:
                from app.auth import deactivate_user
                deactivate_user(self._session, user_id)
                self._session.commit()
                self._reload_users_table()
            except Exception:
                QMessageBox.critical(
                    self,
                    "Erro",
                    "Erro ao desativar usu\u00e1rio. Tente novamente."
                )

    def _on_reactivate_user(self, user_id: int):
        """Reactivate an inactive user."""
        try:
            from app.auth import reactivate_user
            reactivate_user(self._session, user_id)
            self._session.commit()
            self._reload_users_table()
        except Exception:
            QMessageBox.critical(
                self,
                "Erro",
                "Erro ao reativar usu\u00e1rio. Tente novamente."
            )
