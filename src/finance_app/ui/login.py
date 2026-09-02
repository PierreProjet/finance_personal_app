from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from finance_app.models.entities import User
from finance_app.services.auth_service import AuthService


class LoginWindow(QWidget):
    def __init__(self, auth: AuthService, on_authenticated: Callable[[User], None]) -> None:
        super().__init__()
        self._auth = auth
        self._on_authenticated = on_authenticated
        self.setWindowTitle("Finance Foyer — Connexion")
        self.setMinimumSize(520, 560)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_login())
        self._stack.addWidget(self._build_register())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 42, 42, 42)
        layout.addWidget(self._stack)

    def _headline(self, title: str, subtitle: str) -> QVBoxLayout:
        box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("Title")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Muted")
        subtitle_label.setWordWrap(True)
        box.addWidget(title_label)
        box.addWidget(subtitle_label)
        box.addSpacing(18)
        return box

    def _build_login(self) -> QWidget:
        widget = QWidget()
        layout = self._headline("Finance Foyer", "Une vue locale et sécurisée de votre patrimoine.")
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("nom d'utilisateur")
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setPlaceholderText("mot de passe")
        form = QFormLayout()
        form.addRow("Utilisateur", self.login_username)
        form.addRow("Mot de passe", self.login_password)
        layout.addLayout(form)
        button = QPushButton("Se connecter")
        button.setObjectName("Primary")
        button.clicked.connect(self._login)
        register = QPushButton("Créer un profil et un foyer")
        register.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        layout.addSpacing(12)
        layout.addWidget(button)
        layout.addWidget(register)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _build_register(self) -> QWidget:
        widget = QWidget()
        layout = self._headline("Créer votre espace", "Le premier utilisateur devient admin_foyer.")
        self.register_username = QLineEdit()
        self.register_display_name = QLineEdit()
        self.register_household = QLineEdit()
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_color = QComboBox()
        self.register_color.addItems(["#6C63FF", "#3A86FF", "#00A896", "#E76F51", "#D65DB1"])
        form = QFormLayout()
        form.addRow("Utilisateur", self.register_username)
        form.addRow("Nom affiché", self.register_display_name)
        form.addRow("Nom du foyer", self.register_household)
        form.addRow("Mot de passe", self.register_password)
        form.addRow("Couleur", self.register_color)
        layout.addLayout(form)
        create = QPushButton("Créer le profil")
        create.setObjectName("Primary")
        create.clicked.connect(self._register)
        back = QPushButton("Retour à la connexion")
        back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        layout.addWidget(create)
        layout.addWidget(back)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _login(self) -> None:
        user = self._auth.authenticate(self.login_username.text(), self.login_password.text())
        if not user:
            QMessageBox.warning(self, "Connexion", "Identifiants invalides.")
            return
        self._on_authenticated(user)

    def _register(self) -> None:
        try:
            user = self._auth.register_user(
                username=self.register_username.text(),
                password=self.register_password.text(),
                display_name=self.register_display_name.text(),
                accent_color=self.register_color.currentText(),
                household_name=self.register_household.text(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Création", str(exc))
            return
        QMessageBox.information(self, "Création", "Profil créé. Vous êtes admin_foyer.")
        self._on_authenticated(user)
