<#
.SYNOPSIS
Sobe o servidor Flask usando o venv externo em %LOCALAPPDATA%\Heuristika\venv-sinais e gerencia WORKING_PC.lock.
#>
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HeuristikaDir = Join-Path $env:LOCALAPPDATA "Heuristika"
$VenvPython = Join-Path $HeuristikaDir "venv-sinais\Scripts\python.exe"
$LockFile = Join-Path $ProjectDir "WORKING_PC.lock"

if (-not (Test-Path $VenvPython)) {
    throw "Venv externo nao encontrado em $VenvPython. Execute .\setup_pc.ps1 primeiro."
}

$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPYCACHEPREFIX = Join-Path $HeuristikaDir "pycache"

if (Test-Path $LockFile) {
    try {
        $lockObj = Get-Content $LockFile -Raw | ConvertFrom-Json
        $lockTime = [datetime]::Parse($lockObj.started_at)
        $ageHours = ((Get-Date) - $lockTime).TotalHours
        if ($lockObj.pc_name -ne $env:COMPUTERNAME -and $ageHours -lt 12) {
            Write-Warning "ATENCAO: outro PC ($($lockObj.pc_name)) abriu sessao ha $([math]::Round($ageHours, 1))h ($($lockObj.started_at)). Confirme que o Drive esta sincronizado!"
        }
    } catch {
        Write-Warning "WORKING_PC.lock encontrado: $((Get-Content $LockFile -Raw).Trim())"
    }
}

$lockPayload = @{
    pc_name = $env:COMPUTERNAME
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json
Set-Content -Path $LockFile -Value $lockPayload -Encoding UTF8

try {
    Push-Location $ProjectDir
    & $VenvPython "app.py"
} finally {
    Pop-Location
    if (Test-Path $LockFile) {
        Remove-Item -Force -ErrorAction SilentlyContinue $LockFile
    }
}
