# Modèle de sécurité V2

## Principes

1. Les mots de passe sont stockés sous forme de hash Argon2id ; ils ne sont jamais réversibles.
2. Les champs sensibles sont chiffrés côté application.
3. La clé de chiffrement doit être protégée par le coffre-fort du système d'exploitation et ne doit jamais être commitée.
4. Les données financières réelles et les bases locales sont exclues du dépôt Git.
5. Les imports bancaires sont conçus derrière une interface afin de limiter le périmètre d'une future intégration réseau.
6. Les sauvegardes sont chiffrées avant export.
7. La synchronisation cloud reste désactivée par défaut.

## Évolution vers le chiffrement intégral

La base SQLite actuelle reste compatible avec une migration future vers un moteur ou une couche de chiffrement intégral. Cette migration sera traitée comme une release dédiée : sauvegarde préalable, migration transactionnelle, test de restauration et procédure de récupération de clé.

## Menaces couvertes

- lecture accidentelle de fichiers de configuration sensibles ;
- compromission d'un dépôt Git par inclusion de secrets ;
- perte d'une copie de sauvegarde non chiffrée ;
- accès d'un membre du foyer à des données qui ne lui sont pas destinées.

## Menaces non encore couvertes complètement

- machine Windows compromise au niveau administrateur ;
- exfiltration pendant une future synchronisation réseau ;
- chiffrement intégral des colonnes numériques de la base ;
- authentification multifacteur.

Ces limites sont volontairement explicites pour éviter de présenter le MVP comme une solution bancaire certifiée.
