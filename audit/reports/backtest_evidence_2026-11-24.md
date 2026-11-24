# Evidência Real de Backtests e Radar Global — 2026-11-24 07:26:27

## 1. Backtests Reais (Estratégias Baseadas em Preço)

### `indexacao_bogle`
- **Janela:** `2025-09-08` a `2026-11-23` (300 barras)
- **Ativo limitante:** `BOVA11`
- **Métricas:** Retorno Total `20.22%` | Volatilidade `6.58%` | Drawdown Máx `-4.92%` | Sharpe vs CDI `0.48`
- **Custos aplicados:** corretagem `5.0 bps`, slippage `10.0 bps`, execução `t+1`
- **Plausibilidade (D.3):** `OK (sem anomalias de look-ahead ou curva sem drawdown)`
- **Comparação com Benchmarks:**
  - `CDI` (CDI (BCB SGS Série 12), `total_return_cdi`): `17.11%`
  - `BOVA11` (BOVA11.SA (Ajustado), `total_return_adjusted`): `16.97%`
  - `IVVB11` (IVVB11.SA (Ajustado), `total_return_adjusted`): `22.77%`
  - `IBOV_PRICE` (Ibovespa ^BVSP (índice de preço, sem dividendos), `price_index_only`): `16.37%`

### `trend_following_turtles`
- **Janela:** `2026-06-23` a `2026-11-23` (105 barras)
- **Ativo limitante:** `BTC-USD`
- **Métricas:** Retorno Total `-1.26%` | Volatilidade `14.34%` | Drawdown Máx `-9.59%` | Sharpe vs CDI `-1.16`
- **Custos aplicados:** corretagem `5.0 bps`, slippage `10.0 bps`, execução `t+1`
- **Plausibilidade (D.3):** `OK (sem anomalias de look-ahead ou curva sem drawdown)`
- **Comparação com Benchmarks:**
  - `CDI` (CDI (BCB SGS Série 12), `total_return_cdi`): `5.5%`
  - `BOVA11` (BOVA11.SA (Ajustado), `total_return_adjusted`): `-3.48%`
  - `IVVB11` (IVVB11.SA (Ajustado), `total_return_adjusted`): `12.84%`
  - `IBOV_PRICE` (Ibovespa ^BVSP (índice de preço, sem dividendos), `price_index_only`): `-3.77%`

### `dual_momentum_global`
- **Janela:** `2026-06-17` a `2026-11-23` (91 barras)
- **Ativo limitante:** `IVV`
- **Métricas:** Retorno Total `-18.97%` | Volatilidade `34.1%` | Drawdown Máx `-25.52%` | Sharpe vs CDI `-1.71`
- **Custos aplicados:** corretagem `5.0 bps`, slippage `10.0 bps`, execução `t+1`
- **Plausibilidade (D.3):** `OK (sem anomalias de look-ahead ou curva sem drawdown)`
- **Comparação com Benchmarks:**
  - `CDI` (CDI (BCB SGS Série 12), `total_return_cdi`): `4.75%`
  - `BOVA11` (BOVA11.SA (Ajustado), `total_return_adjusted`): `-1.69%`
  - `IVVB11` (IVVB11.SA (Ajustado), `total_return_adjusted`): `13.52%`
  - `IBOV_PRICE` (Ibovespa ^BVSP (índice de preço, sem dividendos), `price_index_only`): `-2.17%`

### `risk_parity_simplified`
- **Janela:** `2025-09-19` a `2026-11-23` (286 barras)
- **Ativo limitante:** `IVV`
- **Métricas:** Retorno Total `11.11%` | Volatilidade `6.73%` | Drawdown Máx `-5.74%` | Sharpe vs CDI `-0.58`
- **Custos aplicados:** corretagem `5.0 bps`, slippage `10.0 bps`, execução `t+1`
- **Plausibilidade (D.3):** `OK (sem anomalias de look-ahead ou curva sem drawdown)`
- **Comparação com Benchmarks:**
  - `CDI` (CDI (BCB SGS Série 12), `total_return_cdi`): `16.26%`
  - `BOVA11` (BOVA11.SA (Ajustado), `total_return_adjusted`): `13.7%`
  - `IVVB11` (IVVB11.SA (Ajustado), `total_return_adjusted`): `22.02%`
  - `IBOV_PRICE` (Ibovespa ^BVSP (índice de preço, sem dividendos), `price_index_only`): `12.98%`

### `radar_top_n`
- **Janela:** `2026-10-15` a `2026-11-23` (26 barras)
- **Ativo limitante:** `BTC-USD`
- **Métricas:** Retorno Total `-15.38%` | Volatilidade `27.81%` | Drawdown Máx `-16.19%` | Sharpe vs CDI `-3.42`
- **Custos aplicados:** corretagem `5.0 bps`, slippage `10.0 bps`, execução `t+1`
- **Plausibilidade (D.3):** `OK (sem anomalias de look-ahead ou curva sem drawdown)`
- **Comparação com Benchmarks:**
  - `CDI` (CDI (BCB SGS Série 12), `total_return_cdi`): `1.28%`
  - `BOVA11` (BOVA11.SA (Ajustado), `total_return_adjusted`): `-19.39%`
  - `IVVB11` (IVVB11.SA (Ajustado), `total_return_adjusted`): `9.29%`
  - `IBOV_PRICE` (Ibovespa ^BVSP (índice de preço, sem dividendos), `price_index_only`): `-19.35%`

## 2. Radar Global com Dados Reais (D.4)

- **Regime atual:** `RISK-OFF` — `4 de 4 sinais disponíveis` (Risk-On: `1`, Risk-Off: `3`)
  - `Volatilidade Implícita (VIX)`: valor=`27.73 pts`, sinal=`RISK-OFF`, regra=`Convenção: < 18.0 Risk-On | > 25.0 Risk-Off`
  - `Curva de Juros EUA (10Y - 3M)`: valor=`0.77 pp (% a.a.)`, sinal=`RISK-ON`, regra=`Convenção: > +0.25 pp Risk-On | < -0.25 pp Risk-Off (^TNX e ^IRX em %)`
  - `Índice Dólar (DXY vs MM50/MM200)`: valor=`104.16 pts`, sinal=`RISK-OFF`, regra=`Convenção: DXY < MM50 Risk-On | DXY > MM50 e MM200 Risk-Off`
  - `Proxy Spread Crédito (HYG/IEF vs MM50)`: valor=`0.835 ratio`, sinal=`RISK-OFF`, regra=`Convenção: HYG/IEF > MM50 Risk-On | < MM50 Risk-Off`
- **Teste de unidades ^TNX e ^IRX:** `^TNX=4.918% a.a.`, `^IRX=4.147% a.a.`, `spread=0.77 pp` -> `PASS (valores em % a.a., não em pontos-base x10)`

### Top 5 Candidatos (A FAVOR e CONTRA)
- **DBC** (Invesco DB Commodity Index | Commodities | Score heurístico: `77.14`):
  - A FAVOR: MM50 acima da MM200 (estrutura de alta intermediária).
  - A FAVOR: Momentum 12-1 positivo de +55.41%.
  - A FAVOR: Força relativa de +21.07 pp frente ao benchmark global ACWI.
  - CONTRA: Preço abaixo da MM200 (tendência primária negativa).
  - CONTRA: Exposição cambial em USD (impostos e IOF não modelados).
  - CONTRA: Valuation manual indisponível (não verificado).
- **SHY** (iShares 1-3 Year Treasury | Renda Fixa | Score heurístico: `71.15`):
  - A FAVOR: Preço de fechamento acima da MM200 (tendência primária positiva).
  - A FAVOR: MM50 acima da MM200 (estrutura de alta intermediária).
  - A FAVOR: Momentum 12-1 positivo de +1.53%.
  - CONTRA: Desempenho inferior ao ACWI em 12m (-9.66 pp).
  - CONTRA: Exposição cambial em USD (impostos e IOF não modelados).
  - CONTRA: Valuation manual indisponível (não verificado).
- **EWJ** (iShares MSCI Japan | Japão | Score heurístico: `63.14`):
  - A FAVOR: MM50 acima da MM200 (estrutura de alta intermediária).
  - A FAVOR: Momentum 12-1 positivo de +23.48%.
  - A FAVOR: Força relativa de +2.43 pp frente ao benchmark global ACWI.
  - CONTRA: Preço abaixo da MM200 (tendência primária negativa).
  - CONTRA: Exposição cambial em USD (impostos e IOF não modelados).
  - CONTRA: Valuation manual indisponível (não verificado).
- **IVV** (iShares Core S&P 500 | Ações EUA | Score heurístico: `63.08`):
  - A FAVOR: MM50 acima da MM200 (estrutura de alta intermediária).
  - A FAVOR: Momentum 12-1 positivo de +17.77%.
  - A FAVOR: Força relativa de +0.34 pp frente ao benchmark global ACWI.
  - CONTRA: Preço abaixo da MM200 (tendência primária negativa).
  - CONTRA: Exposição cambial em USD (impostos e IOF não modelados).
  - CONTRA: Valuation manual indisponível (não verificado).
- **BOVA11.SA** (iShares Ibovespa B3 | Brasil | Score heurístico: `61.44`):
  - A FAVOR: MM50 acima da MM200 (estrutura de alta intermediária).
  - A FAVOR: Momentum 12-1 positivo de +32.06%.
  - CONTRA: Preço abaixo da MM200 (tendência primária negativa).
  - CONTRA: Desempenho inferior ao ACWI em 12m (-6.25 pp).
  - CONTRA: Drawdown máximo recente severo (-21.02%).
  - CONTRA: Valuation manual indisponível (não verificado).

### Resumo da Matriz de Correlação
- **Janela:** `126` pregões | **Ativos:** `0` | **Pares com |corr| >= 0.75:** `0`

## 3. Teste de Reconciliação Independente (`audit/tools/reconcile_backtests.py`)
- **`indexacao_bogle`:** motor `20.22%` vs independente `20.22%` | diferença `0.00 pp` → **PASS**
- **`trend_following_turtles`:** motor `-1.26%` vs independente `-1.25%` | diferença `0.01 pp` → **PASS**
- **Exit code:** `0`
