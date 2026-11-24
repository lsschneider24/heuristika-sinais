# Proposta de Migração para Pasta Local Fora do Google Drive

> **Status:** Proposta documentada — **NÃO executada** (aguardando confirmação explícita do usuário).

## Motivação
1. O diretório atual (`J:\Meu Drive\Antigravity Projetos\Sinais Financeiros`) está montado no Google Drive, o que causa bloqueios de acesso no sandbox padrão e risco de conflitos de sincronização em arquivos `.git` e caches.
2. O `.venv` atual aponta para `C:\Users\Itacel\AppData\Local\Programs\Python\Python312\python.exe`, inexistente nesta máquina (`Pichau`).

## Procedimento Proposto (após confirmação)
1. **Copiar repositório com histórico Git para pasta local fora do Drive** (ex.: `C:\Projetos\Sinais-Financeiros`):
   ```powershell
   robocopy "J:\Meu Drive\Antigravity Projetos\Sinais Financeiros" "C:\Projetos\Sinais-Financeiros" /E /XD .venv __pycache__ data\collector_cache
   ```
2. **Recriar `.venv` com o Python local (`C:\Users\Pichau\AppData\Local\Programs\Python\Python312\python.exe`)**:
   ```powershell
   cd C:\Projetos\Sinais-Financeiros
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\pip.exe install -r requirements.txt
   ```
3. **Validar banco SQLite e `.env` locais** (já residem fora do Drive em `C:\Users\Pichau\AppData\Local\Heuristika\`).
4. **Executar validação completa** no novo diretório:
   ```powershell
   .\.venv\Scripts\python.exe audit\run_audit.py
   ```
5. **Arquivar/congelar** a pasta do Google Drive como somente-leitura ou removê-la após confirmar `EXIT 0` na pasta local.
