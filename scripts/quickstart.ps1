param(
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Test-Python312OrNewer {
    param([string]$PythonPath)

    if (-not (Test-Path $PythonPath)) {
        return $false
    }

    try {
        $versionText = (& $PythonPath --version 2>&1 | Out-String).Trim()
        if ($versionText -match '^Python\s+(\d+)\.(\d+)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            return ($major -gt 3) -or ($major -eq 3 -and $minor -ge 12)
        }
    }
    catch {
        return $false
    }

    return $false
}

function New-ProjectVenv {
    $created = $false

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher) {
        try {
            & py -3.12 --version *> $null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[setup] Creation de .venv avec Python 3.12..."
                & py -3.12 -m venv .venv
                $created = $true
            }
        }
        catch {
            $created = $false
        }
    }

    if (-not $created) {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($null -ne $pythonCommand) {
            $candidate = $pythonCommand.Source
            try {
                $versionText = (& $candidate --version 2>&1 | Out-String).Trim()
                if ($versionText -match '^Python\s+(\d+)\.(\d+)') {
                    $major = [int]$Matches[1]
                    $minor = [int]$Matches[2]
                    if (($major -gt 3) -or ($major -eq 3 -and $minor -ge 12)) {
                        Write-Host "[setup] Creation de .venv avec $versionText..."
                        & $candidate -m venv .venv
                        $created = $true
                    }
                }
            }
            catch {
                $created = $false
            }
        }
    }

    if (-not $created) {
        throw @"
Python 3.12 ou plus recent est requis.
Installez Python 3.12 puis rouvrez le terminal VS Code :
  winget install --id Python.Python.3.12 -e --source winget
"@
    }
}

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ((Test-Path $VenvPython) -and -not (Test-Python312OrNewer $VenvPython)) {
    Write-Host "[setup] L'environnement .venv existant n'utilise pas Python 3.12+. Reinitialisation..."
    Remove-Item -Recurse -Force (Join-Path $RepoRoot ".venv")
}

if (-not (Test-Path $VenvPython)) {
    New-ProjectVenv
}

if (-not (Test-Python312OrNewer $VenvPython)) {
    throw "Impossible de preparer un environnement Python 3.12+ valide dans .venv."
}

$PythonVersion = (& $VenvPython --version 2>&1 | Out-String).Trim()
Write-Host "[setup] $PythonVersion"
Write-Host "[setup] Mise a jour de pip..."
& $VenvPython -m pip install --upgrade pip

Write-Host "[setup] Installation de l'application et des outils de developpement..."
& $VenvPython -m pip install -e ".[dev]"

Write-Host "[test 1/2] Ruff..."
& $VenvPython -m ruff check src tests
if ($LASTEXITCODE -ne 0) {
    throw "Ruff a detecte des erreurs. L'application n'est pas lancee."
}

Write-Host "[test 2/2] Pytest + couverture..."
& $VenvPython -m pytest --cov=finance_app
if ($LASTEXITCODE -ne 0) {
    throw "Pytest a echoue. L'application n'est pas lancee."
}

Write-Host "[ok] La chaine locale equivalente a la CI est verte."

if ($NoLaunch) {
    Write-Host "[ok] -NoLaunch specifie : fin apres les tests."
    exit 0
}

Write-Host "[run] Demarrage de Finance Foyer..."
& $VenvPython -m finance_app.main
