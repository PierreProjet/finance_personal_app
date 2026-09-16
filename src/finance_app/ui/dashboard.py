from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from finance_app.config import Settings
from finance_app.models.entities import AccountKind, AssetKind, User
from finance_app.services.auth_service import AuthService
from finance_app.services.finance_service import FinanceService
from finance_app.ui.charts import LineChart
from finance_app.ui.preferences import PreferencesStore
from finance_app.ui.theme import stylesheet


def money(value: Decimal) -> str:
    return f"{value:,.2f} €".replace(",", " ")


class MetricCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__(); self.setObjectName("Card")
        layout = QVBoxLayout(self); label = QLabel(title); label.setObjectName("Muted"); self.value = QLabel("—"); self.value.setObjectName("CardValue"); layout.addWidget(label); layout.addWidget(self.value)


class DashboardWindow(QWidget):
    """Main shell with dashboard, account management, analytics and preferences."""

    def __init__(self, user: User, finance: FinanceService, auth: AuthService) -> None:
        super().__init__(); self._user = user; self._finance = finance; self._auth = auth
        settings = Settings.load(); self._preferences_store = PreferencesStore(settings.data_dir); self._preferences = self._preferences_store.load(user.id)
        self._drawer = None; self._stack = QStackedWidget(); self.setWindowTitle("Finance Foyer"); self.resize(1380, 820); self._build_ui(); self._apply_preferences(); self.refresh()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0); root.addWidget(self._build_sidebar()); root.addWidget(self._stack, 1)
        self._stack.addWidget(self._build_dashboard_page()); self._stack.addWidget(self._build_accounts_page()); self._stack.addWidget(self._build_analysis_page()); self._stack.addWidget(self._build_budget_page())

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(230); layout = QVBoxLayout(sidebar)
        brand = QLabel("◈  Finance Foyer"); brand.setStyleSheet("font-size:20px;font-weight:700;padding:10px 4px;"); layout.addWidget(brand)
        for label, index in [("Vue d'ensemble", 0), ("Patrimoine", 0), ("Comptes", 1), ("Transactions", 0), ("Budget", 3), ("Analyses", 2)]:
            button = QPushButton(label); button.setObjectName("Nav"); button.clicked.connect(lambda checked=False, i=index: self._navigate(i)); layout.addWidget(button)
        layout.addStretch(); _, household_name, role, _ = self._finance.household_for_user(self._user.id); profile = QLabel(f"{self._user.display_name}\n{household_name} · {role}"); profile.setObjectName("Muted"); layout.addWidget(profile)
        settings_button = QPushButton("⚙  Paramètres"); settings_button.setObjectName("Nav"); settings_button.clicked.connect(self.toggle_drawer); layout.addWidget(settings_button); return sidebar

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout(); title = QLabel("Vue d'ensemble"); title.setObjectName("Title"); header.addWidget(title); header.addStretch(); menu = QPushButton("☰"); menu.clicked.connect(self.toggle_drawer); header.addWidget(menu)
        for text, callback in [("+ Membre", self._show_add_member), ("Budget", self._show_budget), ("+ Transaction", self._show_add_transaction), ("+ Placement", self._show_add_asset), ("+ Compte", self._show_add_account)]:
            button = QPushButton(text); button.clicked.connect(callback); header.addWidget(button)
        layout.addLayout(header)
        cards = QHBoxLayout(); self.gross_card = MetricCard("Patrimoine brut"); self.debt_card = MetricCard("Dettes"); self.net_card = MetricCard("Patrimoine net"); self.return_card = MetricCard("Rendement attendu / an")
        for card in (self.gross_card, self.debt_card, self.net_card, self.return_card): cards.addWidget(card)
        layout.addLayout(cards)
        history_card = QFrame(); history_card.setObjectName("Card"); history_layout = QVBoxLayout(history_card); history_layout.addWidget(QLabel("Évolution du patrimoine net")); self.net_chart = LineChart([]); history_layout.addWidget(self.net_chart); layout.addWidget(history_card)
        row = QHBoxLayout(); self.expenses_card = self._info_card("Principaux postes de dépenses"); self.risk_card = self._info_card("Diversification / concentration"); row.addWidget(self.expenses_card); row.addWidget(self.risk_card); layout.addLayout(row); return page

    def _build_accounts_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); header = QHBoxLayout(); title = QLabel("Comptes"); title.setObjectName("Title"); header.addWidget(title); header.addStretch(); add = QPushButton("+ Ajouter un compte"); add.setObjectName("Primary"); add.clicked.connect(self._show_add_account); header.addWidget(add); layout.addLayout(header)
        layout.addWidget(QLabel("Double-cliquez sur une ligne pour ouvrir l'historique.")); self.accounts_table = QTableWidget(0, 6); self.accounts_table.setHorizontalHeaderLabels(["Compte", "Type", "Solde", "Portée", "Établissement", "Actions"]); self.accounts_table.horizontalHeader().setStretchLastSection(True); self.accounts_table.cellDoubleClicked.connect(self._open_account_history); layout.addWidget(self.accounts_table, 1); return page

    def _build_analysis_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); title = QLabel("Analyses & projections"); title.setObjectName("Title"); layout.addWidget(title); self.analysis_label = QLabel("—"); self.analysis_label.setWordWrap(True); layout.addWidget(self.analysis_label); self.forecast_chart = LineChart([]); layout.addWidget(self.forecast_chart, 1); return page

    def _build_budget_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); title = QLabel("Budget du foyer"); title.setObjectName("Title"); layout.addWidget(title); self.budget_label = QLabel("—"); self.budget_label.setWordWrap(True); layout.addWidget(self.budget_label); edit = QPushButton("Modifier le budget"); edit.clicked.connect(self._show_budget); layout.addWidget(edit); layout.addStretch(); return page

    def _info_card(self, title: str) -> QFrame:
        card = QFrame(); card.setObjectName("Card"); layout = QVBoxLayout(card); layout.addWidget(QLabel(title)); label = QLabel("—"); label.setObjectName("Muted"); label.setWordWrap(True); layout.addWidget(label); card._content_label = label; return card  # type: ignore[attr-defined]

    def _navigate(self, index: int) -> None: self._stack.setCurrentIndex(index); self.refresh()

    def toggle_drawer(self) -> None:
        if self._drawer is not None: self._drawer.close(); self._drawer.deleteLater(); self._drawer = None; return
        drawer = QFrame(self); drawer.setObjectName("Drawer"); drawer.setFixedWidth(330); layout = QVBoxLayout(drawer); title = QLabel("Personnaliser l'interface"); title.setObjectName("Title"); layout.addWidget(title); layout.addWidget(QLabel("Apparence"))
        theme = QComboBox(); theme.addItems(["Sombre", "Claire"]); theme.setCurrentIndex(0 if self._preferences["theme"] == "dark" else 1); layout.addWidget(theme)
        accent = QLineEdit(str(self._preferences["accent_color"])); layout.addWidget(QLabel("Couleur d'accent")); layout.addWidget(accent)
        compact = QCheckBox("Mode compact"); compact.setChecked(bool(self._preferences["compact_mode"])); layout.addWidget(compact)
        options = []
        for key, label in [("show_net_worth", "Graphique patrimoine"), ("show_accounts", "Comptes"), ("show_budget", "Budget"), ("show_analytics", "Analyses")]:
            check = QCheckBox(label); check.setChecked(bool(self._preferences[key])); layout.addWidget(check); options.append(check)
        save = QPushButton("Enregistrer les préférences"); save.setObjectName("Primary"); layout.addWidget(save); layout.addStretch(); save.clicked.connect(lambda: self._save_preferences(theme, accent, compact, options)); drawer.move(self.width() - drawer.width(), 0); drawer.resize(drawer.width(), self.height()); drawer.show(); drawer.raise_(); self._drawer = drawer

    def _save_preferences(self, theme, accent, compact, options) -> None:
        color = accent.text().strip()
        if not color.startswith("#") or len(color) not in (4, 7): QMessageBox.warning(self, "Paramètres", "Couleur invalide. Exemple : #6C63FF."); return
        self._preferences.update({"theme": "dark" if theme.currentIndex() == 0 else "light", "accent_color": color, "compact_mode": compact.isChecked(), "show_net_worth": options[0].isChecked(), "show_accounts": options[1].isChecked(), "show_budget": options[2].isChecked(), "show_analytics": options[3].isChecked()}); self._preferences_store.save(self._user.id, self._preferences); self._apply_preferences(); self.toggle_drawer()

    def _apply_preferences(self) -> None: self.window().setStyleSheet(stylesheet(str(self._preferences["accent_color"]), str(self._preferences["theme"]), bool(self._preferences["compact_mode"])))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._drawer is not None: self._drawer.move(self.width() - self._drawer.width(), 0); self._drawer.resize(self._drawer.width(), self.height())

    def refresh(self) -> None:
        data = self._finance.dashboard(self._user.id); self._finance.record_snapshot(self._user.id); self.gross_card.value.setText(money(data["gross"])); self.debt_card.value.setText(money(data["liabilities"])); self.net_card.value.setText(money(data["net"])); self.return_card.value.setText(f"{float(data['expected_return']) * 100:.2f} %")
        expenses = data["expenses"]; self.expenses_card._content_label.setText("\n".join(f"• {key}: {money(value)}" for key, value in list(expenses.items())[:6]) or "Aucune dépense enregistrée.")  # type: ignore[attr-defined]
        self.risk_card._content_label.setText(f"HHI {float(data['hhi']):.2f} · {len(data['allocation_type'])} classes d'actifs. Indicateur descriptif, pas un conseil d'investissement.")  # type: ignore[attr-defined]
        history = self._finance.net_worth_history(self._user.id); self.net_chart.set_points([(str(row["date"]), Decimal(row["net"])) for row in history]); forecast = data["forecast"]; self.forecast_chart.set_points([(f"An {row.year}", Decimal(row.value)) for row in forecast]); self.analysis_label.setText(f"Rendement pondéré renseigné : {float(data['expected_return']) * 100:.2f} %. Projection centrale à 10 ans : {money(forecast[-1].value)}. Les scénarios dépendent des hypothèses saisies."); self.budget_label.setText(f"Dépensé : {money(data['budget_spent'])}\nBudget prévu : {money(data['budget_planned'])}"); self._refresh_accounts(data["accounts"])

    def _refresh_accounts(self, accounts) -> None:
        self.accounts_table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            for col, value in enumerate([account["name"], account["kind"], money(account["balance"]), "Foyer" if account["shared"] else "Personnel", account["institution"]]): self.accounts_table.setItem(row, col, QTableWidgetItem(str(value)))
            actions = QWidget(); box = QHBoxLayout(actions); box.setContentsMargins(2, 2, 2, 2)
            for label, callback in [("Modifier", lambda aid=int(account["id"]): self._show_edit_account(aid)), ("Historique", lambda aid=int(account["id"]): self._open_account_history(0, 0, aid)), ("Supprimer", lambda aid=int(account["id"]): self._delete_account(aid))]:
                button = QPushButton(label); button.clicked.connect(callback); box.addWidget(button)
            self.accounts_table.setCellWidget(row, 5, actions)

    def _account_form(self, title: str, account=None) -> QDialog:
        dialog = QDialog(self); dialog.setWindowTitle(title); form = QFormLayout(dialog); name = QLineEdit(str(account["name"]) if account else ""); kind = QComboBox(); kind.addItems([item.value for item in AccountKind]); institution = QLineEdit(str(account["institution"]) if account else ""); notes = QLineEdit(str(account["notes"]) if account else ""); balance = QDoubleSpinBox(); balance.setRange(-100_000_000, 100_000_000); balance.setDecimals(2); balance.setSuffix(" €"); balance.setValue(float(account["balance"]) if account else 0)
        if account: kind.setCurrentText(str(account["kind"]))
        for label, widget in [("Nom", name), ("Nature", kind), ("Solde actuel", balance), ("Établissement", institution), ("Note", notes)]: form.addRow(label, widget)
        scope = None
        if account is None: scope = QComboBox(); scope.addItems(["Personnel", "Foyer", "Dette personnelle", "Dette foyer"]); form.addRow("Usage", scope)
        save = QPushButton("Enregistrer"); save.setObjectName("Primary"); form.addRow(save)
        def submit() -> None:
            try:
                if account is None:
                    text = scope.currentText(); self._finance.add_account(self._user.id, name.text(), kind.currentText(), Decimal(str(balance.value())), shared="Foyer" in text, is_liability="Dette" in text, institution=institution.text(), notes=notes.text())
                else: self._finance.update_account(self._user.id, int(account["id"]), name=name.text(), kind=kind.currentText(), institution=institution.text(), notes=notes.text(), balance=Decimal(str(balance.value())))
            except (ValueError, PermissionError) as exc: QMessageBox.warning(dialog, "Compte", str(exc)); return
            dialog.accept(); self.refresh()
        save.clicked.connect(submit); dialog.resize(480, 310); return dialog

    def _show_add_account(self) -> None: self._account_form("Ajouter un compte").exec()
    def _show_edit_account(self, account_id: int) -> None:
        account = next((item for item in self._finance.list_accounts(self._user.id) if int(item["id"]) == account_id), None)
        if account: self._account_form("Modifier le compte", account).exec()
    def _delete_account(self, account_id: int) -> None:
        if QMessageBox.question(self, "Supprimer le compte", "Supprimer le compte et ses données associées ?") != QMessageBox.StandardButton.Yes: return
        try: self._finance.delete_account(self._user.id, account_id)
        except PermissionError as exc: QMessageBox.warning(self, "Compte", str(exc)); return
        self.refresh()

    def _open_account_history(self, row=0, column=0, account_id=None) -> None:
        if account_id is None:
            accounts = self._finance.list_accounts(self._user.id)
            if row >= len(accounts): return
            account_id = int(accounts[row]["id"])
        try: history = self._finance.account_history(self._user.id, account_id)
        except PermissionError as exc: QMessageBox.warning(self, "Historique", str(exc)); return
        dialog = QDialog(self); dialog.setWindowTitle("Évolution du compte"); dialog.resize(760, 500); layout = QVBoxLayout(dialog); chart = LineChart([(str(item["date"]), Decimal(item["balance"])) for item in history]); layout.addWidget(chart); table = QTableWidget(len(history), 2); table.setHorizontalHeaderLabels(["Date", "Solde"])
        for index, item in enumerate(history): table.setItem(index, 0, QTableWidgetItem(str(item["date"]))); table.setItem(index, 1, QTableWidgetItem(money(item["balance"])))
        layout.addWidget(table); dialog.exec()

    def _show_add_transaction(self) -> None:
        accounts = self._finance.list_accounts(self._user.id)
        if not accounts: QMessageBox.information(self, "Transaction", "Ajoutez d'abord un compte."); return
        dialog = QDialog(self); dialog.setWindowTitle("Ajouter une transaction"); form = QFormLayout(dialog); account = QComboBox(); [account.addItem(str(a["name"]), int(a["id"])) for a in accounts]; category = QLineEdit(); label = QLineEdit(); amount = QDoubleSpinBox(); amount.setRange(-100_000_000, 100_000_000); amount.setDecimals(2); amount.setSuffix(" €"); shared = QCheckBox("Transaction du foyer")
        for title, widget in [("Compte", account), ("Catégorie", category), ("Libellé", label), ("Montant (+ entrée / - dépense)", amount), ("Portée", shared)]: form.addRow(title, widget)
        save = QPushButton("Enregistrer"); save.setObjectName("Primary"); form.addRow(save); save.clicked.connect(lambda: (self._finance.add_transaction(int(account.currentData()), date.today(), category.text(), label.text(), Decimal(str(amount.value())), is_shared=shared.isChecked()), dialog.accept(), self.refresh())); dialog.resize(480, 300); dialog.exec()

    def _show_add_asset(self) -> None:
        accounts = self._finance.list_accounts(self._user.id)
        if not accounts: QMessageBox.information(self, "Placement", "Ajoutez d'abord un compte."); return
        dialog = QDialog(self); dialog.setWindowTitle("Ajouter un placement"); form = QFormLayout(dialog); account = QComboBox(); [account.addItem(str(a["name"]), int(a["id"])) for a in accounts]; label = QLineEdit(); kind = QComboBox(); kind.addItems([item.value for item in AssetKind]); value = QDoubleSpinBox(); value.setRange(0, 100_000_000); value.setDecimals(2); value.setSuffix(" €"); sector = QLineEdit(); geography = QLineEdit(); expected = QDoubleSpinBox(); expected.setRange(-100, 100); expected.setDecimals(2); expected.setValue(5); expected.setSuffix(" %")
        for title, widget in [("Compte", account), ("Libellé", label), ("Classe", kind), ("Valeur", value), ("Secteur", sector), ("Géographie", geography), ("Rendement annuel hypothétique", expected)]: form.addRow(title, widget)
        save = QPushButton("Enregistrer"); form.addRow(save); save.clicked.connect(lambda: (self._finance.add_asset(int(account.currentData()), label.text(), kind.currentText(), Decimal(str(value.value())), sector.text(), geography.text(), Decimal(str(expected.value() / 100))), dialog.accept(), self.refresh())); dialog.resize(500, 390); dialog.exec()

    def _show_budget(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer": QMessageBox.warning(self, "Budget", "Seul l'admin_foyer peut modifier le budget du foyer."); return
        dialog = QDialog(self); dialog.setWindowTitle("Budget commun mensuel"); form = QFormLayout(dialog); category = QLineEdit(); amount = QDoubleSpinBox(); amount.setRange(0, 100_000_000); amount.setDecimals(2); amount.setSuffix(" €"); form.addRow("Catégorie", category); form.addRow("Montant prévu", amount); save = QPushButton("Enregistrer"); form.addRow(save)
        def submit() -> None:
            try: self._finance.set_budget(self._user.id, category.text().strip() or "Autre", Decimal(str(amount.value())))
            except (PermissionError, ValueError) as exc: QMessageBox.warning(dialog, "Budget", str(exc)); return
            dialog.accept(); self.refresh()
        save.clicked.connect(submit); dialog.resize(430, 210); dialog.exec()

    def _show_add_member(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer": QMessageBox.warning(self, "Membre", "Seul l'admin_foyer peut créer un membre."); return
        dialog = QDialog(self); dialog.setWindowTitle("Créer un membre du foyer"); form = QFormLayout(dialog); username = QLineEdit(); display = QLineEdit(); password = QLineEdit(); password.setEchoMode(QLineEdit.EchoMode.Password); visibility = QComboBox(); visibility.addItems(["Accès au foyer", "Profil personnel uniquement"])
        for title, widget in [("Utilisateur", username), ("Nom affiché", display), ("Mot de passe", password), ("Visibilité", visibility)]: form.addRow(title, widget)
        save = QPushButton("Créer le membre"); form.addRow(save)
        def submit() -> None:
            try: self._auth.create_household_member(self._user.id, username.text(), password.text(), display.text(), can_view_household=visibility.currentIndex() == 0)
            except (PermissionError, ValueError) as exc: QMessageBox.warning(dialog, "Membre", str(exc)); return
            dialog.accept()
        save.clicked.connect(submit); dialog.resize(460, 280); dialog.exec()
