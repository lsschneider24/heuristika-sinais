# Estratégia de Portabilidade (2 PCs no Google Drive)

> **Decisão do usuário:** o projeto permanece no Google Drive para trabalho alternado entre dois PCs (um de cada vez).

- Consulte o guia completo em `SETUP_NOVO_PC.md` e os scripts `setup_pc.ps1` e `run.ps1` na raiz do projeto.
- `.venv`, banco SQLite (`sinais_vip.db`) e `.env` ficam fora do Drive em `%LOCALAPPDATA%\Heuristika\`.
- `__pycache__` é redirecionado para `%LOCALAPPDATA%\Heuristika\pycache` (`PYTHONDONTWRITEBYTECODE=1`).
