@echo off
chcp 65001 >nul
echo ===================================================
echo   SinaisVIP Terminal - Inicializacao (Windows)
echo ===================================================

set PYTHON_CMD=
where python >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PYTHON_CMD=py -3
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERRO] Python 3 nao encontrado no PATH.
    echo Instale o Python 3.10+ em https://www.python.org/downloads/ e marque "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".env" (
    echo [INFO] Criando .env a partir de .env.example...
    copy ".env.example" ".env" >nul
)

if not exist ".venv" (
    echo [INFO] Criando ambiente virtual .venv...
    %PYTHON_CMD% -m venv .venv
)

".venv\Scripts\python.exe" -V >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Ambiente .venv pertence a outro computador. Usando Python local com pacotes de .venv...
    set "PYTHONPATH=%CD%;%CD%\.venv\Lib\site-packages"
    echo [INFO] Inicializando banco SQLite e sinais iniciais...
    %PYTHON_CMD% seed.py
    echo [INFO] Iniciando servidor Flask em http://127.0.0.1:5050 ...
    %PYTHON_CMD% app.py
    pause
    exit /b 0
)

call ".venv\Scripts\activate.bat"

echo [INFO] Instalando dependencias...
pip install -r requirements.txt

echo [INFO] Inicializando banco SQLite e sinais iniciais...
python seed.py

echo [INFO] Iniciando servidor Flask em http://127.0.0.1:5050 ...
python app.py
pause
