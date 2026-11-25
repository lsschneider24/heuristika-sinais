# Setup em Novo PC (Portabilidade no Google Drive)

Este guia prepara um segundo PC Windows para trabalhar alternadamente no mesmo projeto do Google Drive (um PC por vez).

## 1. Pré-requisitos no Novo PC
1. Instale o **Google Drive para Desktop** e aguarde a sincronização completa.
2. Marque a pasta do projeto como **"Disponível offline"** (clique direito → *Acesso offline* → *Disponível offline*).
3. Instale o **Python 3.12** (marque *Add Python to PATH*) e o **Git**.

## 2. Preparação Automática (`setup_pc.ps1`)
Abra o PowerShell na pasta do projeto dentro do Google Drive e execute:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_pc.ps1
```
O script irá:
- Criar o ambiente virtual **fora do Drive** em `%LOCALAPPDATA%\Heuristika\venv-sinais`.
- Instalar as dependências travadas de `requirements.txt`.
- Copiar `.env.example` para `%LOCALAPPDATA%\Heuristika\.env` (se ainda não existir) — **preencha seus segredos à mão** nesse arquivo.
- Configurar `PYTHONDONTWRITEBYTECODE=1` e `PYTHONPYCACHEPREFIX=%LOCALAPPDATA%\Heuristika\pycache`.
- Executar `audit\run_audit.py` para validar todos os testes e a integridade do Git.

## 3. Como Subir o Servidor e Rodar a Auditoria
- **Subir o servidor Flask:**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\run.ps1
  ```
- **Rodar a auditoria completa:**
  ```powershell
  $env:PYTHONDONTWRITEBYTECODE="1"
  & "$env:LOCALAPPDATA\Heuristika\venv-sinais\Scripts\python.exe" audit\run_audit.py
  ```

## 4. Backup e Restauração (Git Bundle + Banco SQLite)
- **Gerar backup portátil** (`backups_repo/` e `backups_db/`):
  ```powershell
  & "$env:LOCALAPPDATA\Heuristika\venv-sinais\Scripts\python.exe" audit\tools\backup_drive_state.py
  ```
- **Restaurar repositório a partir de um `.bundle`:**
  ```powershell
  git clone backups_repo\sinais_repo_AAAA-MM-DD_HHMM.bundle pasta_restaurada
  ```
- **Restaurar estado do banco SQLite em outro PC:**
  Feche o servidor e copie o arquivo `backups_db\sinais_vip_backup_AAAA-MM-DD_HHMMSS.db` para `%LOCALAPPDATA%\Heuristika\sinais_vip.db`.
