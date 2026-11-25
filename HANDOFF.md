# HANDOFF — Etapa 2C (Construtor → Auditor)

## Estado Atual
- **Etapa 2C implementada pelo Construtor** em commits locais incrementais no branch `main` (sem push).
- `.gitignore` verificado: cobre `.env`, `*.db*`, `sinais_vip.db*`, `backups/`, `data/cdi_sgs_cache.json` e `data/collector_cache/`.
- **Nota sobre o teste de catálogo (`9 != 6`):** em `tests/test_basic.py` (`test_phase1_prerequisites_and_phase2a_deterministic_engine`), o teste originalmente esperava `6` estratégias (Etapa 2A) e foi atualizado para `9` após a Etapa 2B (6 estratégias Fase 1 ativas + 3 Fase 2).

## O que foi feito na Etapa 2C
1. **Integridade da auditoria (A):**
   - `audit/run_audit.py` atualizado para gravar o SHA-256 completo de cada relatório gerado em `audit/reports/MANIFEST.json` e falhar (`FAIL`) se qualquer relatório listado tiver hash divergente ou estiver ausente.
2. **Coletor e Política de Dados (B + C):**
   - Criado `data_collector.py` para gerar `data/b3_fundamentals.json` a partir de fontes públicas gratuitas (Yahoo Finance para `dy_12m_pct` e `years_paying`, documentando tratamento bruto de JCP; Fundamentus apenas como checagem cruzada pontual com cache 24h e pausa `>= 1,2s`; StatusInvest removido por `robots.txt` HTTP 403 / termos de uso).
   - Tabela `ticker_aliases` (`ELET3 -> AXIA3`, `CPLE6 -> CPLE3`, `IRANI3 -> RANI3`) e flag `evento_corporativo` (`BBAS3` excluído da seleção por redução de payout em 10/11/2026).
   - `market_data.py` e `strategies_engine.py` atualizados para respeitar `evento_corporativo` na estratégia `dividendos_barsi`.
   - Resultado da coleta (`COLLECTED=35`, `VERIFIED_TRUE=0`, `VERIFIED_FALSE=35`, `CORPORATE_EVENTS=1`): estratégia `dividendos_barsi` em modo estrito permanece com **0 ativos elegíveis** (`carteira incompleta: 0 de 10 ativos`, 100% alocado em CDI).
3. **Evidência Real de Backtests, Reconciliação e Radar Global (D):**
   - Criado `audit/tools/run_real_evidence.py` e gerado `audit/reports/backtest_evidence_2026-11-24.md` com janela, ativo limitante, métricas, custos e benchmarks das 5 estratégias baseadas em preço + Radar Global (`RISK-OFF`, `4 de 4 sinais disponíveis`, teste `^TNX=4.918%` e `^IRX=4.147%`).
   - Criado `audit/tools/reconcile_backtests.py` (sem importar `strategies_engine.py`): `indexacao_bogle` (`20.22%` vs `20.22%`, `0.00 pp`, **PASS**) e `trend_following_turtles` (`-1.26%` vs `-1.25%`, `0.01 pp`, **PASS**), `exit_code=0`.
4. **Organização (E):**
   - Criado `audit/tools/README.md` e `docs/MIGRACAO_LOCAL.md` (proposta de migração para fora do Google Drive, não executada).

## Arquivos Alterados / Criados
- `audit/run_audit.py`
- `audit/reports/notes_2026-11-24.md`
- `.gitignore`
- `data_collector.py`
- `data/b3_fundamentals.json`
- `market_data.py`
- `strategies_engine.py`
- `audit/tools/run_real_evidence.py`
- `audit/tools/reconcile_backtests.py`
- `audit/tools/README.md`
- `audit/reports/backtest_evidence_2026-11-24.md`
- `docs/MIGRACAO_LOCAL.md`
- `HANDOFF.md`

## Pendências para o Auditor
1. Revisar as alterações em `audit/run_audit.py` (implementação de `MANIFEST.json`) e nos demais arquivos listados.
2. Executar `python audit/run_audit.py` para gerar o relatório oficial com `MANIFEST.json` inicializado e validar `exit code 0`.
3. Conferir `audit/reports/backtest_evidence_2026-11-24.md` e `audit/tools/reconcile_backtests.py`.
4. Confirmar com o usuário se deseja executar a migração descrita em `docs/MIGRACAO_LOCAL.md`.

## Parecer do Auditor (Revisão Etapa 2C)
- **Status:** **FAIL (`exit_code=1`)** — Relatório: `audit/reports/audit_2026-11-24_0741.md` (hash conferido em `audit/reports/MANIFEST.json`).
- **Única falha:** `tests/test_basic.py:885` (`AssertionError: 4.61 != 'indisponível'` em `BBAS3["values"]["dy_12m_pct"]`), pois `data_collector.py` marcou `dy_12m_pct.verified=true` em `BBAS3` mesmo com `evento_corporativo=true`, divergindo da expectativa do teste unitário.
- **Demais checagens:** `test_audit_specifics.py` (`8/8`), `test_global_radar.py` (`3/3`), governança, triggers, backup, `MANIFEST.json`, `reconcile_backtests.py` (`0.00 pp` e `0.01 pp`) e Radar Global (`RISK-OFF`, `4/4` sinais, `^TNX`/`^IRX`) todos **PASS**.
- **Pendências:**
  1. Construtor: resolver o conflito `BBAS3.fields.dy_12m_pct.verified` vs `tests/test_basic.py:885` (idealmente forçar `verified=false` nos campos de ativos com `evento_corporativo=true`, ou justificar atualização do teste).
  2. Auditor: reexecutar `python audit/run_audit.py` após correção para confirmar `EXIT 0` e validar a checagem de `MANIFEST.json` sobre `audit_2026-11-24_0741.md`.

---

# HANDOFF — Etapa 2D (Construtor → Auditor)

## O que foi feito na Etapa 2D
1. **A — Correção e isolamento de testes (`tests/test_basic.py` e `tests/fixtures_strategies.py`):**
   - `test_phase1_strategy_foundation_and_strict_data` (linha 885) reescrito para usar a fixture sintética `make_synthetic_b3_snapshot_json` em `tests/fixtures_strategies.py`, eliminando dependência do snapshot de produção `data/b3_fundamentals.json`.
   - Adicionado `test_dividendos_excludes_evento_corporativo` garantindo que `evento_corporativo=True` exclui o ativo (ex.: `BBAS3`) mesmo com todos os campos verificados.
   - Atualizado `test_phase1_prerequisites_and_phase2a_deterministic_engine` (linha 1036) para validar `net_debt_ebitda is None` e `roe_pct >= 12.0` em Financeiras (`Bancos`, `Seguros`) e `net_debt_ebitda <= 3.0` nas demais, refletindo a nova regra de D.2.
2. **B + C — Backtests em janela longa (10 anos), entrada progressiva e investigação de anomalias:**
   - `market_data.py` recebeu `range_str: str = "2y"` em `get_strict_daily_candles`.
   - Criado `audit/tools/run_long_backtests.py` e gerado `audit/reports/backtest_long_2026-11-24.md` (com entrada progressiva de ativos, `full_universe_since`, versão sem cripto, giro anual, custos pagos, resultados por ano calendário, janelas móveis de 12m e explicação de por que `IVV` aparecia como limitante na janela curta de `limit=420`).
   - Criado `audit/tools/investigate_anomalies.py` comprovando que as variações de `dual_momentum_global` (-18,97% em 91 barras por rotação para `EEM` e depois `BOVA11.SA` antes da queda de -16,25% em out-nov/2026), `trend_following_turtles`, `radar_top_n` e `indexacao_bogle` (+20,22% vs 18,77% por bônus de rebalanceamento) são legítimas e sem bug de conversão/look-ahead.
3. **D — Pipeline CVM (DFP 2025) + Regra ROE para Financeiras:**
   - Criado `cvm_pipeline.py` (dados abertos `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip`) calculando `payout_pct` (DVA 7.08.04.01+7.08.04.02 / DRE 3.11), `net_debt_ebitda` (não-financeiras) e `roe_pct` (DRE 3.11 / BPP 2.03 para Financeiras).
   - `strategies_config.json`, `market_data.py`, `strategies_engine.py` e tabela `strategy_param_versions` atualizados com `min_roe_pct: 12.0` e dispensa de `net_debt_ebitda` para `Bancos` e `Seguros`.
   - Reexecutado `data_collector.py`: **`20/35` ativos com `verified=true`**, **`1` evento corporativo (`BBAS3`)**, **`8` ativos elegíveis para `dividendos_barsi`** (`LEVE3`, `VALE3`, `PETR4`, `VIVT3`, `CPLE3`, `PSSA3`, `CXSE3`, `B3SA3` a 10% cada + `20%` em `SELIC_CDI` → `carteira incompleta: 8 de 10 ativos`).
4. **F — Suíte de testes completa:** `24/24` testes passando (`tests/test_basic.py`, `tests/test_audit_specifics.py`, `tests/test_global_radar.py`, `exit_code=0`).

## Arquivos Alterados / Criados na Etapa 2D
- `tests/fixtures_strategies.py`
- `tests/test_basic.py`
- `market_data.py`
- `strategies_config.json`
- `strategies_engine.py`
- `cvm_pipeline.py`
- `data_collector.py`
- `data/b3_fundamentals.json`
- `audit/tools/run_long_backtests.py`
- `audit/tools/investigate_anomalies.py`
- `audit/reports/backtest_long_2026-11-24.md`
- `HANDOFF.md`

## Pendências para o Auditor
1. Escrever e executar sua própria reconciliação independente a partir de `README.md` e `strategies_config.json` (sem ler `strategies_engine.py` nem `audit/tools/reconcile_backtests.py`).
2. Executar `python audit/run_audit.py` e validar `EXIT 0`, integridade de `MANIFEST.json` e relatório `backtest_long_2026-11-24.md`.
3. Revisar as justificativas das alterações em `tests/test_basic.py`.

## Parecer do Auditor (Revisão Etapa 2D + Itens 7–13)
- **`audit/run_audit.py`:** **PASS (`exit_code=0`)** — Relatório: `audit/reports/audit_2026-11-24_0955.md` (`24/24` testes OK, `MANIFEST.json` válido).
- **Parecer Etapa 2D:** **FAIL (pendência específica no Item 7 e melhoria no Pipeline CVM/Evento Corporativo)**:
  1. **Item 7 (Bloqueante):** incluir `risk_parity_simplified` e `radar_top_n` (com e sem cripto, com rastreio de entradas/saídas) em `audit/reports/backtest_long_2026-11-24.md`.
  2. **Item 9/10 (Pipeline CVM):** evoluir `cvm_pipeline.py` para LTM (`DFP 2025 - ITR 9M25 + ITR 9M26`) e fallback para `DFC`/`DMPL` quando `DVA 7.08.04.01/02` vier zerado (casos `ITUB4`, `BBSE3`, `VALE3`).
  3. **Item 11 (`evento_corporativo`):** implementar regra automática sem viés sazonal (ex.: queda >= 40% em 12m móveis YoY ou 6m vs mesmo 6m do ano anterior).

---

# HANDOFF — Etapa 2E (Construtor → Auditor)

## O que foi feito na Etapa 2E
1. **A + B — Backtests completos (12+ anos) e Banda de Rebalanceamento:**
   - `market_data.fetch_bcb_cdi_series` atualizado para fatiar consultas ao SGS/BCB em blocos de até 3.200 dias (suportando 15 anos de CDI diário).
   - `audit/tools/run_long_backtests.py` atualizado com `range_str="15y"` e todas as 5 estratégias baseadas em preço (`indexacao_bogle`, `trend_following_turtles` c/ e s/ cripto, `dual_momentum_global`, `risk_parity_simplified`, `radar_top_n` c/ e s/ cripto), mais benchmarks (`CDI`, `BOVA11`, `IVVB11`) com volatilidade, MaxDD e Sharpe na mesma janela de cada estratégia.
   - `strategies_config.json` e `strategy_param_versions` atualizados com `rebalance_band_pct: 25.0` e `min_order_pct: 2.0` para `trend_following_turtles` e `dual_momentum_global`; sensibilidade documentada para `0%`, `10%`, `25%` e `50%` em `audit/reports/backtest_long_2026-11-24.md`.
2. **C — Pipeline CVM LTM (`DFP 2025 - ITR 9M25 + ITR 9M26`) e Sem Zero Indevido:**
   - `cvm_pipeline.py` reescrito: dado ausente/zerado nunca vira `0.0` (retorna `None` / `'indisponível'`); lê `_con_` com fallback `_ind_` (`ABCB4: 020958`, `SAPR11: 018627`); usa DVA (`7.08.04` / `7.09.04` / `7.11.04`) com fallback `DFC 6.03.*` (corrigindo `VALE3`, `ITUB4`, `BBSE3`, `BBAS3`); registra `data_base` (`2026-09-30` LTM).
   - `data_collector.py` atualizado com tolerância relativa de DY (`15%` / `±0,5 pp`) considerando JCP bruto vs líquido (85%).
   - Resultado da coleta: **`26/35` ativos `verified=true`**, **`9` `verified=false`**, **`8` elegíveis para `dividendos_barsi`** (`CMIG4`, `LEVE3`, `VIVT3`, `PSSA3`, `CPLE3`, `CXSE3`, `TIMS3`, `B3SA3` a 10% + `20%` `SELIC_CDI` → `carteira incompleta: 8 de 10 ativos`).
3. **D — Detectores Automáticos de `evento_corporativo`:**
   - Detector YoY de proventos 12m (queda `>= 40%` vs 12m anteriores no Yahoo Finance) + varredura de comunicados CVM IPE (`ipe_cia_aberta_2026.zip`, últimos 90 dias) + `CORPORATE_EVENTS` manual como exceções adicionais. `BBAS3` foi capturado pelos 3 critérios simultaneamente (`10` ativos sinalizados).
4. **E — Testes (`25/25 OK`):**
   - Adicionado `test_cvm_missing_data_never_zero` em `tests/test_basic.py`.
   - Pré-requisito 4 em `test_phase1_prerequisites_and_phase2a_deterministic_engine` isolado com `make_synthetic_b3_snapshot_json` para não depender do snapshot de produção (`BBAS3` passou a `verified=true` após o fallback DFC+ROE, sendo excluído da seleção via `evento_corporativo`).

## Arquivos Alterados / Criados na Etapa 2E
- `market_data.py`
- `strategies_config.json`
- `cvm_pipeline.py`
- `data_collector.py`
- `data/b3_fundamentals.json`
- `audit/tools/run_long_backtests.py`
- `audit/reports/backtest_long_2026-11-24.md`
- `tests/test_basic.py`
- `HANDOFF.md`

## Pendências para o Auditor
1. Executar `python audit/run_audit.py` e confirmar `EXIT 0` + `MANIFEST.json`.
2. Validar o novo relatório completo `audit/reports/backtest_long_2026-11-24.md` (todas as 5 estratégias, 12+ anos, sensibilidade da banda).
3. Executar a reconciliação independente do Auditor (a partir de `README.md` e `strategies_config.json`).

## Parecer do Auditor (Revisão Etapa 2E)
- **`audit/run_audit.py`:** **PASS (`exit_code=0`)** — Relatório: `audit/reports/audit_2026-11-24_1403.md`.
- **Parecer Etapa 2E:** **FAIL** — apesar de `run_audit.py`, backtests 12+ anos, banda de `25%`, regra de zero indevido e detectores `evento_corporativo` (`BBAS3` pego pelo IPE 90d) estarem aprovados, a **amostragem externa** revelou erro de escala/moeda no `cvm_pipeline.py`:
  1. `VALE3` está com `payout_pct=4245.5%`, `roe_pct=0.28%` e `verified=true` (divergência de moeda/escala entre DFC e DRE).
  2. Bancos (`ITUB4` `roe=1.95%` vs `23.6%` RI 3T26, `SANB11` `1.23%`, `BBDC4` `5.59%`) com `ESCALA_MOEDA` / conta incorreta no LTM.
- **Pendência para o Construtor:** normalizar `ESCALA_MOEDA` (`MIL` vs `UNIDADE`) e `MOEDA` no `cvm_pipeline.py` (e adicionar sanity check para `payout > 200%` ou `roe` implausível não virarem `verified=true`).

---

# Fluxo de Trabalho em Dois PCs (Projeto no Google Drive)

> **Decisão:** o repositório permanece no Google Drive para trabalho alternado entre dois PCs (um de cada vez).

## Regras Operacionais (Obrigatórias)
1. **Um PC por vez:** nunca abra o projeto nem rode o servidor nos dois PCs simultaneamente.
2. **Disponível offline:** marque a pasta do projeto como **"Disponível offline"** no Google Drive Desktop nos dois PCs.
3. **Antes de trocar de PC:** feche o servidor Flask e o Antigravity, remova `WORKING_PC.lock` (se ainda existir) e **aguarde o Google Drive indicar "Sincronizado"**.
4. **Trava de sessão (`WORKING_PC.lock`):**
   - `run.ps1` cria `WORKING_PC.lock` (nome do PC + horário ISO) ao iniciar e apaga ao encerrar.
   - Se encontrar um `WORKING_PC.lock` de outro PC com menos de **12 horas**, exibe aviso antes de continuar.
5. **Estado do banco SQLite (carteiras simuladas):**
   - O banco vivo fica sempre fora do Drive em `%LOCALAPPDATA%\Heuristika\sinais_vip.db` (e o `.env` em `%LOCALAPPDATA%\Heuristika\.env`).
   - O PC principal guarda o estado oficial; para transferir o estado ao segundo PC, gere um backup com `audit/tools/backup_drive_state.py` (salva em `backups_db/` e `backups_repo/`) e restaure no outro PC copiando o `.db` de `backups_db/` para `%LOCALAPPDATA%\Heuristika\sinais_vip.db`.

## Comandos em Cada PC
- **Preparar um PC novo (1ª vez):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\setup_pc.ps1
  ```
- **Subir o servidor Flask (usando venv externo):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\run.ps1
  ```
- **Rodar a auditoria completa (usando venv externo):**
  ```powershell
  $env:PYTHONDONTWRITEBYTECODE="1"
  & "$env:LOCALAPPDATA\Heuristika\venv-sinais\Scripts\python.exe" audit\run_audit.py
  ```
- **Gerar backup portátil (`git bundle` + `backup_database()`):**
  ```powershell
  & "$env:LOCALAPPDATA\Heuristika\venv-sinais\Scripts\python.exe" audit\tools\backup_drive_state.py
  ```
