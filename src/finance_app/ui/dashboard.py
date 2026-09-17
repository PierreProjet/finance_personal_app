from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from finance_app.config import Settings
from finance_app.models.entities import AccountKind, AssetKind, User
from finance_app.services.auth_service import AuthService
from finance_app.services.finance_service import FinanceService
from finance_app.ui.charts import LineChart
from finance_app.ui.preferences import PreferencesStore
from finance_app.ui.theme import stylesheet


def money(value: Decimal | object) -> str:
    amount = Decimal(value)
    return f"{amount:,.2f} €".replace(",", " ")


class MetricCard(QFrame):
    def __init__(self, title: str, hint: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setObjectName("Muted")
        self.value = QLabel("—")
        self.value.setObjectName("CardValue")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        if hint:
            help_label = QLabel(hint)
            help_label.setObjectName("Muted")
            help_label.setWordWrap(True)
            layout.addWidget(help_label)


class DashboardWindow(QWidget):
    """Desktop shell for personal and household financial management."""

    def __init__(self, user: User, finance: FinanceService, auth: AuthService) -> None:
        super().__init__()
        self._user = user
        self._finance = finance
        self._auth = auth
        settings = Settings.load()
        self._preferences_store = PreferencesStore(settings.data_dir)
        self._preferences = self._preferences_store.load(user.id)
        self._drawer: QFrame | None = None
        self._pref_controls: dict[str, QWidget] = {}
        self._stack = QStackedWidget()
        self._page_layouts: list[QVBoxLayout] = []
        self._accounts_cache: list[dict[str, object]] = []
        self._sidebar_buttons: list[QPushButton] = []
        self.setWindowTitle("Finance Foyer")
        self.resize(1460, 900)
        self._build_ui()
        self._apply_preferences()
        self.refresh()

    def _page_layout(self, page: QWidget) -> QVBoxLayout:
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self._page_layouts.append(layout)
        return layout

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._sidebar = self._build_sidebar()
        root.addWidget(self._sidebar)
        root.addWidget(self._stack, 1)
        pages = [
            self._build_overview_page(),
            self._build_heritage_page(),
            self._build_accounts_page(),
            self._build_transactions_page(),
            self._build_budget_page(),
            self._build_analysis_page(),
            self._build_household_page(),
        ]
        for page in pages:
            self._stack.addWidget(page)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(6)

        self._brand = QLabel("◈  Finance Foyer")
        self._brand.setStyleSheet("font-size:20px;font-weight:700;padding:10px 4px;")
        layout.addWidget(self._brand)
        subtitle = QLabel("Pilotage personnel & foyer")
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        destinations = [
            ("⌂  Vue d'ensemble", 0, "Synthèse essentielle"),
            ("◈  Patrimoine", 1, "Brut, net, historique, projections"),
            ("▣  Comptes & placements", 2, "Soldes, caractéristiques, historique"),
            ("↕  Transactions", 3, "Flux par compte et catégories"),
            ("◎  Budgets & projets", 4, "Prévu, réel, projets du foyer"),
            ("⌁  Analyse", 5, "Allocation, risque, profils"),
            ("♟  Foyer", 6, "Membres, droits, nom du foyer"),
        ]
        for label, index, tooltip in destinations:
            button = QPushButton(label)
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolTip(tooltip)
            button.clicked.connect(
                lambda checked=False, i=index: self._navigate(i)
            )
            self._sidebar_buttons.append(button)
            layout.addWidget(button)
        self._sidebar_buttons[0].setChecked(True)

        layout.addStretch()
        self._sidebar_profile = QLabel("")
        self._sidebar_profile.setObjectName("Muted")
        self._sidebar_profile.setWordWrap(True)
        layout.addWidget(self._sidebar_profile)
        settings_button = QPushButton("⚙  Personnaliser l'interface")
        settings_button.setObjectName("Nav")
        settings_button.clicked.connect(self.toggle_drawer)
        layout.addWidget(settings_button)
        return sidebar

    def _header(self, title: str, subtitle: str = "") -> tuple[QWidget, QHBoxLayout]:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("Title")
        text.addWidget(heading)
        if subtitle:
            hint = QLabel(subtitle)
            hint.setObjectName("Muted")
            hint.setWordWrap(True)
            text.addWidget(hint)
        layout.addLayout(text)
        layout.addStretch()
        return wrapper, layout

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)
        return card, layout

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, header_layout = self._header(
            "Vue d'ensemble",
            "Une synthèse courte : situation, rythme de dépenses et dernières opérations.",
        )
        for text, callback in [
            ("+ Transaction", self._show_add_transaction),
            ("+ Compte", self._show_add_account),
            ("⚙", self.toggle_drawer),
        ]:
            button = QPushButton(text)
            if text == "+ Transaction":
                button.setObjectName("Primary")
            button.clicked.connect(callback)
            header_layout.addWidget(button)
        layout.addWidget(header)

        self._overview_grid = QGridLayout()
        self._overview_grid.setSpacing(14)
        layout.addLayout(self._overview_grid, 1)

        self._overview_metrics = QWidget()
        metrics = QHBoxLayout(self._overview_metrics)
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(12)
        self.overview_net = MetricCard("Patrimoine net", "Actifs moins dettes")
        self.overview_gross = MetricCard("Patrimoine brut", "Total des actifs")
        self.overview_budget = MetricCard("Dépenses du mois", "Transactions négatives")
        self.overview_accounts = MetricCard("Comptes suivis", "Personnel + foyer visible")
        for card in (
            self.overview_net,
            self.overview_gross,
            self.overview_budget,
            self.overview_accounts,
        ):
            metrics.addWidget(card)

        self._overview_history, history_layout = self._card("Tendance du patrimoine net")
        self.overview_chart = LineChart([])
        self.overview_chart.setMinimumHeight(220)
        history_layout.addWidget(self.overview_chart)

        self._overview_budget_card, budget_layout = self._card("Budget du mois")
        self.overview_budget_progress = QProgressBar()
        self.overview_budget_progress.setRange(0, 100)
        self.overview_budget_label = QLabel("—")
        self.overview_budget_label.setObjectName("Muted")
        self.overview_expenses_label = QLabel("—")
        self.overview_expenses_label.setWordWrap(True)
        budget_layout.addWidget(self.overview_budget_progress)
        budget_layout.addWidget(self.overview_budget_label)
        budget_layout.addWidget(self.overview_expenses_label)
        budget_layout.addStretch()

        self._overview_recent, recent_layout = self._card("Transactions récentes")
        self.overview_recent_table = QTableWidget(0, 4)
        self.overview_recent_table.setHorizontalHeaderLabels(
            ["Date", "Compte", "Catégorie", "Montant"]
        )
        self.overview_recent_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        recent_layout.addWidget(self.overview_recent_table)

        self._apply_overview_layout()
        return page

    def _build_heritage_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, controls = self._header(
            "Patrimoine",
            "Le brut additionne vos actifs. Le net retire les dettes et donne la "
            "valeur résiduelle.",
        )
        controls.addWidget(QLabel("Modèle"))
        self.heritage_model = QComboBox()
        self.heritage_model.addItem("Prudent · 2,5 %", "prudent")
        self.heritage_model.addItem("Central · 4,5 %", "central")
        self.heritage_model.addItem("Dynamique · 6,5 %", "dynamique")
        self.heritage_model.addItem("Allocation saisie", "allocation")
        controls.addWidget(self.heritage_model)
        controls.addWidget(QLabel("Horizon"))
        self.heritage_horizon = QComboBox()
        for years in (1, 3, 5, 10, 15, 20, 25, 30):
            self.heritage_horizon.addItem(f"{years} ans", years)
        controls.addWidget(self.heritage_horizon)
        self.heritage_model.currentIndexChanged.connect(self._refresh_heritage)
        self.heritage_horizon.currentIndexChanged.connect(self._refresh_heritage)
        layout.addWidget(header)

        cards = QHBoxLayout()
        self.heritage_gross = MetricCard(
            "Patrimoine brut",
            "Valeur de tous les comptes et actifs avant déduction des dettes.",
        )
        self.heritage_debt = MetricCard(
            "Dettes",
            "Capital restant représenté par les comptes marqués comme dettes.",
        )
        self.heritage_net = MetricCard(
            "Patrimoine net",
            "Patrimoine brut − dettes. C'est l'indicateur de valeur nette.",
        )
        for card in (self.heritage_gross, self.heritage_debt, self.heritage_net):
            cards.addWidget(card)
        layout.addLayout(cards)

        chart_card, chart_layout = self._card("Historique + projection")
        self.heritage_chart = LineChart([])
        self.heritage_projection_label = QLabel("—")
        self.heritage_projection_label.setObjectName("Muted")
        self.heritage_projection_label.setWordWrap(True)
        chart_layout.addWidget(self.heritage_chart, 1)
        chart_layout.addWidget(self.heritage_projection_label)
        layout.addWidget(chart_card, 1)
        return page

    def _build_accounts_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, actions = self._header(
            "Comptes & placements",
            "Chaque modification de solde crée un point d'historique pour suivre l'évolution.",
        )
        add = QPushButton("+ Ajouter un compte")
        add.setObjectName("Primary")
        add.clicked.connect(self._show_add_account)
        actions.addWidget(add)
        layout.addWidget(header)

        self.accounts_table = QTableWidget(0, 7)
        self.accounts_table.setHorizontalHeaderLabels(
            ["Compte", "Type", "Solde", "Portée", "Ouverture", "Frais", "Actions"]
        )
        self.accounts_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.accounts_table.horizontalHeader().setStretchLastSection(True)
        self.accounts_table.setColumnWidth(6, 390)
        self.accounts_table.cellDoubleClicked.connect(self._open_account_history)
        layout.addWidget(self.accounts_table, 1)
        return page

    def _build_transactions_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, actions = self._header(
            "Transactions",
            "Les entrées augmentent le solde ; les dépenses le diminuent. Filtrez par compte.",
        )
        self.transaction_filter = QComboBox()
        self.transaction_filter.addItem("Tous les comptes", None)
        self.transaction_filter.currentIndexChanged.connect(self._refresh_transactions)
        actions.addWidget(self.transaction_filter)
        add = QPushButton("+ Ajouter une transaction")
        add.setObjectName("Primary")
        add.clicked.connect(self._show_add_transaction)
        actions.addWidget(add)
        layout.addWidget(header)

        self.transactions_table = QTableWidget(0, 7)
        self.transactions_table.setHorizontalHeaderLabels(
            ["Date", "Compte", "Libellé", "Catégorie", "Montant", "Portée", "Action"]
        )
        self.transactions_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.transactions_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.transactions_table, 1)
        return page

    def _build_budget_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, actions = self._header(
            "Budgets & projets",
            "Comparez les prévisions aux dépenses réelles et répartissez les projets du foyer.",
        )
        edit = QPushButton("+ Poste budgétaire")
        edit.clicked.connect(self._show_budget)
        actions.addWidget(edit)
        project = QPushButton("+ Projet du foyer")
        project.setObjectName("Primary")
        project.clicked.connect(self._show_household_project)
        actions.addWidget(project)
        layout.addWidget(header)

        cards = QHBoxLayout()
        self.budget_planned_card = MetricCard("Prévu ce mois")
        self.budget_actual_card = MetricCard("Réalisé ce mois")
        self.budget_remaining_card = MetricCard("Reste budgétaire")
        for card in (
            self.budget_planned_card,
            self.budget_actual_card,
            self.budget_remaining_card,
        ):
            cards.addWidget(card)
        layout.addLayout(cards)

        budget_card, budget_layout = self._card("Catégories et postes de dépense")
        self.budget_table = QTableWidget(0, 4)
        self.budget_table.setHorizontalHeaderLabels(
            ["Catégorie", "Prévu", "Réel", "Écart"]
        )
        self.budget_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        budget_layout.addWidget(self.budget_table)
        layout.addWidget(budget_card, 1)

        projects_card, projects_layout = self._card("Budgets spécifiques du foyer")
        project_actions = QHBoxLayout()
        contribution = QPushButton("+ Répartir un financement")
        contribution.clicked.connect(self._show_project_contribution)
        project_actions.addWidget(contribution)
        project_actions.addStretch()
        projects_layout.addLayout(project_actions)
        self.projects_table = QTableWidget(0, 5)
        self.projects_table.setHorizontalHeaderLabels(
            ["Projet", "Type", "Cible", "Statut", "Répartition"]
        )
        self.projects_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        projects_layout.addWidget(self.projects_table)
        layout.addWidget(projects_card, 1)
        return page

    def _build_analysis_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, controls = self._header(
            "Analyse",
            "Analyse descriptive : allocation, concentration, géographie et profils de référence.",
        )
        controls.addWidget(QLabel("Profil"))
        self.analysis_profile = QComboBox()
        self.analysis_profile.addItem("Prudent", "prudent")
        self.analysis_profile.addItem("Équilibré", "equilibre")
        self.analysis_profile.addItem("Dynamique", "dynamique")
        self.analysis_profile.currentIndexChanged.connect(self._refresh_analysis)
        controls.addWidget(self.analysis_profile)
        layout.addWidget(header)

        self.analysis_summary = QLabel("—")
        self.analysis_summary.setWordWrap(True)
        layout.addWidget(self.analysis_summary)

        grid = QGridLayout()
        self.analysis_type = self._text_card("Allocation par classe")
        self.analysis_sector = self._text_card("Répartition sectorielle")
        self.analysis_geo = self._text_card("Répartition géographique")
        self.analysis_profile_card = self._text_card("Profil de référence sélectionné")
        grid.addWidget(self.analysis_type, 0, 0)
        grid.addWidget(self.analysis_sector, 0, 1)
        grid.addWidget(self.analysis_geo, 1, 0)
        grid.addWidget(self.analysis_profile_card, 1, 1)
        layout.addLayout(grid)

        chart_card, chart_layout = self._card("Projection descriptive")
        self.analysis_chart = LineChart([])
        chart_layout.addWidget(self.analysis_chart)
        layout.addWidget(chart_card, 1)
        return page

    def _build_household_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)
        header, actions = self._header(
            "Foyer",
            "Centralisez les membres, les droits et les projets communs sans perdre "
            "la vue personnelle.",
        )
        add = QPushButton("+ Ajouter un membre")
        add.setObjectName("Primary")
        add.clicked.connect(self._show_add_member)
        actions.addWidget(add)
        layout.addWidget(header)

        name_card, name_layout = self._card("Identité du foyer")
        row = QHBoxLayout()
        self.household_name = QLineEdit()
        rename = QPushButton("Renommer le foyer")
        rename.clicked.connect(self._rename_household)
        row.addWidget(self.household_name, 1)
        row.addWidget(rename)
        name_layout.addLayout(row)
        layout.addWidget(name_card)

        members_card, members_layout = self._card("Membres et visibilité")
        self.members_table = QTableWidget(0, 4)
        self.members_table.setHorizontalHeaderLabels(
            ["Membre", "Identifiant", "Rôle", "Visibilité foyer"]
        )
        self.members_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        members_layout.addWidget(self.members_table)
        layout.addWidget(members_card, 1)

        family_projects, family_projects_layout = self._card("Engagements communs")
        self.household_projects_label = QLabel("—")
        self.household_projects_label.setWordWrap(True)
        family_projects_layout.addWidget(self.household_projects_label)
        layout.addWidget(family_projects)
        return page

    def _text_card(self, title: str) -> QFrame:
        card, layout = self._card(title)
        label = QLabel("—")
        label.setObjectName("Muted")
        label.setWordWrap(True)
        layout.addWidget(label)
        card._content_label = label  # type: ignore[attr-defined]
        return card

    def _navigate(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        if 0 <= index < len(self._sidebar_buttons):
            self._sidebar_buttons[index].setChecked(True)
        self.refresh()

    def toggle_drawer(self) -> None:
        if self._drawer is not None:
            self._drawer.close()
            self._drawer.deleteLater()
            self._drawer = None
            return

        drawer = QFrame(self)
        drawer.setObjectName("Drawer")
        drawer.setFixedWidth(410)
        outer = QVBoxLayout(drawer)
        title = QLabel("Personnalisation avancée")
        title.setObjectName("Title")
        outer.addWidget(title)
        hint = QLabel(
            "Dépliez les sections pour régler les couleurs, la densité, les graphiques "
            "et la disposition de la synthèse."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        toolbox = QToolBox()
        scroll.setWidget(toolbox)
        outer.addWidget(scroll, 1)

        appearance = QWidget()
        appearance_form = QFormLayout(appearance)
        theme = QComboBox()
        theme.addItem("Sombre", "dark")
        theme.addItem("Clair", "light")
        theme.setCurrentIndex(0 if self._preferences["theme"] == "dark" else 1)
        appearance_form.addRow("Thème", theme)
        self._pref_controls["theme"] = theme
        for key, label in [
            ("accent_color", "Accent"),
            ("sidebar_color", "Menu latéral"),
            ("surface_color", "Cartes"),
            ("chart_color", "Graphiques"),
        ]:
            field = self._color_control(key, str(self._preferences[key]))
            appearance_form.addRow(label, field)
        toolbox.addItem(appearance, "Apparence & couleurs")

        density = QWidget()
        density_form = QFormLayout(density)
        compact = QComboBox()
        compact.addItem("Étendu · confortable", False)
        compact.addItem("Compact · dense", True)
        compact.setCurrentIndex(1 if self._preferences["compact_mode"] else 0)
        density_form.addRow("Densité", compact)
        self._pref_controls["compact_mode"] = compact
        overview_layout = QComboBox()
        overview_layout.addItem("Synthèse d'abord", "synthese")
        overview_layout.addItem("Graphiques d'abord", "graphiques")
        overview_layout.addItem("Matrice compacte", "compact")
        self._select_combo_data(overview_layout, self._preferences["overview_layout"])
        density_form.addRow("Disposition vue d'ensemble", overview_layout)
        self._pref_controls["overview_layout"] = overview_layout
        toolbox.addItem(density, "Densité & disposition")

        navigation = QWidget()
        navigation_layout = QVBoxLayout(navigation)
        for key, label in [
            ("show_net_worth", "Afficher la tendance patrimoine"),
            ("show_recent_transactions", "Afficher les transactions récentes"),
            ("show_budget", "Afficher le bloc budget"),
            ("show_analytics", "Afficher les indicateurs d'analyse"),
        ]:
            check = QCheckBox(label)
            check.setChecked(bool(self._preferences[key]))
            navigation_layout.addWidget(check)
            self._pref_controls[key] = check
        navigation_layout.addStretch()
        toolbox.addItem(navigation, "Modules visibles")

        charts = QWidget()
        charts_form = QFormLayout(charts)
        chart_type = QComboBox()
        chart_type.addItem("Courbe", "line")
        chart_type.addItem("Aire", "area")
        chart_type.addItem("Barres", "bar")
        self._select_combo_data(chart_type, self._preferences["chart_type"])
        charts_form.addRow("Type de graphique", chart_type)
        self._pref_controls["chart_type"] = chart_type
        axes = QCheckBox("Afficher les axes et l'échelle")
        axes.setChecked(bool(self._preferences["show_chart_axes"]))
        charts_form.addRow("Axes", axes)
        self._pref_controls["show_chart_axes"] = axes
        value_mode = QComboBox()
        value_mode.addItem("Valeur absolue (€)", "absolute")
        value_mode.addItem("Variation depuis le premier point (%)", "percent")
        self._select_combo_data(value_mode, self._preferences["chart_value_mode"])
        charts_form.addRow("Axe vertical", value_mode)
        self._pref_controls["chart_value_mode"] = value_mode
        toolbox.addItem(charts, "Graphiques & axes")

        projections = QWidget()
        projection_form = QFormLayout(projections)
        model = QComboBox()
        model.addItem("Prudent · 2,5 %", "prudent")
        model.addItem("Central · 4,5 %", "central")
        model.addItem("Dynamique · 6,5 %", "dynamique")
        model.addItem("Allocation saisie", "allocation")
        self._select_combo_data(model, self._preferences["projection_model"])
        projection_form.addRow("Modèle par défaut", model)
        self._pref_controls["projection_model"] = model
        horizon = QComboBox()
        for years in (1, 3, 5, 10, 15, 20, 25, 30):
            horizon.addItem(f"{years} ans", years)
        self._select_combo_data(horizon, self._preferences["heritage_horizon"])
        projection_form.addRow("Horizon par défaut", horizon)
        self._pref_controls["heritage_horizon"] = horizon
        toolbox.addItem(projections, "Projections")

        save = QPushButton("Enregistrer et appliquer")
        save.setObjectName("Primary")
        save.clicked.connect(self._save_preferences)
        outer.addWidget(save)
        drawer.move(self.width() - drawer.width(), 0)
        drawer.resize(drawer.width(), self.height())
        drawer.show()
        drawer.raise_()
        self._drawer = drawer

    def _color_control(self, key: str, value: str) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit(value)
        picker = QPushButton("◉")
        picker.setToolTip("Ouvrir le cercle chromatique")
        picker.clicked.connect(
            lambda checked=False, target=field: self._pick_color(target)
        )
        row.addWidget(field, 1)
        row.addWidget(picker)
        self._pref_controls[key] = field
        return wrapper

    def _pick_color(self, field: QLineEdit) -> None:
        current = QColor(field.text().strip())
        color = QColorDialog.getColor(
            current if current.isValid() else QColor("#6C63FF"),
            self,
        )
        if color.isValid():
            field.setText(color.name().upper())

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def _save_preferences(self) -> None:
        color_keys = ("accent_color", "sidebar_color", "surface_color", "chart_color")
        for key in color_keys:
            field = self._pref_controls[key]
            if not isinstance(field, QLineEdit):
                continue
            color = QColor(field.text().strip())
            if not color.isValid():
                QMessageBox.warning(
                    self,
                    "Paramètres",
                    f"Couleur invalide pour {key}. Exemple : #6C63FF.",
                )
                return
            self._preferences[key] = color.name().upper()

        theme = self._pref_controls["theme"]
        compact = self._pref_controls["compact_mode"]
        overview = self._pref_controls["overview_layout"]
        chart_type = self._pref_controls["chart_type"]
        value_mode = self._pref_controls["chart_value_mode"]
        model = self._pref_controls["projection_model"]
        horizon = self._pref_controls["heritage_horizon"]
        if isinstance(theme, QComboBox):
            self._preferences["theme"] = theme.currentData()
        if isinstance(compact, QComboBox):
            self._preferences["compact_mode"] = bool(compact.currentData())
        if isinstance(overview, QComboBox):
            self._preferences["overview_layout"] = overview.currentData()
        if isinstance(chart_type, QComboBox):
            self._preferences["chart_type"] = chart_type.currentData()
        if isinstance(value_mode, QComboBox):
            self._preferences["chart_value_mode"] = value_mode.currentData()
        if isinstance(model, QComboBox):
            self._preferences["projection_model"] = model.currentData()
        if isinstance(horizon, QComboBox):
            self._preferences["heritage_horizon"] = horizon.currentData()

        for key in (
            "show_net_worth",
            "show_recent_transactions",
            "show_budget",
            "show_analytics",
        ):
            widget = self._pref_controls[key]
            if isinstance(widget, QCheckBox):
                self._preferences[key] = widget.isChecked()

        self._preferences_store.save(self._user.id, self._preferences)
        self._apply_preferences()
        self._sync_projection_controls()
        self.toggle_drawer()
        self.refresh()

    def _sync_projection_controls(self) -> None:
        self._select_combo_data(self.heritage_model, self._preferences["projection_model"])
        self._select_combo_data(self.heritage_horizon, self._preferences["heritage_horizon"])

    def _apply_preferences(self) -> None:
        self.window().setStyleSheet(
            stylesheet(
                str(self._preferences["accent_color"]),
                str(self._preferences["theme"]),
                bool(self._preferences["compact_mode"]),
                str(self._preferences["sidebar_color"]),
                str(self._preferences["surface_color"]),
            )
        )
        compact = bool(self._preferences["compact_mode"])
        self._sidebar.setFixedWidth(190 if compact else 275)
        self._brand.setText("◈ Finance" if compact else "◈  Finance Foyer")
        self._sidebar_profile.setVisible(not compact)
        margins = (16, 14, 16, 14) if compact else (28, 24, 28, 24)
        spacing = 9 if compact else 16
        for layout in self._page_layouts:
            layout.setContentsMargins(*margins)
            layout.setSpacing(spacing)
        self.accounts_table.verticalHeader().setDefaultSectionSize(28 if compact else 38)
        self.transactions_table.verticalHeader().setDefaultSectionSize(28 if compact else 38)
        self._overview_history.setVisible(bool(self._preferences["show_net_worth"]))
        self._overview_recent.setVisible(bool(self._preferences["show_recent_transactions"]))
        self._overview_budget_card.setVisible(bool(self._preferences["show_budget"]))
        self._apply_overview_layout()
        for chart in (
            self.overview_chart,
            self.heritage_chart,
            self.analysis_chart,
        ):
            chart.set_options(
                str(self._preferences["chart_type"]),
                bool(self._preferences["show_chart_axes"]),
                str(self._preferences["chart_color"]),
                str(self._preferences["chart_value_mode"]),
            )

    def _apply_overview_layout(self) -> None:
        if not hasattr(self, "_overview_grid"):
            return
        widgets = [
            self._overview_metrics,
            self._overview_history,
            self._overview_budget_card,
            self._overview_recent,
        ]
        for widget in widgets:
            self._overview_grid.removeWidget(widget)
        mode = str(self._preferences.get("overview_layout", "synthese"))
        if mode == "graphiques":
            positions = [
                (self._overview_history, 0, 0, 1, 2),
                (self._overview_metrics, 1, 0, 1, 2),
                (self._overview_recent, 2, 0, 1, 1),
                (self._overview_budget_card, 2, 1, 1, 1),
            ]
        elif mode == "compact":
            positions = [
                (self._overview_metrics, 0, 0, 1, 2),
                (self._overview_history, 1, 0, 1, 1),
                (self._overview_recent, 1, 1, 1, 1),
                (self._overview_budget_card, 2, 0, 1, 2),
            ]
        else:
            positions = [
                (self._overview_metrics, 0, 0, 1, 2),
                (self._overview_budget_card, 1, 0, 1, 1),
                (self._overview_recent, 1, 1, 1, 1),
                (self._overview_history, 2, 0, 1, 2),
            ]
        for widget, row, column, row_span, column_span in positions:
            self._overview_grid.addWidget(widget, row, column, row_span, column_span)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._drawer is not None:
            self._drawer.move(self.width() - self._drawer.width(), 0)
            self._drawer.resize(self._drawer.width(), self.height())

    def refresh(self) -> None:
        self._finance.record_snapshot(self._user.id)
        data = self._finance.dashboard(self._user.id)
        self._accounts_cache = list(data["accounts"])
        household_id, household_name, role, _ = self._finance.household_for_user(
            self._user.id
        )
        del household_id
        self._sidebar_profile.setText(
            f"{self._user.display_name}\n{household_name} · {role}"
        )
        self.household_name.setText(household_name)

        self.overview_net.value.setText(money(data["net"]))
        self.overview_gross.value.setText(money(data["gross"]))
        self.overview_budget.value.setText(money(data["budget_spent"]))
        self.overview_accounts.value.setText(str(len(self._accounts_cache)))
        self.heritage_gross.value.setText(money(data["gross"]))
        self.heritage_debt.value.setText(money(data["liabilities"]))
        self.heritage_net.value.setText(money(data["net"]))

        history = self._finance.net_worth_history(self._user.id)
        history_points = [
            (str(row["date"]), Decimal(row["net"]))
            for row in history
        ]
        self.overview_chart.set_points(history_points)
        self._refresh_overview_budget(data)
        self._refresh_overview_recent(data["recent_transactions"])
        self._refresh_accounts(self._accounts_cache)
        self._sync_transaction_filter(self._accounts_cache)
        self._refresh_transactions()
        self._refresh_budget()
        self._refresh_heritage()
        self._refresh_analysis()
        self._refresh_household()

    def _refresh_overview_budget(self, data: dict[str, object]) -> None:
        planned = Decimal(data["budget_planned"])
        spent = Decimal(data["budget_spent"])
        percent = int(min(100, (spent / planned * 100) if planned > 0 else 0))
        self.overview_budget_progress.setValue(percent)
        self.overview_budget_label.setText(
            f"{money(spent)} réalisés sur {money(planned)} prévus"
            if planned > 0
            else f"{money(spent)} de dépenses · aucun budget planifié"
        )
        expenses = data["expenses"]
        lines = [
            f"{key}: {money(value)}"
            for key, value in list(expenses.items())[:4]
        ]
        self.overview_expenses_label.setText(
            "Principaux postes · " + " · ".join(lines)
            if lines
            else "Aucune dépense enregistrée ce mois."
        )

    def _refresh_overview_recent(self, rows: object) -> None:
        transactions = list(rows)
        self.overview_recent_table.setRowCount(len(transactions))
        for row_index, transaction in enumerate(transactions):
            values = [
                transaction["date"],
                transaction["account"],
                transaction["category"],
                money(transaction["amount"]),
            ]
            for column, value in enumerate(values):
                self.overview_recent_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

    def _refresh_heritage(self) -> None:
        if not hasattr(self, "heritage_model"):
            return
        model = str(self.heritage_model.currentData() or "central")
        years = int(self.heritage_horizon.currentData() or 10)
        try:
            projection = self._finance.projection(self._user.id, model, years)
        except ValueError:
            return
        history = self._finance.net_worth_history(self._user.id)
        points = [
            (str(row["date"]), Decimal(row["net"]))
            for row in history[-24:]
        ]
        future = [(f"A+{point.year}", Decimal(point.value)) for point in projection[1:]]
        self.heritage_chart.set_points([*points, *future])
        if projection:
            last = projection[-1]
            self.heritage_projection_label.setText(
                f"Modèle « {model} » · horizon {years} ans · valeur projetée : "
                f"{money(last.value)}. Projection déterministe fondée sur une hypothèse "
                "de rendement constant ; elle ne constitue pas une prévision garantie."
            )

    def _refresh_accounts(self, accounts: list[dict[str, object]]) -> None:
        self.accounts_table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            fee = (
                f"{float(Decimal(account['annual_fee_percent'])):.2f} % + "
                f"{money(account['annual_fee_fixed'])}"
            )
            opened = account["opened_on"] or "—"
            values = [
                account["name"],
                account["kind"],
                money(account["balance"]),
                "Foyer" if account["shared"] else "Personnel",
                opened,
                fee,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, int(account["id"]))
                self.accounts_table.setItem(row, column, item)

            actions = QWidget()
            box = QHBoxLayout(actions)
            box.setContentsMargins(2, 2, 2, 2)
            account_id = int(account["id"])
            callbacks = [
                ("Modifier", lambda checked=False, aid=account_id: self._show_edit_account(aid)),
                ("+ Point", lambda checked=False, aid=account_id: self._show_add_history(aid)),
                (
                    "Historique",
                    lambda checked=False, aid=account_id: self._open_account_history(
                        account_id=aid
                    ),
                ),
                ("Archiver", lambda checked=False, aid=account_id: self._archive_account(aid)),
            ]
            for label, callback in callbacks:
                button = QPushButton(label)
                button.clicked.connect(callback)
                box.addWidget(button)
            self.accounts_table.setCellWidget(row, 6, actions)

    def _sync_transaction_filter(self, accounts: list[dict[str, object]]) -> None:
        current = self.transaction_filter.currentData()
        self.transaction_filter.blockSignals(True)
        self.transaction_filter.clear()
        self.transaction_filter.addItem("Tous les comptes", None)
        for account in accounts:
            self.transaction_filter.addItem(str(account["name"]), int(account["id"]))
        self._select_combo_data(self.transaction_filter, current)
        self.transaction_filter.blockSignals(False)

    def _refresh_transactions(self) -> None:
        if not hasattr(self, "transactions_table"):
            return
        account_id = self.transaction_filter.currentData()
        try:
            rows = self._finance.list_transactions(
                self._user.id,
                int(account_id) if account_id is not None else None,
            )
        except PermissionError:
            rows = []
        self.transactions_table.setRowCount(len(rows))
        for row_index, transaction in enumerate(rows):
            values = [
                transaction["date"],
                transaction["account"],
                transaction["label"],
                transaction["category"],
                money(transaction["amount"]),
                "Foyer" if transaction["shared"] else "Personnel",
            ]
            for column, value in enumerate(values):
                self.transactions_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )
            delete = QPushButton("Supprimer")
            transaction_id = int(transaction["id"])
            delete.clicked.connect(
                lambda checked=False, tid=transaction_id: self._delete_transaction(tid)
            )
            self.transactions_table.setCellWidget(row_index, 6, delete)

    def _refresh_budget(self) -> None:
        if not hasattr(self, "budget_table"):
            return
        summary = self._finance.budget_summary(self._user.id)
        planned = sum((Decimal(row["planned"]) for row in summary), Decimal("0"))
        actual = sum((Decimal(row["actual"]) for row in summary), Decimal("0"))
        remaining = planned - actual
        self.budget_planned_card.value.setText(money(planned))
        self.budget_actual_card.value.setText(money(actual))
        self.budget_remaining_card.value.setText(money(remaining))
        self.budget_table.setRowCount(len(summary))
        for row_index, row in enumerate(summary):
            values = [
                row["category"],
                money(row["planned"]),
                money(row["actual"]),
                money(row["remaining"]),
            ]
            for column, value in enumerate(values):
                self.budget_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

        projects = self._finance.list_household_projects(self._user.id)
        self.projects_table.setRowCount(len(projects))
        for row_index, project in enumerate(projects):
            shares = project["shares"]
            parts = []
            for share in shares:
                detail = money(share["amount"])
                if Decimal(share["monthly_amount"]) > 0:
                    detail += (
                        f" + {money(share['monthly_amount'])}/mois × "
                        f"{share['duration_months']}"
                    )
                parts.append(f"{share['member']} · {share['kind']} · {detail}")
            values = [
                project["name"],
                project["kind"],
                money(project["target_amount"]),
                project["status"],
                " | ".join(parts) if parts else "À répartir",
            ]
            for column, value in enumerate(values):
                self.projects_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

    def _refresh_analysis(self) -> None:
        if not hasattr(self, "analysis_profile"):
            return
        profile = str(self.analysis_profile.currentData() or "equilibre")
        analysis = self._finance.investment_analysis(self._user.id, profile)
        hhi = float(Decimal(analysis["hhi"]))
        expected = float(Decimal(analysis["expected_return"])) * 100
        self.analysis_summary.setText(
            f"Concentration HHI : {hhi:.2f} · rendement annuel pondéré renseigné : "
            f"{expected:.2f} %. Le profil choisi sert uniquement de repère descriptif."
        )
        data = self._finance.dashboard(self._user.id)
        self._set_card_lines(self.analysis_type, data["allocation_type"])
        self._set_card_lines(self.analysis_sector, analysis["by_sector"])
        self._set_card_lines(self.analysis_geo, analysis["by_geography"])
        target = analysis["target"]
        profile_text = "\n".join(f"• {key}: {value} %" for key, value in target.items())
        self.analysis_profile_card._content_label.setText(  # type: ignore[attr-defined]
            profile_text
        )
        projection = self._finance.projection(self._user.id, "allocation", 10)
        self.analysis_chart.set_points(
            [(f"A+{point.year}", Decimal(point.value)) for point in projection]
        )

    @staticmethod
    def _set_card_lines(card: QFrame, values: object) -> None:
        mapping = dict(values)
        text = "\n".join(f"• {key}: {money(value)}" for key, value in mapping.items())
        card._content_label.setText(  # type: ignore[attr-defined]
            text or "Aucune donnée renseignée."
        )

    def _refresh_household(self) -> None:
        if not hasattr(self, "members_table"):
            return
        members = self._auth.list_household_members(self._user.id)
        self.members_table.setRowCount(len(members))
        for row_index, member in enumerate(members):
            values = [
                member["display_name"],
                member["username"],
                member["role"],
                "Oui" if member["can_view_household"] else "Personnel uniquement",
            ]
            for column, value in enumerate(values):
                self.members_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )
        projects = self._finance.list_household_projects(self._user.id)
        lines = []
        for project in projects[:6]:
            lines.append(
                f"• {project['name']} · {project['status']} · cible "
                f"{money(project['target_amount'])} · {len(project['shares'])} participation(s)"
            )
        self.household_projects_label.setText(
            "\n".join(lines) if lines else "Aucun projet commun créé."
        )

    def _account_form(self, title: str, account: dict[str, object] | None = None) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        form = QFormLayout(dialog)

        name = QLineEdit(str(account["name"]) if account else "")
        kind = QComboBox()
        kind.addItems([item.value for item in AccountKind])
        institution = QLineEdit(str(account["institution"]) if account else "")
        notes = QLineEdit(str(account["notes"]) if account else "")
        balance = QDoubleSpinBox()
        balance.setRange(-100_000_000, 100_000_000)
        balance.setDecimals(2)
        balance.setSuffix(" €")
        balance.setValue(float(Decimal(account["balance"])) if account else 0)
        if account:
            kind.setCurrentText(str(account["kind"]))

        opened = QDateEdit()
        opened.setCalendarPopup(True)
        opened.setDisplayFormat("dd/MM/yyyy")
        opened_value = account["opened_on"] if account else date.today()
        if isinstance(opened_value, date):
            opened.setDate(QDate(opened_value.year, opened_value.month, opened_value.day))
        else:
            opened.setDate(QDate.currentDate())

        fee_percent = QDoubleSpinBox()
        fee_percent.setRange(0, 100)
        fee_percent.setDecimals(3)
        fee_percent.setSuffix(" % / an")
        fee_percent.setValue(
            float(Decimal(account["annual_fee_percent"])) if account else 0
        )
        fee_fixed = QDoubleSpinBox()
        fee_fixed.setRange(0, 10_000_000)
        fee_fixed.setDecimals(2)
        fee_fixed.setSuffix(" € / an")
        fee_fixed.setValue(float(Decimal(account["annual_fee_fixed"])) if account else 0)
        availability = QSpinBox()
        availability.setRange(0, 36_500)
        availability.setSuffix(" jours")
        availability.setValue(int(account["availability_days"]) if account else 0)
        details = QLineEdit()
        account_details = account["details"] if account else {}
        if isinstance(account_details, dict):
            details.setText(str(account_details.get("specific", "")))
        detail_label = QLabel("Caractéristique spécifique")

        def update_detail_label() -> None:
            labels = {
                "compte_courant": "Découvert / conditions",
                "epargne": "Taux / fiscalité / conditions",
                "investissement": "Enveloppe fiscale / stratégie",
                "credit": "Taux / échéance / assurance",
                "liquidites": "Disponibilité / localisation",
            }
            detail_label.setText(labels.get(kind.currentText(), "Caractéristique spécifique"))

        kind.currentTextChanged.connect(update_detail_label)
        update_detail_label()
        form.addRow("Nom", name)
        form.addRow("Nature", kind)
        form.addRow("Solde actuel", balance)
        form.addRow("Établissement", institution)
        form.addRow("Date d'ouverture", opened)
        form.addRow("Frais variables", fee_percent)
        form.addRow("Frais fixes", fee_fixed)
        form.addRow("Délai de disponibilité", availability)
        form.addRow(detail_label, details)
        form.addRow("Note", notes)

        scope: QComboBox | None = None
        if account is None:
            scope = QComboBox()
            scope.addItems(["Personnel", "Foyer", "Dette personnelle", "Dette foyer"])
            form.addRow("Usage", scope)

        save = QPushButton("Enregistrer")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                opened_on = opened.date().toPython()
                extra = {"specific": details.text().strip()}
                if account is None and scope is not None:
                    scope_text = scope.currentText()
                    self._finance.add_account(
                        self._user.id,
                        name.text(),
                        kind.currentText(),
                        Decimal(str(balance.value())),
                        shared="Foyer" in scope_text,
                        is_liability="Dette" in scope_text,
                        institution=institution.text(),
                        notes=notes.text(),
                        opened_on=opened_on,
                        annual_fee_percent=Decimal(str(fee_percent.value())),
                        annual_fee_fixed=Decimal(str(fee_fixed.value())),
                        availability_days=availability.value(),
                        details=extra,
                    )
                elif account is not None:
                    self._finance.update_account(
                        self._user.id,
                        int(account["id"]),
                        name=name.text(),
                        kind=kind.currentText(),
                        institution=institution.text(),
                        notes=notes.text(),
                        balance=Decimal(str(balance.value())),
                        opened_on=opened_on,
                        annual_fee_percent=Decimal(str(fee_percent.value())),
                        annual_fee_fixed=Decimal(str(fee_fixed.value())),
                        availability_days=availability.value(),
                        details=extra,
                    )
            except (ValueError, PermissionError) as exc:
                QMessageBox.warning(dialog, "Compte", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.resize(560, 520)
        return dialog

    def _show_add_account(self) -> None:
        self._account_form("Ajouter un compte ou placement").exec()

    def _show_edit_account(self, account_id: int) -> None:
        account = next(
            (
                item
                for item in self._finance.list_accounts(self._user.id)
                if int(item["id"]) == account_id
            ),
            None,
        )
        if account is None:
            QMessageBox.warning(self, "Compte", "Compte introuvable ou non accessible.")
            return
        self._account_form("Modifier le compte", account).exec()

    def _archive_account(self, account_id: int) -> None:
        response = QMessageBox.question(
            self,
            "Archiver le compte",
            "Archiver ce compte ? Son historique reste conservé.",
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        try:
            self._finance.archive_account(self._user.id, account_id)
        except PermissionError as exc:
            QMessageBox.warning(self, "Compte", str(exc))
            return
        self.refresh()

    def _show_add_history(self, account_id: int) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter un point d'historique")
        form = QFormLayout(dialog)
        captured = QDateEdit()
        captured.setCalendarPopup(True)
        captured.setDate(QDate.currentDate())
        balance = QDoubleSpinBox()
        balance.setRange(-100_000_000, 100_000_000)
        balance.setDecimals(2)
        balance.setSuffix(" €")
        account = next(
            (item for item in self._accounts_cache if int(item["id"]) == account_id),
            None,
        )
        if account:
            balance.setValue(float(Decimal(account["balance"])))
        note = QLineEdit()
        form.addRow("Date", captured)
        form.addRow("Solde à cette date", balance)
        form.addRow("Note", note)
        save = QPushButton("Ajouter le point")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                self._finance.add_account_snapshot(
                    self._user.id,
                    account_id,
                    captured.date().toPython(),
                    Decimal(str(balance.value())),
                    note.text(),
                )
            except PermissionError as exc:
                QMessageBox.warning(dialog, "Historique", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.exec()

    def _open_account_history(
        self,
        row: int = 0,
        column: int = 0,
        account_id: int | None = None,
    ) -> None:
        del column
        if account_id is None:
            item = self.accounts_table.item(row, 0)
            if item is None:
                return
            account_id = int(item.data(Qt.ItemDataRole.UserRole))
        try:
            history = self._finance.account_history(self._user.id, account_id)
        except PermissionError as exc:
            QMessageBox.warning(self, "Historique", str(exc))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Évolution du compte")
        dialog.resize(820, 620)
        layout = QVBoxLayout(dialog)
        toolbar = QHBoxLayout()
        add = QPushButton("+ Ajouter un point historique")
        add.clicked.connect(
            lambda checked=False, aid=account_id: self._show_add_history(aid)
        )
        toolbar.addWidget(add)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        chart = LineChart(
            [(str(item["date"]), Decimal(item["balance"])) for item in history]
        )
        chart.set_options(
            str(self._preferences["chart_type"]),
            bool(self._preferences["show_chart_axes"]),
            str(self._preferences["chart_color"]),
            str(self._preferences["chart_value_mode"]),
        )
        layout.addWidget(chart)
        table = QTableWidget(len(history), 4)
        table.setHorizontalHeaderLabels(["Date", "Solde", "Source", "Note"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for index, item in enumerate(history):
            values = [item["date"], money(item["balance"]), item["source"], item["note"]]
            for column_index, value in enumerate(values):
                table.setItem(index, column_index, QTableWidgetItem(str(value)))
        layout.addWidget(table)
        dialog.exec()

    def _show_add_transaction(self) -> None:
        accounts = self._finance.list_accounts(self._user.id)
        if not accounts:
            QMessageBox.information(self, "Transaction", "Ajoutez d'abord un compte.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une transaction")
        form = QFormLayout(dialog)
        account = QComboBox()
        for item in accounts:
            account.addItem(str(item["name"]), int(item["id"]))
        booked = QDateEdit()
        booked.setCalendarPopup(True)
        booked.setDate(QDate.currentDate())
        category = QComboBox()
        category.setEditable(True)
        category.addItems(
            [
                "Logement",
                "Alimentation",
                "Transport",
                "Loisirs",
                "Santé",
                "Énergie",
                "Épargne",
                "Revenus",
                "Autre",
            ]
        )
        label = QLineEdit()
        amount = QDoubleSpinBox()
        amount.setRange(-100_000_000, 100_000_000)
        amount.setDecimals(2)
        amount.setSuffix(" €")
        shared = QCheckBox("Dépense ou revenu commun au foyer")
        form.addRow("Compte", account)
        form.addRow("Date", booked)
        form.addRow("Catégorie", category)
        form.addRow("Libellé", label)
        form.addRow("Montant (+ entrée / - dépense)", amount)
        form.addRow("Portée", shared)
        save = QPushButton("Enregistrer la transaction")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                self._finance.add_transaction(
                    self._user.id,
                    int(account.currentData()),
                    booked.date().toPython(),
                    category.currentText(),
                    label.text(),
                    Decimal(str(amount.value())),
                    is_shared=shared.isChecked(),
                )
            except (ValueError, PermissionError) as exc:
                QMessageBox.warning(dialog, "Transaction", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.resize(520, 360)
        dialog.exec()

    def _delete_transaction(self, transaction_id: int) -> None:
        response = QMessageBox.question(
            self,
            "Supprimer la transaction",
            "Supprimer cette transaction ? Le solde du compte sera recalculé en conséquence.",
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        try:
            self._finance.delete_transaction(self._user.id, transaction_id)
        except PermissionError as exc:
            QMessageBox.warning(self, "Transaction", str(exc))
            return
        self.refresh()

    def _show_add_asset(self) -> None:
        accounts = self._finance.list_accounts(self._user.id)
        if not accounts:
            QMessageBox.information(self, "Placement", "Ajoutez d'abord un compte.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une position de placement")
        form = QFormLayout(dialog)
        account = QComboBox()
        for item in accounts:
            account.addItem(str(item["name"]), int(item["id"]))
        label = QLineEdit()
        kind = QComboBox()
        kind.addItems([item.value for item in AssetKind])
        value = QDoubleSpinBox()
        value.setRange(0, 100_000_000)
        value.setDecimals(2)
        value.setSuffix(" €")
        sector = QLineEdit()
        geography = QLineEdit()
        expected = QDoubleSpinBox()
        expected.setRange(-100, 100)
        expected.setDecimals(2)
        expected.setValue(5)
        expected.setSuffix(" %")
        for title, widget in [
            ("Compte", account),
            ("Libellé", label),
            ("Classe", kind),
            ("Valeur", value),
            ("Secteur", sector),
            ("Géographie", geography),
            ("Rendement annuel hypothétique", expected),
        ]:
            form.addRow(title, widget)
        save = QPushButton("Enregistrer")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                self._finance.add_asset(
                    self._user.id,
                    int(account.currentData()),
                    label.text(),
                    kind.currentText(),
                    Decimal(str(value.value())),
                    sector.text(),
                    geography.text(),
                    Decimal(str(expected.value() / 100)),
                )
            except (ValueError, PermissionError) as exc:
                QMessageBox.warning(dialog, "Placement", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.resize(500, 390)
        dialog.exec()

    def _show_budget(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer":
            QMessageBox.warning(
                self,
                "Budget",
                "Seul l'admin_foyer peut modifier le budget du foyer.",
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Poste budgétaire mensuel")
        form = QFormLayout(dialog)
        category = QComboBox()
        category.setEditable(True)
        category.addItems(
            ["Logement", "Alimentation", "Transport", "Loisirs", "Santé", "Énergie", "Autre"]
        )
        amount = QDoubleSpinBox()
        amount.setRange(0, 100_000_000)
        amount.setDecimals(2)
        amount.setSuffix(" €")
        form.addRow("Catégorie", category)
        form.addRow("Montant prévu", amount)
        save = QPushButton("Enregistrer")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                self._finance.set_budget(
                    self._user.id,
                    category.currentText(),
                    Decimal(str(amount.value())),
                )
            except (PermissionError, ValueError) as exc:
                QMessageBox.warning(dialog, "Budget", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.exec()

    def _show_household_project(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer":
            QMessageBox.warning(self, "Projet", "Seul l'admin_foyer peut créer un projet.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Créer un budget spécifique")
        form = QFormLayout(dialog)
        name = QLineEdit()
        kind = QComboBox()
        kind.setEditable(True)
        kind.addItems(["Voiture", "Vacances", "Logement", "Travaux", "Enfant", "Autre"])
        target = QDoubleSpinBox()
        target.setRange(0, 100_000_000)
        target.setDecimals(2)
        target.setSuffix(" €")
        status = QComboBox()
        status.addItems(["prévu", "actif", "en_pause", "terminé"])
        notes = QLineEdit()
        form.addRow("Nom", name)
        form.addRow("Type", kind)
        form.addRow("Montant cible", target)
        form.addRow("Statut", status)
        form.addRow("Note", notes)
        save = QPushButton("Créer le projet")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                self._finance.create_household_project(
                    self._user.id,
                    name.text(),
                    kind.currentText(),
                    Decimal(str(target.value())),
                    status.currentText(),
                    notes.text(),
                )
            except (ValueError, PermissionError) as exc:
                QMessageBox.warning(dialog, "Projet", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.exec()

    def _show_project_contribution(self) -> None:
        projects = self._finance.list_household_projects(self._user.id)
        members = self._auth.list_household_members(self._user.id)
        accounts = self._finance.list_accounts(self._user.id)
        if not projects:
            QMessageBox.information(self, "Projet", "Créez d'abord un projet du foyer.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Répartir le financement d'un projet")
        form = QFormLayout(dialog)
        project = QComboBox()
        for item in projects:
            project.addItem(str(item["name"]), int(item["id"]))
        member = QComboBox()
        for item in members:
            member.addItem(str(item["display_name"]), int(item["user_id"]))
        account = QComboBox()
        account.addItem("Aucun compte lié", None)
        for item in accounts:
            account.addItem(str(item["name"]), int(item["id"]))
        kind = QComboBox()
        kind.addItems(["cash", "mensualité", "prêt", "virement", "autre"])
        amount = QDoubleSpinBox()
        amount.setRange(0, 100_000_000)
        amount.setDecimals(2)
        amount.setSuffix(" € initial")
        monthly = QDoubleSpinBox()
        monthly.setRange(0, 10_000_000)
        monthly.setDecimals(2)
        monthly.setSuffix(" € / mois")
        duration = QSpinBox()
        duration.setRange(0, 600)
        duration.setSuffix(" mois")
        status = QComboBox()
        status.addItems(["prévu", "en_cours", "terminé"])
        for label, widget in [
            ("Projet", project),
            ("Membre", member),
            ("Compte source / prêt", account),
            ("Mode de financement", kind),
            ("Montant initial", amount),
            ("Mensualité", monthly),
            ("Durée", duration),
            ("Statut", status),
        ]:
            form.addRow(label, widget)
        save = QPushButton("Ajouter la participation")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            account_data = account.currentData()
            try:
                self._finance.add_project_contribution(
                    self._user.id,
                    int(project.currentData()),
                    int(member.currentData()),
                    kind.currentText(),
                    Decimal(str(amount.value())),
                    Decimal(str(monthly.value())),
                    duration.value(),
                    int(account_data) if account_data is not None else None,
                    status.currentText(),
                )
            except (ValueError, PermissionError) as exc:
                QMessageBox.warning(dialog, "Projet", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.resize(540, 460)
        dialog.exec()

    def _show_add_member(self) -> None:
        _, _, role, _ = self._finance.household_for_user(self._user.id)
        if role != "admin_foyer":
            QMessageBox.warning(
                self,
                "Membre",
                "Seul l'admin_foyer peut créer un membre.",
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Créer un membre du foyer")
        form = QFormLayout(dialog)
        username = QLineEdit()
        display = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        visibility = QComboBox()
        visibility.addItems(["Accès au foyer", "Profil personnel uniquement"])
        form.addRow("Utilisateur", username)
        form.addRow("Nom affiché", display)
        form.addRow("Mot de passe", password)
        form.addRow("Visibilité", visibility)
        save = QPushButton("Créer le membre")
        save.setObjectName("Primary")
        form.addRow(save)

        def submit() -> None:
            try:
                self._auth.create_household_member(
                    self._user.id,
                    username.text(),
                    password.text(),
                    display.text(),
                    can_view_household=visibility.currentIndex() == 0,
                )
            except (PermissionError, ValueError) as exc:
                QMessageBox.warning(dialog, "Membre", str(exc))
                return
            dialog.accept()
            self.refresh()

        save.clicked.connect(submit)
        dialog.exec()

    def _rename_household(self) -> None:
        try:
            self._auth.rename_household(self._user.id, self.household_name.text())
        except (ValueError, PermissionError) as exc:
            QMessageBox.warning(self, "Foyer", str(exc))
            return
        self.refresh()
