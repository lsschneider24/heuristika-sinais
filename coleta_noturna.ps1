# Coleta Noturna Agendada (PC Principal - Custo Zero)
# Uso no Agendador de Tarefas do Windows:
#   Programa: powershell.exe
#   Argumentos: -ExecutionPolicy Bypass -File "coleta_noturna.ps1"
#   Iniciar em: pasta do projeto no Google Drive
$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
$py = Join-Path $env:LOCALAPPDATA "Heuristika\venv-sinais\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Venv externo nao encontrado em $py." }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $py -c "import data_collector, market_data; data_collector.collect_b3_fundamentals(enable_crosscheck=True, use_cache=True); market_data.fetch_bcb_cdi_series(allow_cache=False); print('COLETA_NOTURNA_OK=1')"
$code = $LASTEXITCODE
$sw.Stop()
Write-Host ("COLETA_NOTURNA_SEC={0:N2} EXIT={1}" -f $sw.Elapsed.TotalSeconds, $code)
exit $code
