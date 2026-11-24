# Relatório Completo de Backtests em Janela Longa (12+ Anos) e Sensibilidade de Banda — 2026-11-24 13:57:03

## 1. Datas Reais das Séries (Yahoo Finance `range=15y` + BCB SGS CDI)
- `CDI (BCB SGS Série 12)`: `2011-11-24` a `2026-11-23` (3766 dias úteis)
- `BOVA11.SA`: `2011-11-24` a `2026-11-24` (3726 barras)
- `BTC-USD`: `2014-09-17` a `2026-11-24` (4452 barras)
- `DBC`: `2011-11-25` a `2026-11-24` (3771 barras)
- `EEM`: `2011-11-25` a `2026-11-24` (3771 barras)
- `ETH-USD`: `2017-11-09` a `2026-11-24` (3303 barras)
- `EWJ`: `2011-11-25` a `2026-11-24` (3771 barras)
- `EWZ`: `2011-11-25` a `2026-11-24` (3771 barras)
- `GC=F`: `2011-11-25` a `2026-11-24` (3771 barras)
- `GLD`: `2011-11-25` a `2026-11-24` (3771 barras)
- `HYG`: `2011-11-25` a `2026-11-24` (3771 barras)
- `INDA`: `2012-02-03` a `2026-11-24` (3724 barras)
- `ITUB4.SA`: `2011-11-24` a `2026-11-24` (3727 barras)
- `IVV`: `2011-11-25` a `2026-11-24` (3771 barras)
- `IVVB11.SA`: `2014-04-29` a `2026-11-24` (3128 barras)
- `MCHI`: `2011-11-25` a `2026-11-24` (3771 barras)
- `PETR4.SA`: `2011-11-24` a `2026-11-24` (3727 barras)
- `QQQ`: `2011-11-25` a `2026-11-24` (3771 barras)
- `SHY`: `2011-11-25` a `2026-11-24` (3771 barras)
- `TLT`: `2011-11-25` a `2026-11-24` (3771 barras)
- `USDBRL=X`: `2011-11-24` a `2026-11-24` (3904 barras)
- `VALE3.SA`: `2011-11-24` a `2026-11-24` (3727 barras)
- `VGK`: `2011-11-25` a `2026-11-24` (3771 barras)
- `VNQ`: `2011-11-25` a `2026-11-24` (3771 barras)
- `WEGE3.SA`: `2011-11-24` a `2026-11-24` (3727 barras)
- `^BVSP`: `2011-11-24` a `2026-11-24` (3718 barras)

## 2. Resultados Completos (Todas as Estratégias + Benchmarks na Mesma Janela)

### `indexacao_bogle`
- **Janela:** `2014-04-29` a `2026-11-24` (`3128` barras, `12.57` anos) | **Universo completo desde:** `2014-04-29`
- **Métricas:** Retorno Total `432.17%` | **CAGR:** `14.22%` | **Volatilidade:** `9.47%` | **Drawdown Máx:** `-21.43%` | **Sharpe vs CDI:** `0.45`
- **Giro e Custos:** Giro anual `6.67%` | Custo médio/ano `0.01%` | Custo total `0.13%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `231.08%` | CAGR `9.99%` | Vol `0.23%` | MaxDD `0.0%` | Sharpe `1.85`
  - `BOVA11`: Retorno `222.01%` | CAGR `9.75%` | Vol `24.07%` | MaxDD `-46.93%` | Sharpe `0.11`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (2876):** mín `-7.96%`, mediana `15.72%`, máx `51.28%`
- **Por ano calendário:** `{'2014': 11.08, '2015': 15.55, '2016': 13.73, '2017': 19.19, '2018': 11.43, '2019': 22.85, '2020': 18.6, '2021': 9.27, '2022': -1.98, '2023': 16.84, '2024': 16.67, '2025': 16.52, '2026': 10.75}`

### `trend_following_turtles (c/ cripto, banda 25%)`
- **Janela:** `2012-09-12` a `2026-11-24` (`3699` barras, `14.2` anos) | **Universo completo desde:** `2015-06-23`
- **Métricas:** Retorno Total `418.16%` | **CAGR:** `12.28%` | **Volatilidade:** `12.47%` | **Drawdown Máx:** `-18.06%` | **Sharpe vs CDI:** `0.19`
- **Giro e Custos:** Giro anual `815.79%` | Custo médio/ano `2.45%` | Custo total `34.75%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `307.25%` | CAGR `10.4%` | Vol `0.22%` | MaxDD `0.0%` | Sharpe `1.48`
  - `BOVA11`: Retorno `175.87%` | CAGR `7.41%` | Vol `23.67%` | MaxDD `-46.93%` | Sharpe `0.03`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (3447):** mín `-16.6%`, mediana `12.8%`, máx `69.09%`
- **Por ano calendário:** `{'2012': -0.51, '2013': -2.76, '2014': -2.09, '2015': 11.44, '2016': 21.59, '2017': 40.23, '2018': -2.88, '2019': 18.49, '2020': 45.48, '2021': -0.61, '2022': 1.56, '2023': 8.13, '2024': 20.99, '2025': 29.89, '2026': 0.25}`

### `trend_following_turtles_sem_cripto (banda 25%)`
- **Janela:** `2012-09-12` a `2026-11-24` (`3661` barras, `14.2` anos) | **Universo completo desde:** `2015-02-13`
- **Métricas:** Retorno Total `217.08%` | **CAGR:** `8.47%` | **Volatilidade:** `11.95%` | **Drawdown Máx:** `-17.07%` | **Sharpe vs CDI:** `-0.07`
- **Giro e Custos:** Giro anual `769.47%` | Custo médio/ano `2.31%` | Custo total `32.78%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `299.53%` | CAGR `10.25%` | Vol `0.22%` | MaxDD `0.0%` | Sharpe `1.44`
  - `BOVA11`: Retorno `175.87%` | CAGR `7.41%` | Vol `23.67%` | MaxDD `-46.93%` | Sharpe `0.03`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (3409):** mín `-15.95%`, mediana `8.66%`, máx `50.89%`
- **Por ano calendário:** `{'2012': -0.51, '2013': -2.76, '2014': -2.34, '2015': 8.17, '2016': 5.97, '2017': 16.88, '2018': 2.89, '2019': 16.76, '2020': 25.37, '2021': -0.75, '2022': 1.13, '2023': 3.84, '2024': 15.86, '2025': 28.66, '2026': 7.05}`

### `dual_momentum_global (BRL, banda 25%)`
- **Janela:** `2013-01-11` a `2026-11-24` (`3567` barras, `13.87` anos) | **Universo completo desde:** `2013-01-11`
- **Métricas:** Retorno Total `306.3%` | **CAGR:** `10.64%` | **Volatilidade:** `20.4%` | **Drawdown Máx:** `-39.61%` | **Sharpe vs CDI:** `0.12`
- **Giro e Custos:** Giro anual `360.56%` | Custo médio/ano `0.54%` | Custo total `7.5%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `288.46%` | CAGR `10.28%` | Vol `0.23%` | MaxDD `0.0%` | Sharpe `1.39`
  - `BOVA11`: Retorno `169.78%` | CAGR `7.42%` | Vol `23.78%` | MaxDD `-46.93%` | Sharpe `0.02`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (3315):** mín `-22.93%`, mediana `11.3%`, máx `65.5%`
- **Por ano calendário:** `{'2013': 18.84, '2014': 19.41, '2015': 36.95, '2016': -8.76, '2017': 24.43, '2018': -6.37, '2019': 39.9, '2020': -18.13, '2021': 10.02, '2022': -6.66, '2023': 12.03, '2024': 38.02, '2025': 1.84, '2026': 6.16}`

### `risk_parity_simplified (BRL)`
- **Janela:** `2012-02-28` a `2026-11-24` (`3790` barras, `14.74` anos) | **Universo completo desde:** `2012-02-28`
- **Métricas:** Retorno Total `85.24%` | **CAGR:** `4.27%` | **Volatilidade:** `16.44%` | **Drawdown Máx:** `-51.18%` | **Sharpe vs CDI:** `-0.24`
- **Giro e Custos:** Giro anual `109.49%` | Custo médio/ano `0.33%` | Custo total `4.84%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `316.2%` | CAGR `10.16%` | Vol `0.22%` | MaxDD `0.0%` | Sharpe `1.43`
  - `BOVA11`: Retorno `150.28%` | CAGR `6.42%` | Vol `23.65%` | MaxDD `-46.93%` | Sharpe `-0.01`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (3538):** mín `-34.54%`, mediana `3.88%`, máx `49.22%`
- **Por ano calendário:** `{'2012': 6.26, '2013': -9.52, '2014': 24.38, '2015': -9.37, '2016': -0.99, '2017': -7.62, '2018': 8.26, '2019': 4.18, '2020': -20.67, '2021': 3.81, '2022': 3.29, '2023': 8.87, '2024': 28.0, '2025': 9.71, '2026': 27.41}`

### `radar_top_n (c/ cripto)`
- **Janela:** `2012-11-28` a `2026-11-24` (`3644` barras, `13.99` anos) | **Universo completo desde:** `2018-10-29`
- **Métricas:** Retorno Total `1091.26%` | **CAGR:** `19.38%` | **Volatilidade:** `19.84%` | **Drawdown Máx:** `-36.23%` | **Sharpe vs CDI:** `0.48`
- **Giro e Custos:** Giro anual `275.24%` | Custo médio/ano `0.83%` | Custo total `11.55%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `300.85%` | CAGR `10.44%` | Vol `0.23%` | MaxDD `0.0%` | Sharpe `1.46`
  - `BOVA11`: Retorno `193.12%` | CAGR `7.99%` | Vol `23.72%` | MaxDD `-46.93%` | Sharpe `0.05`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (3392):** mín `-23.65%`, mediana `11.75%`, máx `169.21%`
- **Por ano calendário:** `{'2012': 1.81, '2013': 16.27, '2014': 6.68, '2015': 1.02, '2016': 16.92, '2017': 111.87, '2018': -17.96, '2019': 5.76, '2020': 56.36, '2021': 89.73, '2022': -10.49, '2023': 25.91, '2024': 35.81, '2025': 3.69, '2026': -7.71}`

### `radar_top_n_sem_cripto`
- **Janela:** `2012-11-28` a `2026-11-24` (`3606` barras, `13.99` anos) | **Universo completo desde:** `2013-02-06`
- **Métricas:** Retorno Total `226.94%` | **CAGR:** `8.84%` | **Volatilidade:** `12.53%` | **Drawdown Máx:** `-20.69%` | **Sharpe vs CDI:** `-0.04`
- **Giro e Custos:** Giro anual `278.1%` | Custo médio/ano `0.83%` | Custo total `11.67%`
- **Benchmarks na mesma janela:**
  - `CDI`: Retorno `293.25%` | CAGR `10.28%` | Vol `0.23%` | MaxDD `0.0%` | Sharpe `1.43`
  - `BOVA11`: Retorno `193.12%` | CAGR `7.99%` | Vol `23.72%` | MaxDD `-46.93%` | Sharpe `0.05`
  - `IVVB11`: Retorno `1035.21%` | CAGR `21.32%` | Vol `19.77%` | MaxDD `-30.71%` | Sharpe `0.6`
- **Janelas móveis 12m (3354):** mín `-13.29%`, mediana `10.13%`, máx `39.32%`
- **Por ano calendário:** `{'2012': 1.81, '2013': 16.27, '2014': 6.85, '2015': -2.46, '2016': 0.85, '2017': 22.29, '2018': -4.83, '2019': 18.11, '2020': 15.03, '2021': 22.78, '2022': -8.99, '2023': 9.24, '2024': 11.47, '2025': 23.31, '2026': -0.97}`

## 3. Investigação do Giro Excessivo e Sensibilidade à Banda de Rebalanceamento (Bloco B)
- **Origem do giro excessivo:** no `trend_following_turtles` (~974%/ano sem banda), a reponderação semanal por `1/ATR` ajustava os pesos de todos os ativos todas as semanas mesmo sem mudança de sinal de tendência, somada a whipsaws semanais em `BTC-USD`/`PETR4`. No `dual_momentum_global` (~485%/ano sem banda), empates próximos entre os líderes de 12m causavam trocas integrais (100%) quase todo mês.
- **Regra implementada:** `rebalance_band_pct` (padrão `25.0%` relativo + ordem mínima `2.0%` para Turtles; margem relativa de momentum de `2.5 pp` para Dual Momentum quando `band=25%`).

### Sensibilidade — `trend_following_turtles` (com cripto)
| Banda (%) | CAGR (%) | Vol (%) | MaxDD (%) | Sharpe | Giro/ano (%) | Custo Total (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Sem banda (0%) | 11.88 | 12.56 | -18.47 | 0.17 | 891.16 | 37.96 |
| 10% | 11.85 | 12.52 | -18.14 | 0.16 | 866.16 | 36.89 |
| 25% | 12.28 | 12.47 | -18.06 | 0.19 | 815.79 | 34.75 |
| 50% | 12.12 | 12.26 | -17.28 | 0.18 | 726.42 | 30.94 |

### Sensibilidade — `dual_momentum_global` (BRL)
| Banda (%) | CAGR (%) | Vol (%) | MaxDD (%) | Sharpe | Giro/ano (%) | Custo Total (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Sem banda (0%) | 11.91 | 19.88 | -39.61 | 0.17 | 447.1 | 9.3 |
| 10% | 11.41 | 19.88 | -39.61 | 0.15 | 425.46 | 8.85 |
| 25% | 10.64 | 20.4 | -39.61 | 0.12 | 360.56 | 7.5 |
| 50% | 10.33 | 20.14 | -39.61 | 0.1 | 346.14 | 7.2 |

## 4. Rastreio Recente `radar_top_n`
- `2026-02-18: top5=['GLD', 'EEM', 'BOVA11.SA', 'EWZ', 'EWJ']`
- `2026-03-19: top5=['GLD', 'EWZ', 'BOVA11.SA', 'EEM', 'EWJ']`
- `2026-04-17: top5=['EWZ', 'DBC', 'GLD', 'BOVA11.SA', 'EEM']`
- `2026-05-18: top5=['EWZ', 'GLD', 'BOVA11.SA', 'EEM', 'DBC']`
- `2026-06-16: top5=['DBC', 'EEM', 'QQQ', 'EWZ', 'BOVA11.SA']`
- `2026-07-15: top5=['EEM', 'EWJ', 'EWZ', 'DBC', 'QQQ']`
- `2026-08-13: top5=['DBC', 'EEM', 'QQQ', 'EWJ', 'IVV']`
- `2026-09-11: top5=['DBC', 'EEM', 'EWJ', 'QQQ', 'VGK']`
- `2026-10-12: top5=['DBC', 'EWZ', 'EEM', 'EWJ', 'IVV']`
- `2026-11-10: top5=['DBC', 'IVV', 'VGK', 'SHY', 'VNQ']`
