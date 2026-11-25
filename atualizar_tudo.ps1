<#
.SYNOPSIS
Botao unico em linha de comando: coleta, estrategias, radar, relatorio e auditoria.
#>
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $env:LOCALAPPDATA "Heuristika\venv-sinais\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Venv externo nao encontrado em $VenvPython. Execute .\setup_pc.ps1 primeiro."
}

$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPYCACHEPREFIX = Join-Path $env:LOCALAPPDATA "Heuristika\pycache"

Write-Host "1/4 Coletando dados (Yahoo + CVM LTM + detectores evento_corporativo)..."
& $VenvPython (Join-Path $ProjectDir "data_collector.py")

Write-Host "2/4 Executando estrategias, Radar Global e relatorio semanal..."
& $VenvPython -c "import sys; sys.path.insert(0, r'$ProjectDir'); import strategies_engine, strategy_agent, market_data; market_data.fetch_bcb_cdi_series(); ag=strategy_agent.StrategyAgent(); [strategies_engine.run_strategy(s['id'], persist=True) for s in ag.list_strategies() if s.get('enabled')]; rep=ag.generate_report('semanal'); print(rep['markdown'])"

Write-Host "3/4 Gerando backup portatil (git bundle + banco SQLite)..."
& $VenvPython (Join-Path $ProjectDir "audit\tools\backup_drive_state.py")

Write-Host "4/4 Executando auditoria completa..."
& $VenvPython (Join-Path $ProjectDir "audit\run_audit.py")
if ($LASTEXITCODE -ne 0) {
    throw "Auditoria falhou com exit_code=$LASTEXITCODE"
}
Write-Host "Laboratorio atualizado com sucesso!"
