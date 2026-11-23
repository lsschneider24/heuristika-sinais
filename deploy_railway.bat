@echo off
chcp 65001 >nul
echo ===================================================
echo   Heuristika - Deploy 24/7 para Railway
echo ===================================================

where railway >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Instalando Railway CLI...
    call npm install -g @railway/cli
)

railway whoami >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Abrindo login do Railway no navegador...
    call railway login
)

echo [INFO] Vinculando ao projeto heuristika-sinais...
call railway link -p 58faf7f1-2d29-47b6-a41f-82665d0d5063 -s f562ea83-54e3-4920-9086-9fedeb1e5116 -e production

echo [INFO] Enviando codigo para producao...
call railway up --detach

echo [SUCESSO] Deploy iniciado! Acesse: https://heuristika-web-production.up.railway.app
pause
