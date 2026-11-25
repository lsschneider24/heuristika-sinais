# Teste Rápido (Camada 1): roda apenas os testes dos módulos afetados (ou padrão)
param(
    [string[]]$Modules = @("tests.test_calendar_and_variants", "tests.test_strategy_agent_and_ui")
)
$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
$py = Join-Path $env:LOCALAPPDATA "Heuristika\venv-sinais\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Venv externo nao encontrado em $py. Rode setup_pc.ps1." }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $py -m unittest @Modules -v
$code = $LASTEXITCODE
$sw.Stop()
Write-Host ("TEST_RAPIDO_SEC={0:N2} EXIT={1}" -f $sw.Elapsed.TotalSeconds, $code)
exit $code
