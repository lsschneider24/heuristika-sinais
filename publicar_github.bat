@echo off
chcp 65001 >nul
echo ===================================================
echo   Heuristika - Sincronizar Backend + GitHub Pages 24/7
echo ===================================================

echo [1/3] Salvando codigo-fonte no repositorio PRIVADO (heuristika-sinais)...
git add -A
git diff --cached --quiet
if %errorlevel% neq 0 (
    git commit -m "Atualizacao Heuristika Terminal, Academia & GitHub Pages 24/7"
)
git push -u origin main

echo.
echo [2/3] Gerando pacote estatico atualizado para o GitHub Pages (site_dist)...
set "PYTHONPATH=%CD%;%CD%\.venv\Lib\site-packages"
python build_github_pages.py

echo.
echo [3/3] Publicando portal estatico 24/7 em https://lsschneider24.github.io/heuristika/ ...
git -C site_dist init -b main >nul 2>nul
git -C site_dist config user.name "Heuristika Quant"
git -C site_dist config user.email "contato@heuristika.com.br"
git -C site_dist remote remove origin >nul 2>nul
git -C site_dist remote add origin https://github.com/lsschneider24/heuristika.git
git -C site_dist add -A
git -C site_dist commit -m "Deploy Heuristika Portal & Academia 24/7" >nul 2>nul
git -C site_dist push -f -u origin main

echo.
echo ===================================================
echo   [SUCESSO] PUBLICACAO 24/7 CONCLUIDA!
echo   Vitrine 24/7:   https://lsschneider24.github.io/heuristika/
echo   Academia 24/7:  https://lsschneider24.github.io/heuristika/academia/
echo   Carteiras 24/7: https://lsschneider24.github.io/heuristika/carteiras/
echo   Repo Privado:   https://github.com/lsschneider24/heuristika-sinais
echo ===================================================
pause
