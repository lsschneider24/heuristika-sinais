# Regras Permanentes do Projeto (`PROJECT_RULES.md`)

## 1. Modo Autônomo e Política de Decisão
- **Autonomia:** Executar ponta a ponta sem perguntas desnecessárias; se faltar informação, escolher o padrão mais seguro e registrar no `HANDOFF.md`.
- **Conflito de dados:** O valor do coletor oficial/público prevalece sobre snapshot antigo; divergência além da tolerância (`±5%` rel ou `±0,3 pp`) -> `verified=false` com causa registrada; dado ausente -> `"indisponível"` (`null`), nunca `0.0` ou estimativa.
- **Escalar ao usuário apenas por:**
  1. Mudança de **REGRA** de estratégia (parâmetros técnicos são permitidos e registrados em `strategy_param_versions`);
  2. Fonte de dados nova que exija cadastro ou custo;
  3. Conflito sem solução pela política acima;
  4. Ação irreversível.

## 2. Limites e Governança
- **Backup:** Sempre criar backup datado (`audit/tools/backup_drive_state.py` + ZIP fora do Drive) antes de editar.
- **Git:** Nunca fazer `git push` nem criar repositório remoto sem autorização.
- **Custo zero:** Apenas fontes públicas gratuitas (Yahoo Finance, BCB SGS, CVM Dados Abertos, Fundamentus com pausa e cache).
- **Modo estrito & Paper trading:** `allow_price_fallback=false`, `paper_trading_only=true`, `LLM_ENABLED=false` por padrão, sem recomendação personalizada.
- **Segredos:** Nunca gravar `.env` real, chaves ou tokens no repositório ou no Google Drive (usar `%LOCALAPPDATA%\Heuristika\.env`).

## 3. Portabilidade em Dois PCs (Projeto no Google Drive)
- Projeto permanece no Google Drive; **fora do Drive** ficam: `.venv` (`%LOCALAPPDATA%\Heuristika\venv-sinais`), banco SQLite (`%LOCALAPPDATA%\Heuristika\sinais_vip.db`), `.env` (`%LOCALAPPDATA%\Heuristika\.env`), cache local (`%LOCALAPPDATA%\Heuristika\cache\`) e `__pycache__` (`PYTHONDONTWRITEBYTECODE=1`).
- Zero caminhos absolutos de máquina (`J:\`, `C:\Users\`) em código, testes ou scripts.

## 4. Regras de Teste e Relatórios
- **Testes:** Usar apenas fixtures sintéticas em `tests/` (nunca depender do snapshot de produção). Justificar qualquer alteração em testes ou `audit/run_audit.py` no `HANDOFF.md`.
- **Relatórios:** Nome com data real (`AAAA-MM-DD`), preservando versões anteriores; registrar SHA-256 em `audit/reports/MANIFEST.json`; relatórios gerados são imutáveis (notas de auditoria vão em `audit/reports/notes_AAAA-MM-DD.md`).

## 5. Mapa de Arquivos por Responsabilidade (Paralelismo Seguro)
Subagentes só podem trabalhar em paralelo em áreas **disjuntas**; o Construtor integra. **Nunca dois agentes no mesmo arquivo.**
- **Dados e CVM:** `cvm_pipeline.py`, `data_collector.py`, `market_data.py`, `local_cache.py`, `calendar_fill.py`
- **Motor e Backtests:** `strategies_engine.py`, `strategies_config.json`, `global_radar.py`, `audit/tools/run_long_backtests.py`
- **Agente:** `strategy_agent.py`
- **Interface e Rotas:** `app.py`, `templates/`, `static/`, `build_github_pages.py`
- **Auditoria e Testes:** `audit/run_audit.py`, `audit/independent/`, `tests/`

## 6. Formato Curto de Entrega
- Resumo objetivo do que mudou, números antes/depois, `AUDIT_EXIT_CODE`, parecer do Auditor e pendências que exijam decisão humana.
