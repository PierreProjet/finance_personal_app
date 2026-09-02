$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name finance --paths src src\finance_app\main.py
Write-Host "Executable créé dans dist\finance\finance.exe"
