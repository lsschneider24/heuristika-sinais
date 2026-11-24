# Ferramentas de Auditoria e Evidência (`audit/tools/`)

- `run_real_evidence.py`: executa os backtests reais das 5 estratégias baseadas em preço (`indexacao_bogle`, `trend_following_turtles`, `dual_momentum_global`, `risk_parity_simplified`, `radar_top_n`) e o `global_radar.scan_global_opportunities()`, gerando `audit/reports/backtest_evidence_AAAA-MM-DD.md`.
- `reconcile_backtests.py`: script independente (sem importar `strategies_engine.py`) que recomputa `indexacao_bogle` e `trend_following_turtles` a partir de séries brutas de preços e CDI e compara com os resultados do motor (tolerância `<= 1.5 pp`).

> Nota: os scripts temporários exploratórios usados na rodada anterior (`inspect_si.py`, `test_si2.py`, `check_fundamentus_one_by_one.py`, `check_statusinvest_one_by_one.py`, `compare_dy.py`, `generate_evidence.py`) ficaram restritos ao diretório de scratch da sessão e não permanecem na raiz do repositório.
