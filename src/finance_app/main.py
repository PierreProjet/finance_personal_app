from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from finance_app.config import Settings
from finance_app.db import Database
from finance_app.models.entities import User
from finance_app.security.crypto import CryptoService
from finance_app.services.auth_service import AuthService
from finance_app.services.finance_service import FinanceService
from finance_app.ui.dashboard import DashboardWindow
from finance_app.ui.login import LoginWindow
from finance_app.ui.theme import stylesheet


class ApplicationController:
    def __init__(self, app: QApplication) -> None:
        settings = Settings.load()
        self._app = app
        self._database = Database(settings.database_path)
        self._database.initialize()
        self._crypto = CryptoService(settings.data_dir)
        self._auth = AuthService(self._database)
        self._finance = FinanceService(self._database, self._crypto)
        self._login: LoginWindow | None = None
        self._dashboard: DashboardWindow | None = None

    def start(self) -> None:
        self._app.setStyleSheet(stylesheet("#6C63FF"))
        self._login = LoginWindow(self._auth, self._open_dashboard)
        self._login.show()

    def _open_dashboard(self, user: User) -> None:
        self._app.setStyleSheet(stylesheet(user.accent_color))
        self._dashboard = DashboardWindow(user, self._finance, self._auth)
        self._dashboard.show()
        if self._login:
            self._login.close()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Finance Foyer")
    controller = ApplicationController(app)
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
