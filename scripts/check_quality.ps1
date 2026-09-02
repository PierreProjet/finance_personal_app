$ErrorActionPreference = "Stop"
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\pytest.exe --cov=finance_app --cov-report=term-missing
