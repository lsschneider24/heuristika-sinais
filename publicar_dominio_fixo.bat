@echo off
chcp 65001 >nul
echo ===================================================
echo   Heuristika - Servidor + Dominio Fixo Cloudflare
echo ===================================================

if not exist "bin\cloudflared.exe" (
    echo [ERRO] bin\cloudflared.exe nao encontrado.
    pause
    exit /b 1
)

if not exist "cloudflared-config.yml" (
    echo [INFO] Configuracao de dominio fixo ainda nao criada.
    echo Siga os 3 passos abaixo uma unica vez:
    echo   1. bin\cloudflared.exe tunnel login
    echo   2. bin\cloudflared.exe tunnel create heuristika
    echo   3. bin\cloudflared.exe tunnel route dns heuristika sinais.seudominio.com.br
    echo   4. Copie cloudflared-config.example.yml para cloudflared-config.yml e preencha o ID.
    pause
    exit /b 1
)

echo [INFO] Iniciando servidor Flask em http://127.0.0.1:5050 ...
start "Heuristika Server" cmd /c "call .venv\Scripts\activate.bat && python app.py"

timeout /t 3 >nul

echo [INFO] Conectando tunel com dominio fixo...
bin\cloudflared.exe tunnel --config cloudflared-config.yml run heuristika
pause
