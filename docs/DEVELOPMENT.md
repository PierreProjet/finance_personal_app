# Guide de développement

## Branches

- `main` : version stable.
- `develop` : intégration.
- `feature/*` : une fonctionnalité cohérente.
- `fix/*` : correction ciblée.

## Commits

Utiliser Conventional Commits : `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `security:`, `build:`.

Exemples :

- `feat(ui): add collapsible settings drawer`
- `feat(accounts): persist balance history`
- `fix(database): migrate legacy account columns`
- `test(accounts): cover update and deletion permissions`

## Qualité

Avant une Pull Request :

```text
ruff check src tests
pytest --cov=finance_app
```

Les fonctions doivent rester courtes, avoir un nom explicite et ne pas mélanger logique métier, accès aux données et présentation.

## Données

Aucune donnée financière réelle, base SQLite, clé de chiffrement ou secret ne doit être commité. Les données utilisateur sont locales au poste.
