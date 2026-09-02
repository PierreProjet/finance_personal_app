# Connexion à GitHub

Le dossier est déjà initialisable comme dépôt Git.

```powershell
git init
git add .
git commit -m "feat: initial Finance Foyer MVP"
git branch -M main
git remote add origin https://github.com/VOTRE-COMPTE/VOTRE-DEPOT.git
git push -u origin main
```

Deux workflows sont fournis :

- `.github/workflows/ci.yml` : lint + tests à chaque push / pull request;
- `.github/workflows/build-windows.yml` : build Windows manuel ou lors d'un tag `v*`, puis publication de l'exécutable comme artifact GitHub Actions.

Pour une release :

```powershell
git tag v0.1.0
git push origin v0.1.0
```
