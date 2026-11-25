# Backlog Priorizado (`BACKLOG.md`)

| ID | Descrição | Critério de Aceite (Definição de Pronto) | Verificação | Estado |
| --- | --- | --- | --- | --- |
| **BL-01** | Conferência manual dos 13 ativos com `verified=false` em `data/b3_fundamentals.json` | Evidência primária gravada em `audit/evidence/fundamentals_evidence.json` para os ativos revisados | Completa | Pendente (decisão usuário) |
| **BL-02** | Coleta noturna agendada no PC principal (`coleta_noturna.ps1` + Agendador Windows) | Tarefa agendada rodando sem interação e atualizando cache local fora do Drive | Módulo | Pronto (script criado; agendar no PC) |
| **BL-03** | Estratégia `value_graham` (Fase 2) — somente paper trading prospectivo | Habilitada em `strategies_config.json` com `prospective_paper_only` e testes sintéticos | Completa | Planejado |
| **BL-04** | Estratégia `qualidade_compounders` (Fase 2) — somente paper trading prospectivo | Habilitada com filtros ROIC/Margem/Dívida em modo estrito e testes sintéticos | Completa | Planejado |
| **BL-05** | Estratégia `fatorial_multifactor` (Fase 2) — somente paper trading prospectivo | Z-Score Value+Momentum+Quality+LowVol com testes sintéticos | Completa | Planejado |
| **BL-06** | Acompanhamento periódico das carteiras simuladas | Registro mensal de aderência, drift e propostas no painel `/carteiras` | Módulo | Em operação |
| **BL-07** | Adaptador opcional de LLM (desligado por padrão) | `LLM_ENABLED=false` por padrão; se ligado, respeita `max_requests_per_minute=5` e fallback determinístico | Módulo | Implementado (desligado) |
