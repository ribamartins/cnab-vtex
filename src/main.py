"""Application entry point for CNAB PIX Payment System.

Startup flow (per D-05):
1. Initialize DB and session
2. If no users in DB: show first-run setup wizard
3. Try to restore persisted session (D-01)
4. If no valid session: show login dialog
5. Launch main window with authenticated user
"""
import sys
from PySide6.QtWidgets import QApplication, QDialog
from app.database import init_db
from app.auth import has_any_users, restore_session
from ui.styles import get_app_stylesheet


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("CNAB PIX")
    app.setStyleSheet(get_app_stylesheet())

    engine, Session = init_db()
    session = Session()

    # Check if first run (no users) — per D-05
    if not has_any_users(session):
        from ui.setup_wizard import SetupWizard
        wizard = SetupWizard(session)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    # Try to restore session — per D-01
    user = restore_session(session)

    if user is None:
        from ui.login_dialog import LoginDialog
        dialog = LoginDialog(session)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        user = dialog.logged_in_user

    from ui.main_window import MainWindow
    window = MainWindow(session, user)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
