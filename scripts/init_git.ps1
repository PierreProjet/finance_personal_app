$ErrorActionPreference = "Stop"
if (-not (Test-Path ".git")) { git init }
git add .
git status
Write-Host "Puis: git commit -m 'feat: initial Finance Foyer MVP'"
Write-Host "Et ajoutez votre remote GitHub selon docs/GITHUB.md"
