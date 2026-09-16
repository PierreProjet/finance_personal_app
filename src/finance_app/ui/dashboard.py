from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from finance_app.models.entities import AccountKind, AssetKind, User
from finance_app.services.auth_service import AuthService
from finance_app.services.finance_service import FinanceService


def money(value: Decimal) -> str:
    return f"{value:,.2f} €".replace(",", " ")


class MetricCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setObjectName("Muted")
        self.value = QLabel("—")
        self.value.setObjectName("CardValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value)


class DashboardWindow(QWidget):
    def __init__(self, user: User, finance: FinanceService, auth: AuthService) -> None:
        super().__init__()
        self._user = user
        self._finance = finance
        self._auth = auth
        self.setWindowTitle("Finance Foyer")
        self.resize(1200, 760)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        brand = QLabel("◈  Finance Foyer")
        brand.setStyleSheet("font-size:20px;font-weight:700;padding:10px 4px;")
        side.addWidget(brand)
        for label in [
            "Vue d'ensemble",
            "Patrimoine",
            "Transactions",
            "Budget",
            "Diversification",
        ]:
            button = QPushButton(label)
            button.clicked.connect(self.refresh)
            side.addWidget(button)
        side.addStretch()
        _, household_name, role, _ = self._finance.household_for_user(self._user.id)
        profile = QLabel(f"{self._user.display_name}\n{household_name} · {role}")
        profile.setObjectName("Muted")
        side.addWidget(profile)
        root.addWidget(sidebar)

        content_widget = QWidget()
        content = QVBoxLayout(content_widget)
        content.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        title = QLabel("Vue d'ensemble")
        title.setObjectName("Title")
        header.addWidget(title)
        header.addStretch()

        add_member = QPushButton("+ Membre")
        add_member.clicked.connect(self._show_add_member)
        add_budget = QPushButton("Budget")
        add_budget.clicked.connect(self._show_budget)
        add_transaction = QPushButton("+ Transaction")
        add_transaction.clicked.connect(self._show_add_transaction)
        add_account = QPushButton("+ Compte")
        add_account.setObjectName("Primary")
        add_account.clicked.connect(self._show_add_account)
        add_asset = QPushButton("+ Placement")
        add_asset.clicked.connect(self._show_add_asset)
        header.addWidget(add_member)
        header.addWidget(add_budget)
        header.addWidget(add_transaction)
        header.addWidget(add_asset)
        header.addWidget(add_account)
        content.addLayout(header)

        cards = QGridLayout()
        self.gross_card = MetricCard("Patrimoine brut")
        self.debt_card = MetricCard("Dettes")
        self.net_card = MetricCard("Patrimoine net")
        self.return_card = MetricCard("Rendement attendu / an")
        cards.addWidget(self.gross_card, 0, 0)
        cards.addWidget(self.debt_card, 0, 1)
        cards.addWidget(self.net_card, 0, 2)
        cards.addWidget(self.return_card, 0, 3)
        content.addLayout(cards)

        lower = QGridLayout()
        accounts_card = QFrame()
        accounts_card.setObjectName("Card")
        accounts_layout = QVBoxLayout(accounts_card)
        accounts_layout.addWidget(QLabel("Comptes"))
        self.accounts = QTableWidget(0, 4)
        self.accounts.setHorizontalHeaderLabels(
            ["Compte", "Type", "Solde", "Portée"]
        )
        self.accounts.horizontalHeader().setStretchLastSection(True)
        accounts_layout.addWidget(self.accounts)
        lower.addWidget(accounts_card, 0, 0, 2, 2)

        expenses_card = QFrame()
        expenses_card.setObjectName("Card")
        expenses_layout = QVBoxLayout(expenses_card)
        expenses_layout.addWidget(QLabel("Principaux postes de dépenses"))
        self.expenses_label = QLabel("Aucune transaction")
        self.expenses_label.setWordWrap(True)
        self.expenses_label.setObjectName("Muted")
        expenses_layout.addWidget(self.expenses_label)
        lower.addWidget(expenses_card, 0, 2)

        risk_card = QFrame()
        risk_card.setObjectName("Card")
        risk_layout = QVBoxLayout(risk_card)
        risk_layout.addWidget(QLabel("Diversification / concentration"))
        self.risk_label = QLabel("—")
        self.risk_label.setObjectName("Muted")
        self.risk_label.setWordWrap(True)
        risk_layout.addWidget(self.risk_label)
        lower.addWidget(risk_card, 1, 2)

        budget_card = QFrame()
        budget_card.setObjectName("Card")
        budget_layout = QVBoxLayout(budget_card)
        budget_layout.addWidget(QLabel("Budget commun du mois"))
        self.budget_progress = QProgressBar()
        self.budget_progress.setRange(0, 100)
        self.budget_label = QLabel("—")
        self.budget_label.setObjectName("Muted")
        budget_layout.addWidget(self.budget_progress)
        budget_layout.addWidget(self.budget_label)
        lower.addWidget(budget_card, 2, 0)

        forecast_card = QFrame()
        forecast_card.setObjectName("Card")
        forecast_layout = QVBoxLayout(forecast_card)
        forecast_layout.addWidget(QLabel("Projection à 10 ans"))
        self.forecast_label = QLabel("—")
        self.forecast_label.setObjectName("Muted")
        self.forecast_label.setWordWrap(True)
        forecast_layout.addWidget(self.forecast_label)
        lower.addWidget(forecast_card, 2, 1, 1, 2)
        content.addLayout(lower, 1)
        root.addWidget(content_widget, 1)

    def refresh(self) -> None:
        data = self._finance.dashboard(self._user.id)
        self.gross_card.value.setText(money(data["gross"]))
        self.debt_card.value.setText(money(data["liabilities"]))
        self.net_card.value.setText(money(data["net"]))
        expected_return = float(data["expected_return"])
        self.return_card.value.setText(f"{expected_return * 100:.2f} %")

        accounts = data["accounts"]
        self.accounts.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            values = [
                account["name"],
                account["kind"],
                money(account["balance"]),
                "Foyer" if account["shared"] else "Personnel",
            ]
            for column, value in enumerate(values):
                self.accounts.setItem(row, column, QTableWidgetItem(str(value)))

        expenses = data["expenses"]
        expense_lines = [
            f"• {category}: {money(amount)}"
            for category, amount in list(expenses.items())[:5]
        ]
        self.expenses_label.setText(
            "\n".join(expense_lines) or "Aucune dépense enregistrée."
        )

        hhi = float(data["hhi"])
        level = "faible" if hhi < 0.15 else "modérée" if hhi < 0.25 else "élevée"
        by_type = data["allocation_type"]
        top = next(iter(by_type.items()), None)
        detail = f"Concentration {level} (HHI {hhi:.2f})."
        if top:
            total = sum(by_type.values(), Decimal("0"))
            share = float(top[1] / total * 100) if total else 0
            detail += f" Première classe: {top[0]} ({share:.0f} %)."
        detail += " Indicateur informatif, pas un conseil d'investissement."
        self.risk_label.setText(detail)

        planned = data["budget_planned"]
        spent = data["budget_spent"]
        ratio = int(min(100, float(spent / planned * 100))) if planned else 0
        self.budget_progress.setValue(ratio)
        self.budget_label.setText(f"Dépensé {money(spent)} / prévu {money(planned)}")

        forecast = data["forecast"]
        forecast_text = (
            f"Scénario central transparent : {money(forecast[-1].value)} à 10 ans, "
            "basé sur le rendement pondéré saisi. À compléter ultérieurement par "
            "scénarios prudent/central/dynamique."
        )
        self.forecast_label.setText(forecast_text)

    @staticmethod
    def _fill_account_combo(combo: QComboBox, accounts: list[dict[str, object]]) -> None:
        for account in accounts:
            combo.addItem(str(account["name"]), int(account["id"]))

    def _show_add_account(self) -> None:
        dialog = QWidget(self, Qt.WindowType.Dialog)
        dialog.setWindowTitle("Ajouter un compte")
        form = QFormLayout(dialog)

        name = QLineEdit()
        kind = QComboBox()
        kind.addItems([account_kind.value for account_kind in AccountKind])
        balance = QDoubleSpinBox()
        balance.setRange(-100_000_000, 100_000_000)
        balance.setDecimals(2)
        balance.setSuffix(" €")
        scope = QComboBox()
        scope.addItems(
            ["Personnel", "Foyer", "Dette personnelle", "Dette foyer"]
        )
        institution = QLineEdit()
        submit = QPushButton("Ajouter")
        submit.setObjectName("Primary")

        form.addRow("Nom", name)
        form.addRow("Type", kind)
        form.addRow("Solde", balance)
        form.addRow("Portée", scope)
        form.addRow("Établissement", institution)
        form.addRow(submit)

        def save() -> None:
            scope_text = scope.currentText()
            self._finance.add_account(
                self._user.id,
                name.text(),
                kind.currentText(),
                Decimal(str(balance.value())),
                shared="Foyer" in scope_text,
                is_liability="Dette" in scope_text,
                institution=institution.text(),
            )
            dialog.close()
            self.refresh()

        submit.clicked.connect(save)
        dialog.resize(420, 260)
        dialog.show()
        self._account_dialog = dialog

    def _show_add_asset(self) -> None:
        accounts = self._finance.list_accounts(self._user.id)
        if not accounts:
            QMessageBox.information(self, "Placement", "Ajoutez d'abord un compte.")
            return

        dialog = QWidget(self, Qt.WindowType.Dialog)
        dialog.setWindowTitle("Ajouter un placement")
        form = QFormLayout(dialog)
        account = QComboBox()
        self._fill_account_combo(account, accounts)
        label = QLineEdit()
        kind = QComboBox()
        kind.addItems([asset_kind.value for asset_kind in AssetKind])
        value = QDoubleSpinBox()
        value.setRange(0, 100_000_000)
        value.setDecimals(2)
        value.setSuffix(" €")
        sector = QLineEdit()
        geography = QLineEdit()
        expected = QDoubleSpinBox()
        expected.setRange(-100, 100)
        expected.setDecimals(2)
        expected.setValue(5.0)
        expected.setSuffix(" %")
        submit = QPushButton("Ajouter")
        submit.setObjectName("Primary")

        fields = [
            ("Compte", account),
            ("Libellé", label),
            ("Classe", kind),
            ("Valeur", value),
            ("Secteur", sector),
            ("Géographie", geography),
            ("Rendement attendu", expected),
        ]
        for title, widget in fields:
            form.addRow(title, widget)
        form.addRow(submit)

        def save() -> None:
            self._finance.add_asset(
                int(account.currentData()),
                label.text(),
                kind.currentText(),
                Decimal(str(value.value())),
                sector.text(),
                geography.text(),
                Decimal(str(expected.value() / 100)),
            )
            dialog.close()
            self.refresh()

        submit.clicked.connect(save)
        dialog.resize(440, 360)
        dialog.show()
        self._asset_dialog = dialog

    def _show_add_transaction(self) -> None:
        accounts = self._finance.list_accounts(self._user.id)
        if not accounts:
            QMessageBox.information(
                self, "Transaction", "Ajoutez d'abord un compte."
            )
            return

        dialog = QWidget(self, Qt.WindowType.Dialog)
        dialog.setWindowTitle("Ajouter une transaction")
        form = QFormLayout(dialog)
        account = QComboBox()
        self._fill_account_combo(account, accounts)
        category = QLineEdit()
        category.setPlaceholderText("Logement, Courses, Salaire…")
        label = QLineEdit()
        amount = QDoubleSpinBox()
        amount.setRange(-100_000_000, 100_000_000)
        amount.setDecimals(2)
        amount.setSuffix(" €")
        scope = QComboBox()
        scope.addItems(["Personnel", "Foyer"])
        submit = QPushButton("Enregistrer")
        submit.setObjectName("Primary")

        fields = [
            ("Compte", account),
            ("Catégorie", category),
            ("Libellé", label),
            ("Montant (+ entrée / - dépense)", amount),
            ("Portée", scope),
        ]
        for title, widget in fields:
            form.addRow(title, widget)
        form.addRow(submit)

        def save() -> None:
            self._finance.add_transaction(
                int(account.currentData()),
                date.today(),
                category.text(),
                label.text(),
                Decimal(str(amount.value())),
                is_shared=scope.currentText() == "Foyer",
            )
            dialog.close()
            self.refresh()

        submit.clicked.connect(save)
        dialog.resize(470, 300)
        dialog.show()
        self._transaction_dialog = dialog

    def _show_budget(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer":
            QMessageBox.warning(
                self,
                "Budget",
                "Seul l'admin_foyer peut modifier le budget commun.",
            )
            return

        dialog = QWidget(self, Qt.WindowType.Dialog)
        dialog.setWindowTitle("Budget commun mensuel")
        form = QFormLayout(dialog)
        category = QLineEdit()
        category.setPlaceholderText("Courses, logement, énergie…")
        amount = QDoubleSpinBox()
        amount.setRange(0, 100_000_000)
        amount.setDecimals(2)
        amount.setSuffix(" €")
        submit = QPushButton("Enregistrer")
        submit.setObjectName("Primary")
        form.addRow("Catégorie", category)
        form.addRow("Montant prévu", amount)
        form.addRow(submit)

        def save() -> None:
            try:
                self._finance.set_budget(
                    self._user.id,
                    category.text().strip() or "Autre",
                    Decimal(str(amount.value())),
                )
            except (PermissionError, ValueError) as exc:
                QMessageBox.warning(dialog, "Budget", str(exc))
                return
            dialog.close()
            self.refresh()

        submit.clicked.connect(save)
        dialog.resize(430, 210)
        dialog.show()
        self._budget_dialog = dialog

    def _show_add_member(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer":
            QMessageBox.warning(
                self, "Membre", "Seul l'admin_foyer peut créer un membre."
            )
            return

        dialog = QWidget(self, Qt.WindowType.Dialog)
        dialog.setWindowTitle("Créer un membre du foyer")
        form = QFormLayout(dialog)
        username = QLineEdit()
        display_name = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        visibility = QComboBox()
        visibility.addItems(["Accès au foyer", "Profil personnel uniquement"])
        submit = QPushButton("Créer le membre")
        submit.setObjectName("Primary")

        fields = [
            ("Utilisateur", username),
            ("Nom affiché", display_name),
            ("Mot de passe", password),
            ("Visibilité", visibility),
        ]
        for title, widget in fields:
            form.addRow(title, widget)
        form.addRow(submit)

        def save() -> None:
            try:
                self._auth.create_household_member(
                    self._user.id,
                    username.text(),
                    password.text(),
                    display_name.text(),
                    can_view_household=visibility.currentIndex() == 0,
                )
            except (PermissionError, ValueError) as exc:
                QMessageBox.warning(dialog, "Membre", str(exc))
                return
            QMessageBox.information(
                dialog,
                "Membre",
                "Le membre peut maintenant se connecter avec son propre profil.",
            )
            dialog.close()

        submit.clicked.connect(save)
        dialog.resize(450, 280)
        dialog.show()
        self._member_dialog = dialog
