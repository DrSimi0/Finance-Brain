# Instalación de Finance Brain en Windows (PowerShell), sin WSL ni Docker.
# Uso, desde la carpeta del repo:
#   powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1 -ConAgentes
param([switch]$ConAgentes)
$ErrorActionPreference = "Stop"

Write-Host "1/5 Comprobando Python 3.12..." -ForegroundColor Cyan
try { py -3.12 --version } catch {
    Write-Host "No encuentro Python 3.12. Instálalo con:  winget install Python.Python.3.12" -ForegroundColor Red
    exit 1
}

Write-Host "2/5 Creando entorno virtual .venv..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip

Write-Host "3/5 Instalando dependencias (alpaca-py, vectorbt, ...)..." -ForegroundColor Cyan
& $py -m pip install -e ".[dev]"
if ($ConAgentes) {
    Write-Host "     + capa de agentes (TradingAgents v0.7.1, requiere Git)..." -ForegroundColor Cyan
    & $py -m pip install -e ".[agentes]"
}

Write-Host "4/5 Preparando .env..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "     Creado .env: ábrelo con 'notepad .env' y pon tus claves de Alpaca (paper)." -ForegroundColor Yellow
} else { Write-Host "     .env ya existe; no se toca." }

Write-Host "5/5 Verificando con los tests y la demo..." -ForegroundColor Cyan
& $py -m pytest
& .\.venv\Scripts\finance-brain.exe demo

Write-Host "`nListo. Activa el entorno en cada terminal nueva con:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
