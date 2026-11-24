# Relatório de Backtests em Janela Longa (10 Anos) e Investigação de Anomalias — 2026-11-24 08:22:36

## 1. Datas Reais de Cada Série (Yahoo Finance `range=10y` + BCB SGS CDI)
- `CDI (BCB SGS Série 12)`: `2016-11-24` a `2026-11-19` (2507 dias úteis)
- `BOVA11.SA`: `2016-11-23` a `2026-11-23` (2490 barras)
- `IVVB11.SA`: `2016-11-23` a `2026-11-23` (2490 barras)
- `^BVSP`: `2016-11-23` a `2026-11-23` (2483 barras)
- `USDBRL=X`: `2016-11-24` a `2026-11-24` (2601 barras)
- `PETR4.SA`: `2016-11-23` a `2026-11-23` (2491 barras)
- `VALE3.SA`: `2016-11-23` a `2026-11-23` (2491 barras)
- `ITUB4.SA`: `2016-11-23` a `2026-11-23` (2491 barras)
- `WEGE3.SA`: `2016-11-23` a `2026-11-23` (2491 barras)
- `GC=F`: `2016-11-25` a `2026-11-24` (2515 barras)
- `BTC-USD`: `2017-04-26` a `2026-11-24` (3500 barras)
- `IVV`: `2016-11-25` a `2026-11-23` (2512 barras)
- `VGK`: `2016-11-25` a `2026-11-23` (2512 barras)
- `EEM`: `2016-11-25` a `2026-11-23` (2512 barras)

### Por que `IVV` aparecia como `limiting_asset` na janela curta anterior?
- Em `market_data.py`, o padrão anterior buscava `range=2y` e fatiava `candles[-limit:]` (`limit=300` ou `420`). Como pregões de EUA (`IVV`, ~250/ano), Brasil (`BOVA11.SA`, ~248/ano) e câmbio (`USDBRL=X`, ~260/ano) têm calendários distintos, a interseção após `[-420:]` fazia `IVV` iniciar poucos dias depois ou com menos barras comuns após `lookback=252` (deixando apenas 91 barras úteis), apesar de `IVV` ter histórico real de 10+ anos.

## 2. Resultados em Janela Longa (Entrada Progressiva de Ativos)

### `indexacao_bogle`
- **Janela:** `2016-11-23` a `2026-11-23` (`2490` barras, `10.0` anos) | **Universo completo desde:** `2016-11-23`
- **Retorno Total:** `261.17%` | **Retorno Anualizado (CAGR):** `13.7%` | **Volatilidade:** `9.52%` | **Drawdown Máx:** `-21.43%` | **Sharpe vs CDI:** `0.47`
- **Giro Anual:** `5.84%` | **Custos Pagos (acumulados):** `0.09%`
- **Benchmarks na mesma janela:** `CDI=143.16%`, `BOVA11=170.0%`, `IVVB11=528.36%`, `IBOV_PRICE=165.86%`
- **Janelas móveis 12m (2238 janelas):** mín `-7.96%`, mediana `16.0%`, máx `51.28%`
- **Por ano calendário:** `{'2016': -0.93, '2017': 18.88, '2018': 11.1, '2019': 22.85, '2020': 18.6, '2021': 9.27, '2022': -1.98, '2023': 16.84, '2024': 16.67, '2025': 16.52, '2026': 11.37}`

### `trend_following_turtles (com BTC-USD)`
- **Janela:** `2017-09-07` a `2026-11-24` (`2404` barras, `9.21` anos) | **Universo completo desde:** `2018-01-30`
- **Retorno Total:** `193.96%` | **Retorno Anualizado (CAGR):** `12.42%` | **Volatilidade:** `12.6%` | **Drawdown Máx:** `-18.34%` | **Sharpe vs CDI:** `0.25`
- **Giro Anual:** `973.6%` | **Custos Pagos (acumulados):** `13.45%`
- **Benchmarks na mesma janela:** `CDI=135.12%`, `BOVA11=128.82%`, `IVVB11=505.26%`, `IBOV_PRICE=125.5%`
- **Janelas móveis 12m (2152 janelas):** mín `-17.16%`, mediana `12.83%`, máx `69.01%`
- **Por ano calendário:** `{'2017': 4.26, '2018': -1.26, '2019': 18.27, '2020': 46.47, '2021': -1.53, '2022': 0.29, '2023': 7.34, '2024': 21.49, '2025': 30.13, '2026': -1.65}`

### `trend_following_turtles_sem_cripto`
- **Janela:** `2017-09-07` a `2026-11-24` (`2375` barras, `9.21` anos) | **Universo completo desde:** `2017-09-12`
- **Retorno Total:** `155.09%` | **Retorno Anualizado (CAGR):** `10.7%` | **Volatilidade:** `11.88%` | **Drawdown Máx:** `-17.55%` | **Sharpe vs CDI:** `0.15`
- **Giro Anual:** `896.43%` | **Custos Pagos (acumulados):** `12.39%`
- **Benchmarks na mesma janela:** `CDI=131.72%`, `BOVA11=128.82%`, `IVVB11=505.26%`, `IBOV_PRICE=125.5%`
- **Janelas móveis 12m (2123 janelas):** mín `-16.1%`, mediana `10.61%`, máx `50.02%`
- **Por ano calendário:** `{'2017': 4.26, '2018': 0.26, '2019': 18.61, '2020': 26.74, '2021': -0.8, '2022': 0.14, '2023': 3.31, '2024': 16.87, '2025': 28.18, '2026': 5.6}`

### `dual_momentum_global (BRL)`
- **Janela:** `2018-01-12` a `2026-11-23` (`2277` barras, `8.86` anos) | **Universo completo desde:** `2018-01-12`
- **Retorno Total:** `126.42%` | **Retorno Anualizado (CAGR):** `9.66%` | **Volatilidade:** `20.41%` | **Drawdown Máx:** `-23.42%` | **Sharpe vs CDI:** `0.11`
- **Giro Anual:** `485.19%` | **Custos Pagos (acumulados):** `6.45%`
- **Benchmarks na mesma janela:** `CDI=124.74%`, `BOVA11=111.75%`, `IVVB11=418.38%`, `IBOV_PRICE=107.69%`
- **Janelas móveis 12m (2025 janelas):** mín `-11.36%`, mediana `9.08%`, máx `40.9%`
- **Por ano calendário:** `{'2018': -4.07, '2019': 25.82, '2020': 2.68, '2021': 16.47, '2022': -1.89, '2023': 12.98, '2024': 28.13, '2025': 0.37, '2026': 10.05}`

## 3. Investigação de Anomalias (Bloco C)
1. **`dual_momentum_global` (-18,97% e 34,1% vol na janela curta de 91 barras):**
   - **Diagnóstico: comportamento legítimo (sem bug de conversão USD→BRL, sinal ou t+1).** Na janela curta de `2026-06-17` a `2026-11-23`, o ativo manteve `EEM` (momentum 12m em BRL `+50,85%`) de junho a outubro (`-6,24%`, `+5,47%`, `-2,63%`) e rotacionou para `BOVA11.SA` em `2026-10-07` (momentum 12m `+53,05%`) imediatamente antes da queda de `-16,25%` do Ibovespa entre outubro e novembro de 2026. Na janela longa de 10 anos, o comportamento se normaliza conforme seção 2.
   - **Rastreio recente (janela longa):**
     - `2026-01-15: escolhido=BOVA11.SA | moms={'CDI': 14.45, 'IVV': 4.8, 'VGK': 21.8, 'EEM': 25.48, 'BOVA11.SA': 40.18}`
     - `2026-02-13: escolhido=BOVA11.SA | moms={'CDI': 14.62, 'IVV': -1.21, 'VGK': 21.33, 'EEM': 25.58, 'BOVA11.SA': 49.31}`
     - `2026-03-17: escolhido=BOVA11.SA | moms={'CDI': 14.76, 'IVV': 0.55, 'VGK': 14.18, 'EEM': 25.47, 'BOVA11.SA': 46.46}`
     - `2026-04-16: escolhido=BOVA11.SA | moms={'CDI': 14.8, 'IVV': 3.44, 'VGK': 8.33, 'EEM': 26.64, 'BOVA11.SA': 56.43}`
     - `2026-05-18: escolhido=EEM | moms={'CDI': 14.81, 'IVV': 15.47, 'VGK': 10.98, 'EEM': 31.7, 'BOVA11.SA': 28.31}`
     - `2026-06-16: escolhido=EEM | moms={'CDI': 14.79, 'IVV': 26.96, 'VGK': 16.8, 'EEM': 46.9, 'BOVA11.SA': 24.75}`
     - `2026-07-15: escolhido=EEM | moms={'CDI': 14.73, 'IVV': 17.05, 'VGK': 8.84, 'EEM': 30.58, 'BOVA11.SA': 29.3}`
     - `2026-08-13: escolhido=EEM | moms={'CDI': 14.66, 'IVV': 21.3, 'VGK': 17.27, 'EEM': 32.62, 'BOVA11.SA': 23.5}`
     - `2026-09-14: escolhido=BOVA11.SA | moms={'CDI': 14.57, 'IVV': 13.06, 'VGK': 7.65, 'EEM': 25.51, 'BOVA11.SA': 31.52}`
     - `2026-10-13: escolhido=BOVA11.SA | moms={'CDI': 14.47, 'IVV': 14.21, 'VGK': 3.92, 'EEM': 24.18, 'BOVA11.SA': 44.74}`
     - `2026-11-11: escolhido=EEM | moms={'CDI': 14.37, 'IVV': 21.54, 'VGK': 22.8, 'EEM': 24.67, 'BOVA11.SA': 14.69}`

2. **`trend_following_turtles` (-1,26% na janela curta) e `radar_top_n` (-15,38% na janela curta):**
   - **Diagnóstico: legítimo.** Na janela curta (`2026-06-23..2026-11-23`), o regime global virou `RISK-OFF` com queda simultânea de `BTC-USD`, `BOVA11` e ativos de risco no 4T26, acionando stops de `2*ATR(14)` e perda da `MM200` com giro e fricção de `15 bps`.
   - **Rastreio recente Turtles:**
     - `2026-09-03: ativos_tendencia=['ITUB4.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=25.0%`
     - `2026-09-10: ativos_tendencia=['IVVB11.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=26.9%`
     - `2026-09-17: ativos_tendencia=['BOVA11.SA', 'IVVB11.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=12.8%`
     - `2026-09-24: ativos_tendencia=['BOVA11.SA', 'IVVB11.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=14.5%`
     - `2026-10-01: ativos_tendencia=['BOVA11.SA', 'BTC-USD', 'IVVB11.SA', 'PETR4.SA'], caixa_cdi=21.4%`
     - `2026-10-08: ativos_tendencia=['BOVA11.SA', 'BTC-USD', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=6.6%`
     - `2026-10-15: ativos_tendencia=['BOVA11.SA', 'BTC-USD', 'ITUB4.SA', 'IVVB11.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=4.9%`
     - `2026-10-22: ativos_tendencia=['BOVA11.SA', 'BTC-USD', 'ITUB4.SA', 'IVVB11.SA', 'PETR4.SA'], caixa_cdi=8.2%`
     - `2026-10-29: ativos_tendencia=['IVVB11.SA', 'WEGE3.SA'], caixa_cdi=50.0%`
     - `2026-11-05: ativos_tendencia=['BTC-USD', 'IVVB11.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=13.6%`
     - `2026-11-12: ativos_tendencia=['IVVB11.SA', 'PETR4.SA', 'WEGE3.SA'], caixa_cdi=26.8%`
     - `2026-11-19: ativos_tendencia=['IVVB11.SA', 'WEGE3.SA'], caixa_cdi=50.0%`

3. **`indexacao_bogle` (20,22% vs média ponderada dos benchmarks de 18,77%):**
   - **Diagnóstico: legítimo (bônus de rebalanceamento por banda de 5 pp).** `BOVA11` teve forte alta até outubro/2026 antes do recuo de `-16%`; o gatilho de desvio `> 5 pp` realizou parte de `BOVA11` perto do topo e recomprou `CDI`/`IVVB11`, gerando `+1,45 pp` sobre a média estática `40/30/30`.
