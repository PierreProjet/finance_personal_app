# Sécurité et confidentialité

## Menaces couvertes par le MVP
- vol du fichier SQLite seul : les libellés sensibles sont chiffrés;
- fuite de mots de passe : Argon2id rend les attaques hors-ligne coûteuses;
- accès d'un membre à des données foyer non autorisées : filtrage par permission dans les services;
- corruption relationnelle : clés étrangères SQLite activées.

## Limites connues
Les montants restent numériques dans SQLite pour permettre des requêtes et agrégations fiables. Le chiffrement intégral de la base n'est donc pas garanti dans ce MVP. Pour une exigence de chiffrement total au repos, utiliser SQLCipher ou un volume utilisateur chiffré (BitLocker) en complément.

Le fallback `.master.key` n'offre pas la même protection que le gestionnaire de secrets de l'OS. Sous Windows, `keyring` utilise normalement le gestionnaire d'identifiants disponible.

## Règles de développement
- jamais de secret dans Git;
- aucune journalisation des mots de passe ou clés;
- validation des entrées dans les services;
- dépendances épinglées par plages majeures et analysées avant release;
- tests automatiques avant build;
- revue des changements touchant `security/`, `services/` et le schéma de données.
