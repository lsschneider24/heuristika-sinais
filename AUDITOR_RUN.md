# Checklist de Auditoria Independente — `AUDITOR_RUN.md`

Execute cada item abaixo de forma independente (sem alterar código de estratégias ou testes):

1. **Integridade do relatório e `MANIFEST.json`:**
   - Execute `audit/run_audit.py` com o venv externo (`%LOCALAPPDATA%\Heuristika\venv-sinais\Scripts\python.exe` e `PYTHONDONTWRITEBYTECODE=1`).
   - Nunca edite o relatório gerado (`audit/reports/audit_AAAA-MM-DD_HHMM.md`). Registre comentários em `audit/reports/notes_AAAA-MM-DD.md`.
   - Confirme `exit_code=0` e que `audit/reports/MANIFEST.json` valida todos os hashes SHA-256.

2. **Reconciliação independente:**
   - A partir apenas de `README.md` e `strategies_config.json` (sem ler `strategies_engine.py` nem `audit/tools/reconcile_backtests.py`), recompute `indexacao_bogle`, `trend_following_turtles` e `dual_momentum_global` e compare com `audit/reports/backtest_long_*.md`.

3. **Conferência externa de fundamentos (amostra):**
   - Compare `payout_pct` e `roe_pct` de 3 a 5 empresas (incluindo um banco, ex.: `ITUB4`, e a `VALE3`) em `data/b3_fundamentals.json` com fontes externas oficiais (RI ou CVM).
   - Confirme que nenhum dado ausente virou `0.0` e que `VALE3` não foi marcada `verified=true` com payout > 300%.

4. **Backtests completos e giro:**
   - Confirme que todas as 5 estratégias (com e sem cripto para Turtles e Radar Top-N) estão em `audit/reports/backtest_long_*.md` com janela >= 10 anos efetivos, benchmarks na mesma janela e sensibilidade da banda de rebalanceamento (`0%`, `10%`, `25%`, `50%`).

5. **Dividendos e `evento_corporativo`:**
   - Informe a contagem de `verified=true/false` e quantos ativos ficaram elegíveis para `dividendos_barsi`.
   - Confirme que `BBAS3` foi detectado pelo detector automático de anúncios (CVM IPE 90d) e YoY.

6. **Portabilidade 2 PCs e Git no Drive:**
   - Confirme ausência de `.venv`, `.env` real, `*.db*` e `__pycache__` dentro da pasta do projeto.
   - Confirme ausência de caminhos absolutos (`J:\`, `C:\Users\`) em código, testes e documentação.
   - Confirme `git fsck`, `git status` limpo, backups datados em `backups_repo/` e `backups_db/`, e nenhum push/remoto novo.
   - Execute teste de segundo PC simulado em pasta temporária (`setup_pc.ps1` + `run_audit.py` -> `PASS`) e apague a cópia temporária.

7. **Governança, Admin e Botão Único:**
   - Confirme que `approve_or_reject_proposal`, `/api/admin/strategies/proposals/<id>/decide` e `/api/admin/atualizar-laboratorio` exigem Admin (`403` sem Admin) e que `strategy_agent.py` opera em modo determinístico por padrão (`LLM_ENABLED=false`), recusando recomendação personalizada.
   - Confirme que `atualizar_tudo.ps1` e o botão no `/admin` existem e estão cobertos por testes.
