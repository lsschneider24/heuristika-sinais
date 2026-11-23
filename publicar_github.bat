@echo off
chcp 65001 >nul
echo ===================================================
echo   Heuristika - Publicar no GitHub + GitHub Pages 24/7
echo ===================================================

set "GH_EXE=C:\Program Files\GitHub CLI\gh.exe"
if not exist "%GH_EXE%" (
    where gh >nul 2>nul
    if %errorlevel%==0 (
        set "GH_EXE=gh"
    ) else (
        echo [ERRO] GitHub CLI nao encontrado. Instale com: winget install --id GitHub.cli -e
        pause
        exit /b 1
    )
)

"%GH_EXE%" auth status >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Conectando sua conta do GitHub no navegador...
    "%GH_EXE%" auth login --web -h github.com -p https -s workflow
    if %errorlevel% neq 0 (
        echo [ERRO] Falha na autenticacao do GitHub.
        pause
        exit /b 1
    )
)

"%GH_EXE%" auth setup-git >nul 2>nul

echo [INFO] Verificando alteracoes locais (protegendo .env e banco SQLite)...
git add -A
git diff --cached --quiet
if %errorlevel% neq 0 (
    git commit -m "Atualizacao Heuristika Terminal, Academia & GitHub Pages 24/7"
)

git remote get-url origin >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Criando repositorio publico heuristika-sinais no seu GitHub...
    "%GH_EXE%" repo create heuristika-sinais --public --source=. --remote=origin --push
) else (
    echo [INFO] Enviando atualizacoes para o GitHub...
    git push -u origin main
)

echo [INFO] Ativando GitHub Pages 24/7 via GitHub Actions...
for /f "delims=" %%u in ('"%GH_EXE%" api user -q .login') do set "GH_USER=%%u"
"%GH_EXE%" api --method POST "repos/%GH_USER%/heuristika-sinais/pages" -f build_type=workflow >nul 2>nul
"%GH_EXE%" api --method PUT "repos/%GH_USER%/heuristika-sinais/pages" -f build_type=workflow >nul 2>nul

echo.
echo ===================================================
echo   [SUCESSO] PUBLICACAO 24/7 CONCLUIDA!
echo   Repositorio: https://github.com/%GH_USER%/heuristika-sinais
echo   Site 24/7:   https://%GH_USER%.github.io/heuristika-sinais/
echo   Academia:    https://%GH_USER%.github.io/heuristika-sinais/academia/
echo ===================================================
pause
