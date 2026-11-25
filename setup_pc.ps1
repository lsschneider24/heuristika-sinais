<#
.SYNOPSIS
Prepara o ambiente local fora do Google Drive para este PC (venv, .env, testes e auditoria).
#>
param(
    [switch]$SkipAudit
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HeuristikaDir = Join-Path $env:LOCALAPPDATA "Heuristika"
$VenvDir = Join-Path $HeuristikaDir "venv-sinais"
$EnvFile = Join-Path $HeuristikaDir ".env"
$LockFile = Join-Path $ProjectDir "WORKING_PC.lock"

$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPYCACHEPREFIX = Join-Path $HeuristikaDir "pycache"

if (Test-Path $LockFile) {
    Write-Warning "WORKING_PC.lock encontrado: $((Get-Content $LockFile -Raw).Trim())"
}

# Localiza Python 3.12
$PythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        $ver = & py -3.12 --version 2>$null
        if ($LASTEXITCODE -eq 0) { $PythonCmd = @("py", "-3.12") }
    } catch {}
}
if (-not $PythonCmd -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $ver = & python --version 2>&1
    if ($ver -match "3\.12") { $PythonCmd = @("python") }
}
if (-not $PythonCmd) {
    throw "Python 3.12 nao encontrado no PATH. Instale Python 3.12 antes de continuar."
}

New-Item -ItemType Directory -Force -Path $HeuristikaDir | Out-Null

if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    Write-Host "Criando venv externo em $VenvDir..."
    if ($PythonCmd.Count -eq 2) {
        & $PythonCmd[0] $PythonCmd[1] -m venv $VenvDir
    } else {
        & $PythonCmd[0] -m venv $VenvDir
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

Write-Host "Instalando dependencias de requirements.txt..."
& $VenvPip install --quiet -r (Join-Path $ProjectDir "requirements.txt")

if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $ProjectDir ".env.example") $EnvFile
    Write-Warning "Arquivo .env criado em $EnvFile a partir de .env.example. PREENCHA SEUS SEGREDOS A MAO antes de publicar sinais!"
} else {
    Write-Host ".env externo ja existe em $EnvFile"
}

if (-not $SkipAudit) {
    Write-Host "Executando auditoria e suite completa..."
    & $VenvPython (Join-Path $ProjectDir "audit\run_audit.py")
    if ($LASTEXITCODE -ne 0) {
        throw "audit\run_audit.py falhou com exit_code=$LASTEXITCODE"
    }
}

Write-Host "Setup concluido com sucesso! Venv: $VenvDir"
