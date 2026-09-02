# Système d'agents

Ce dossier formalise une organisation multi-agent où chaque agent reçoit une tâche unique, bornée et vérifiable.

Ordre recommandé :

1. `manager.md` découpe la demande et attribue les tâches;
2. `planner.md` transforme une tâche en plan/critères d'acceptation;
3. `coder.md` implémente uniquement la tâche attribuée;
4. `quality.md` vérifie tests, sécurité, lisibilité et régressions;
5. `documentation.md` met à jour README, architecture et changelog.

Aucun agent ne doit modifier une zone hors de sa mission sans instruction explicite du manager.
