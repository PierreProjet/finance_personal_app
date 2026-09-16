# Décisions produit — V2

## Données bancaires

Le domaine expose une interface `BankingConnector`, mais aucun connecteur bancaire distant n'est activé dans la V2. Le MVP reste local et manuel/import CSV. Cette décision évite de créer une dépendance commerciale ou de transmettre des données financières avant validation explicite.

## Données de marché

L'application utilise d'abord des sources gratuites lorsqu'elles sont disponibles. L'interface `MarketDataProvider` isole les fournisseurs afin de pouvoir changer de source sans modifier le domaine.

## Chiffrement

Le stockage actuel chiffre les champs sensibles et protège la clé au niveau du coffre-fort système. L'architecture réserve une étape ultérieure au chiffrement intégral de la base. Cette étape nécessitera une migration et une procédure de récupération de clé documentées avant activation.

## Sauvegardes et synchronisation

La V2 privilégie des sauvegardes manuelles chiffrées. Une future synchronisation cloud sera ajoutée derrière un service distinct, avec résolution de conflits et chiffrement de bout en bout étudiés séparément.

## Niveau de qualité

Le projet progresse vers un niveau quasi professionnel par incréments : architecture modulaire, tests, analyse statique, CI, audit, migrations, sauvegardes et packaging Windows.
