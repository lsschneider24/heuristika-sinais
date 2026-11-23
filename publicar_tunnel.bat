@echo off
chcp 65001 >nul
echo ===================================================
echo   Heuristika - Servidor + Cloudflare Tunnel (Gratis)
echo ===================================================

if not exist "bin\cloudflared.exe" (
    echo [ERRO] bin\cloudflared.exe nao encontrado.
    pause
    exit /b 1
)

echo [INFO] Iniciando servidor Flask em http://127.0.0.1:5050 ...
start "Heuristika Server" cmd /c "call .venv\Scripts\activate.bat && python app.py"

timeout /t 3 >nul

echo [INFO] Abrindo tunel HTTPS gratuito na Cloudflare...
echo [DICA] Copie a URL https://....trycloudflare.com que aparecer abaixo!
bin\cloudflared.exe tunnel --url http://127.0.0.1:5050
pause
