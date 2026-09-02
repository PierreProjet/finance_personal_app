# Architecture

## Objectif
Finance Foyer est une application **desktop locale-first**. Le domaine financier, la sécurité, la persistance et l'interface sont séparés afin de garder le code testable et de permettre une évolution vers de nouveaux connecteurs bancaires ou moteurs d'analyse sans réécrire l'UI.

## Couches

- `ui/` : fenêtres PySide6 et thème utilisateur.
- `services/` : cas d'usage et règles d'autorisation.
- `models/` : modèle SQLAlchemy.
- `security/` : hachage des mots de passe et chiffrement applicatif.
- `analytics/` : calculs de patrimoine, allocation, concentration et projection.
- `db.py` : cycle de vie SQLite / SQLAlchemy.
- `config.py` : chemins et configuration locale.

## Modèle principal

- `User` : compte de connexion et préférence de couleur.
- `Household` : foyer.
- `HouseholdMember` : rôle (`admin_foyer` / `membre`) + permission de visibilité.
- `FinancialAccount` : compte personnel ou partagé, actif ou dette.
- `AssetPosition` : position patrimoniale avec type, secteur, géographie, rendement attendu.
- `Transaction` : flux catégorisé.
- `MonthlyBudget` : enveloppe mensuelle du foyer.
- `NetWorthSnapshot` : point d'historique de patrimoine (prévu pour automatisation v0.2).

## Sécurité

- Mot de passe : Argon2id via `argon2-cffi`; aucun mot de passe n'est stocké en clair.
- Champs textuels sensibles : Fernet (`cryptography`).
- Clé maître : Windows Credential Manager via `keyring` lorsque disponible; fichier local restreint en repli.
- SQLite : clés étrangères activées.
- Permissions : contrôlées dans la couche service, pas dans l'UI uniquement.

> Pour une version distribuée commercialement, prévoir une revue de sécurité, une stratégie de sauvegarde chiffrée, un verrouillage après inactivité et éventuellement SQLCipher/Windows DPAPI natif pour un chiffrement intégral au repos.

## Projection financière
La v0.1 utilise une projection composée déterministe fondée sur le rendement annuel attendu saisi pour chaque position et pondéré par sa valeur. Elle est volontairement explicable. Elle ne constitue pas un conseil d'investissement. Une version suivante doit proposer plusieurs scénarios, inflation, fiscalité, volatilité et Monte-Carlo.
