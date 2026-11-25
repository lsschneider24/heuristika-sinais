# Lições Aprendidas (`LESSONS.md`)

Todo agente deve ler este arquivo antes de iniciar e acrescentar novas lições ao final de cada marco.

1. **Dado ausente nunca vira zero (`0.0`):** Converter dado ausente em `0.0` mascara falhas de coleta e aprova ativos indevidamente (ex.: `net_debt_ebitda=0.0` em bancos ou `payout=0.0` quando ausente). Usar `null` / `"indisponível"`.
2. **Ativo nunca é excluído por diferença de calendário:** Excluir um ativo por `d_cur not in px[s]` em feriados locais (ex.: Memorial Day/Presidents' Day nos EUA com B3 aberta) concentrou 100% do `risk_parity_simplified` em `BOVA11.SA` por um trimestre (`-51.18%` DD). Usar forward-fill limitado (`calendar_fill.py`, até 5 datas) e sinalizar.
3. **Testes não usam snapshot de produção:** Testes acoplados a `data/b3_fundamentals.json` quebram quando o coletor atualiza. Usar sempre fixtures sintéticas em `tests/fixtures_strategies.py`.
4. **Benchmarks sempre na mesma janela:** Comparar CAGR/Sharpe/MaxDD de uma estratégia com benchmarks em janelas diferentes gera conclusões falsas. Calcular CDI, BOVA11 e IVVB11 exatamente entre `start_date` e `end_date` da estratégia.
5. **Distorção por resultado não recorrente:** Lucro LTM comprimido por evento atípico (ex.: `VALE3` impairment 4T25 -> `4245.5%` payout; `KLBN11` `261.21%`) ou salto não recorrente (`GGBR4`, `AXIA3`) distorce payout. Regra geral: `payout > 100%` ou `|12m - DFP| > 30 p.p.` -> `"indisponível"` e `verified=false`.
6. **Universo escolhido hoje gera viés de sobrevivência e seleção:** Criptoativos (`BTC-USD`, `ETH-USD`) escolhidos hoje concentram retorno histórico em `trend_following_turtles` e `radar_top_n`. Exibir aviso explícito e separar efeito seleção vs universo (pesos iguais).
7. **Renormalização pós-teto não pode violar os tetos:** Normalizar `w / sum(w)` após aplicar tetos de 35%/ativo e 50%/classe re-estoura os limites. Usar *water-filling* iterativo.
8. **Higiene do Google Drive:** `.venv`, `.env`, `*.db*` e `__pycache__` dentro do Drive causam conflitos de sincronização entre 2 PCs. Manter tudo em `%LOCALAPPDATA%\Heuristika\` e usar `PYTHONDONTWRITEBYTECODE=1`.
