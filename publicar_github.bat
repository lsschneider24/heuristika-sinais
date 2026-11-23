@echo off
chcp 65001 >nul
echo ===================================================
echo   Heuristika - Sincronizar GitHub + Pages 24/7
echo ===================================================

git status --short
echo.
echo [INFO] Adicionando alteracoes (protegendo .env e banco local)...
git add -A

git diff --cached --quiet
if %errorlevel%==0 (
    echo [INFO] Nenhuma alteracao pendente para commit.
) else (
    git commit -m "Atualizacao automatica Heuristika Terminal & Academia"
)

echo [INFO] Enviando para o GitHub (aciona deploy automatico 24/7 no GitHub Pages)...
git push -u origin main

echo.
echo [SUCESSO] Codigo sincronizado com o GitHub!
pause
