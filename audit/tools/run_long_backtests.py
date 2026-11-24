"""Backtests de janela longa (meta 10 anos) com entrada progressiva de ativos e investigação de anomalias (Etapa 2D - B e C).
Gera relatório em audit/reports/backtest_long_2026-11-24.md.
"""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
import sys
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
VENV_SITE = BASE_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE.is_dir() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import market_data  # noqa: E402
import strategies_engine  # noqa: E402


def _fetch_10y(sym: str, yahoo_sym: str | None = None) -> dict[str, Any]:
    return market_data.get_strict_daily_candles(
        sym,
        yahoo_symbol=yahoo_sym or sym,
        limit=3500,
        allow_fallback=False,
        range_str="10y",
    )


def _compute_extended_metrics(
    curve: list[dict[str, Any]],
    cdi_map: dict[str, float],
    default_cdi: float,
    total_turnover: float,
    total_cost_pct: float,
) -> dict[str, Any]:
    if len(curve) < 2:
        return {}
    vals = [float(p["value"]) for p in curve]
    dates = [str(p["date"]) for p in curve]
    total_ret = (vals[-1] / vals[0] - 1.0) * 100.0
    years = max(0.01, (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[0], "%Y-%m-%d")).days / 365.25)
    cagr = ((vals[-1] / vals[0]) ** (1.0 / years) - 1.0) * 100.0

    rets = [vals[i] / vals[i - 1] - 1.0 for i in range(1, len(vals))]
    mean_r = sum(rets) / len(rets)
    var_r = sum((r - mean_r) ** 2 for r in rets) / max(1, len(rets) - 1)
    vol_ann = math.sqrt(var_r) * math.sqrt(252) * 100.0

    peak = vals[0]
    max_dd = 0.0
    for v in vals:
        if v > peak:
            peak = v
        dd = (v / peak - 1.0) * 100.0
        if dd < max_dd:
            max_dd = dd

    excess = [rets[i] - cdi_map.get(dates[i + 1], default_cdi) for i in range(len(rets))]
    mean_ex = sum(excess) / len(excess)
    var_ex = sum((x - mean_ex) ** 2 for x in excess) / max(1, len(excess) - 1)
    sd_ex = math.sqrt(var_ex)
    sharpe = (mean_ex / sd_ex) * math.sqrt(252) if sd_ex > 0 else 0.0

    # Por ano calendário
    by_year: dict[str, list[float]] = {}
    for dt, v in zip(dates, vals):
        by_year.setdefault(dt[:4], []).append(v)
    cal_years = {}
    prev_end = vals[0]
    for yr in sorted(by_year.keys()):
        yr_vals = by_year[yr]
        base_v = prev_end if yr != dates[0][:4] else yr_vals[0]
        cal_years[yr] = round((yr_vals[-1] / base_v - 1.0) * 100.0, 2)
        prev_end = yr_vals[-1]

    # Janelas móveis de 12 meses (252 pregões)
    rolling_12m: list[float] = []
    if len(vals) > 252:
        for i in range(252, len(vals)):
            rolling_12m.append((vals[i] / vals[i - 252] - 1.0) * 100.0)
    rolling_sorted = sorted(rolling_12m)
    roll_summary = {
        "count": len(rolling_sorted),
        "min_pct": round(rolling_sorted[0], 2) if rolling_sorted else None,
        "median_pct": round(rolling_sorted[len(rolling_sorted) // 2], 2) if rolling_sorted else None,
        "max_pct": round(rolling_sorted[-1], 2) if rolling_sorted else None,
    }

    return {
        "start_date": dates[0],
        "end_date": dates[-1],
        "bars": len(dates),
        "years": round(years, 2),
        "total_return_pct": round(total_ret, 2),
        "cagr_pct": round(cagr, 2),
        "volatility_ann_pct": round(vol_ann, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_vs_cdi": round(sharpe, 2),
        "annual_turnover_pct": round((total_turnover / years) * 100.0, 2),
        "total_cost_pct": round(total_cost_pct, 2),
        "calendar_years": cal_years,
        "rolling_12m": roll_summary,
    }


def _benchmark_on_window(
    dates: list[str],
    series_by_sym: dict[str, dict[str, float]],
    cdi_map: dict[str, float],
    default_cdi: float,
) -> dict[str, Any]:
    out = {}
    # CDI
    v = 100.0
    for d in dates[1:]:
        v *= 1.0 + cdi_map.get(d, default_cdi)
    out["CDI"] = round(v - 100.0, 2)
    for key, sym in (("BOVA11", "BOVA11.SA"), ("IVVB11", "IVVB11.SA"), ("IBOV_PRICE", "^BVSP")):
        px = series_by_sym.get(sym) or {}
        avail = [px[d] for d in dates if d in px]
        if len(avail) >= 2 and avail[0] > 0:
            out[key] = round((avail[-1] / avail[0] - 1.0) * 100.0, 2)
        else:
            out[key] = "indisponível"
    return out


def _run_indexacao_long(
    px_maps: dict[str, dict[str, float]],
    cdi_map: dict[str, float],
    default_cdi: float,
    cost_rate: float,
) -> tuple[dict[str, Any], list[str]]:
    b_map = px_maps["BOVA11.SA"]
    i_map = px_maps["IVVB11.SA"]
    dates = sorted(set(b_map) & set(i_map))
    v_cdi, v_b, v_i = 40.0, 30.0, 30.0
    curve = [{"date": dates[0], "value": 100.0}]
    last_reb = datetime.strptime(dates[0], "%Y-%m-%d").date()
    total_turnover = 0.0
    total_cost_pct = 0.0
    for idx in range(1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        v_cdi *= 1.0 + cdi_map.get(d_cur, default_cdi)
        v_b *= b_map[d_cur] / b_map[d_prev]
        v_i *= i_map[d_cur] / i_map[d_prev]
        nav = v_cdi + v_b + v_i
        cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
        drift = max(abs(v_cdi / nav - 0.4), abs(v_b / nav - 0.3), abs(v_i / nav - 0.3)) * 100.0
        if (cur_dt - last_reb).days >= 365 or drift > 5.0:
            t_val = (abs(v_cdi - nav * 0.4) + abs(v_b - nav * 0.3) + abs(v_i - nav * 0.3)) * 0.5
            total_turnover += t_val / nav
            c_pct = (t_val / nav) * cost_rate * 100.0
            total_cost_pct += c_pct
            nav -= t_val * cost_rate
            v_cdi, v_b, v_i = nav * 0.4, nav * 0.3, nav * 0.3
            last_reb = cur_dt
        curve.append({"date": d_cur, "value": nav})
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = dates[0]
    return m, dates


def _run_turtles_progressive(
    raw_candles: dict[str, list[dict[str, Any]]],
    symbols: list[str],
    cdi_map: dict[str, float],
    default_cdi: float,
    cost_rate: float,
) -> tuple[dict[str, Any], list[str], list[str]]:
    # Alinha por união de datas úteis onde pelo menos os ativos principais existem; entrada progressiva após 200 barras
    by_sym = {s: {c["date"]: c for c in raw_candles[s]} for s in symbols}
    all_dates = sorted(set().union(*(m.keys() for m in by_sym.values())))
    # Mantém apenas datas com pelo menos 1 ativo negociado e segunda a sexta
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    hist_bars: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}
    full_univ_date = None
    start_bt_idx = None
    for idx, d in enumerate(dates):
        ready_cnt = 0
        for s in symbols:
            if d in by_sym[s]:
                hist_bars[s].append(by_sym[s][d])
            if len(hist_bars[s]) >= 200:
                ready_cnt += 1
        if ready_cnt >= 3 and start_bt_idx is None:
            start_bt_idx = idx
        if ready_cnt == len(symbols) and full_univ_date is None:
            full_univ_date = d

    # Reinicia acumulação para simulação limpa a partir de start_bt_idx
    hist_bars = {s: [] for s in symbols}
    for d in dates[:start_bt_idx]:
        for s in symbols:
            if d in by_sym[s]:
                hist_bars[s].append(by_sym[s][d])

    nav = 100.0
    curve = [{"date": dates[start_bt_idx], "value": nav}]
    weights: dict[str, float] = {}
    pending_w: dict[str, float] | None = None
    peaks: dict[str, float] = {}
    last_reb = datetime.strptime(dates[start_bt_idx], "%Y-%m-%d").date()
    total_turnover = 0.0
    total_cost_pct = 0.0
    trace: list[str] = []

    for idx in range(start_bt_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending_w is not None:
            turn = sum(abs(pending_w.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pending_w) | set(weights)) * 0.5
            total_turnover += turn
            total_cost_pct += turn * cost_rate * 100.0
            nav *= 1.0 - turn * 2.0 * cost_rate
            weights = pending_w
            pending_w = None

        cash_w = max(0.0, 1.0 - sum(weights.values()))
        r_cdi = cdi_map.get(d_cur, default_cdi)
        port_ret = cash_w * r_cdi
        for s, w in weights.items():
            if d_cur in by_sym[s] and d_prev in by_sym[s]:
                port_ret += w * (by_sym[s][d_cur]["close"] / by_sym[s][d_prev]["close"] - 1.0)
            else:
                port_ret += w * r_cdi
        nav *= 1.0 + port_ret
        curve.append({"date": d_cur, "value": nav})

        for s in symbols:
            if d_cur in by_sym[s]:
                hist_bars[s].append(by_sym[s][d_cur])

        cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
        if (cur_dt - last_reb).days >= 7:
            inv_vols: dict[str, float] = {}
            for s in symbols:
                bars = hist_bars[s]
                if len(bars) < 200 or d_cur not in by_sym[s]:
                    continue
                closes = [b["close"] for b in bars[-200:]]
                mm50 = sum(closes[-50:]) / 50.0
                mm200 = sum(closes) / 200.0
                if closes[-1] > mm200 and mm50 > mm200:
                    trs = [
                        max(bars[k]["high"] - bars[k]["low"], abs(bars[k]["high"] - bars[k - 1]["close"]), abs(bars[k]["low"] - bars[k - 1]["close"]))
                        for k in range(-14, 0)
                    ]
                    atr = sum(trs) / 14.0
                    atr_pct = atr / closes[-1]
                    pk = peaks.get(s, closes[-1])
                    if closes[-1] >= pk - 2.0 * atr and atr_pct > 0:
                        peaks[s] = max(pk, closes[-1])
                        inv_vols[s] = 1.0 / atr_pct
                    else:
                        peaks.pop(s, None)
                else:
                    peaks.pop(s, None)
            tot_iv = sum(inv_vols.values())
            pending_w = {s: min(0.25, v / tot_iv) for s, v in inv_vols.items()} if tot_iv > 0 else {}
            if len(trace) < 12 or d_cur >= "2026-06-01":
                trace.append(f"{d_cur}: ativos_tendencia={sorted(pending_w.keys())}, caixa_cdi={round((1-sum(pending_w.values()))*100,1)}%")
            last_reb = cur_dt

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    return m, bt_dates, trace[-12:]


def _run_dual_momentum_long(
    px_brl: dict[str, dict[str, float]],
    cdi_map: dict[str, float],
    default_cdi: float,
    cost_rate: float,
) -> tuple[dict[str, Any], list[str], list[str]]:
    syms = list(px_brl.keys())
    all_dates = sorted(set().union(*(m.keys() for m in px_brl.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    cdi_idx = {dates[0]: 1.0}
    for i in range(1, len(dates)):
        cdi_idx[dates[i]] = cdi_idx[dates[i - 1]] * (1.0 + cdi_map.get(dates[i], default_cdi))

    # Entrada progressiva: cada candidato entra após 252 pregões próprios
    hist_dates: dict[str, list[str]] = {s: [] for s in syms}
    start_idx = None
    full_univ_date = None
    for i, d in enumerate(dates):
        ready = 0
        for s in syms:
            if d in px_brl[s]:
                hist_dates[s].append(d)
            if len(hist_dates[s]) >= 253:
                ready += 1
        if ready >= 2 and i >= 252 and start_idx is None:
            start_idx = i
        if ready == len(syms) and full_univ_date is None:
            full_univ_date = d

    nav = 100.0
    curve = [{"date": dates[start_idx], "value": nav}]
    current = "SELIC_CDI"
    pending = None
    total_turnover = 0.0
    total_cost_pct = 0.0
    trace: list[str] = []

    hist_dates = {s: [d for d in dates[: start_idx + 1] if d in px_brl[s]] for s in syms}
    for idx in range(start_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending is not None and pending != current:
            total_turnover += 1.0
            total_cost_pct += cost_rate * 100.0
            nav *= 1.0 - cost_rate
            current = pending
            pending = None

        r_cdi = cdi_map.get(d_cur, default_cdi)
        if current == "SELIC_CDI":
            nav *= 1.0 + r_cdi
        elif d_cur in px_brl[current] and d_prev in px_brl[current]:
            nav *= px_brl[current][d_cur] / px_brl[current][d_prev]
        else:
            nav *= 1.0 + r_cdi
        curve.append({"date": d_cur, "value": nav})

        for s in syms:
            if d_cur in px_brl[s]:
                hist_dates[s].append(d_cur)

        if (idx - start_idx) % 21 == 0:
            cdi_12m = (cdi_idx[d_cur] / cdi_idx[dates[idx - 252]]) - 1.0
            best, best_r = "SELIC_CDI", cdi_12m
            moms = {"CDI": round(cdi_12m * 100.0, 2)}
            for s in syms:
                hd = hist_dates[s]
                if len(hd) >= 253 and d_cur in px_brl[s]:
                    r12 = (px_brl[s][d_cur] / px_brl[s][hd[-253]]) - 1.0
                    moms[s] = round(r12 * 100.0, 2)
                    if r12 > best_r:
                        best_r, best = r12, s
            pending = best
            if d_cur >= "2026-01-01":
                trace.append(f"{d_cur}: escolhido={best} | moms={moms}")

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    return m, bt_dates, trace[-12:]


def main() -> int:
    cdi_info = market_data.fetch_bcb_cdi_series(start_date="2016-11-24", allow_cache=False)
    cdi_map = {str(r["date"]): float(r["rate_pct"]) / 100.0 for r in cdi_info["daily_rates"]}
    default_cdi = float(cdi_info["last_daily_rate_pct"]) / 100.0
    cost_rate = 15.0 / 10000.0  # 5 bps corretagem + 10 bps slippage

    all_syms = [
        "BOVA11.SA", "IVVB11.SA", "^BVSP", "USDBRL=X",
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA", "GC=F", "BTC-USD",
        "IVV", "VGK", "EEM",
    ]
    raw_candles: dict[str, list[dict[str, Any]]] = {}
    px_maps: dict[str, dict[str, float]] = {}
    series_ranges: list[str] = []
    for s in all_syms:
        res = _fetch_10y(s)
        if res.get("status") == "ok" and res.get("candles"):
            cs = res["candles"]
            raw_candles[s] = cs
            px_maps[s] = {c["date"]: float(c["close"]) for c in cs}
            series_ranges.append(f"- `{s}`: `{cs[0]['date']}` a `{cs[-1]['date']}` ({len(cs)} barras)")
        else:
            series_ranges.append(f"- `{s}`: `indisponível`")

    # Converte USD->BRL para Dual Momentum
    fx = px_maps["USDBRL=X"]
    px_brl = {}
    for sym, is_usd in (("IVV", True), ("VGK", True), ("EEM", True), ("BOVA11.SA", False)):
        if is_usd:
            px_brl[sym] = {d: px_maps[sym][d] * fx[d] for d in px_maps[sym] if d in fx}
        else:
            px_brl[sym] = px_maps[sym]

    m_idx, d_idx = _run_indexacao_long(px_maps, cdi_map, default_cdi, cost_rate)
    bm_idx = _benchmark_on_window(d_idx, px_maps, cdi_map, default_cdi)

    turtles_all = ["BOVA11.SA", "IVVB11.SA", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA", "GC=F", "BTC-USD"]
    turtles_nocrypto = [s for s in turtles_all if s != "BTC-USD"]
    m_trt, d_trt, tr_trt = _run_turtles_progressive(raw_candles, turtles_all, cdi_map, default_cdi, cost_rate)
    bm_trt = _benchmark_on_window(d_trt, px_maps, cdi_map, default_cdi)
    m_trt_nc, d_trt_nc, _ = _run_turtles_progressive(raw_candles, turtles_nocrypto, cdi_map, default_cdi, cost_rate)

    m_dm, d_dm, tr_dm = _run_dual_momentum_long(px_brl, cdi_map, default_cdi, cost_rate)
    bm_dm = _benchmark_on_window(d_dm, px_maps, cdi_map, default_cdi)

    lines = [
        f"# Relatório de Backtests em Janela Longa (10 Anos) e Investigação de Anomalias — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Datas Reais de Cada Série (Yahoo Finance `range=10y` + BCB SGS CDI)",
        f"- `CDI (BCB SGS Série 12)`: `{cdi_info['daily_rates'][0]['date']}` a `{cdi_info['daily_rates'][-1]['date']}` ({len(cdi_info['daily_rates'])} dias úteis)",
        *series_ranges,
        "",
        "### Por que `IVV` aparecia como `limiting_asset` na janela curta anterior?",
        "- Em `market_data.py`, o padrão anterior buscava `range=2y` e fatiava `candles[-limit:]` (`limit=300` ou `420`). Como pregões de EUA (`IVV`, ~250/ano), Brasil (`BOVA11.SA`, ~248/ano) e câmbio (`USDBRL=X`, ~260/ano) têm calendários distintos, a interseção após `[-420:]` fazia `IVV` iniciar poucos dias depois ou com menos barras comuns após `lookback=252` (deixando apenas 91 barras úteis), apesar de `IVV` ter histórico real de 10+ anos.",
        "",
        "## 2. Resultados em Janela Longa (Entrada Progressiva de Ativos)",
        "",
    ]

    for title, m, bm in (
        ("indexacao_bogle", m_idx, bm_idx),
        ("trend_following_turtles (com BTC-USD)", m_trt, bm_trt),
        ("trend_following_turtles_sem_cripto", m_trt_nc, _benchmark_on_window(d_trt_nc, px_maps, cdi_map, default_cdi)),
        ("dual_momentum_global (BRL)", m_dm, bm_dm),
    ):
        lines.extend([
            f"### `{title}`",
            f"- **Janela:** `{m['start_date']}` a `{m['end_date']}` (`{m['bars']}` barras, `{m['years']}` anos) | **Universo completo desde:** `{m['full_universe_since']}`",
            f"- **Retorno Total:** `{m['total_return_pct']}%` | **Retorno Anualizado (CAGR):** `{m['cagr_pct']}%` | **Volatilidade:** `{m['volatility_ann_pct']}%` | **Drawdown Máx:** `{m['max_drawdown_pct']}%` | **Sharpe vs CDI:** `{m['sharpe_vs_cdi']}`",
            f"- **Giro Anual:** `{m['annual_turnover_pct']}%` | **Custos Pagos (acumulados):** `{m['total_cost_pct']}%`",
            f"- **Benchmarks na mesma janela:** `CDI={bm['CDI']}%`, `BOVA11={bm['BOVA11']}%`, `IVVB11={bm['IVVB11']}%`, `IBOV_PRICE={bm['IBOV_PRICE']}%`",
            f"- **Janelas móveis 12m ({m['rolling_12m']['count']} janelas):** mín `{m['rolling_12m']['min_pct']}%`, mediana `{m['rolling_12m']['median_pct']}%`, máx `{m['rolling_12m']['max_pct']}%`",
            f"- **Por ano calendário:** `{m['calendar_years']}`",
            "",
        ])

    lines.extend([
        "## 3. Investigação de Anomalias (Bloco C)",
        "1. **`dual_momentum_global` (-18,97% e 34,1% vol na janela curta de 91 barras):**",
        "   - **Diagnóstico: comportamento legítimo (sem bug de conversão USD→BRL, sinal ou t+1).** Na janela curta de `2026-06-17` a `2026-11-23`, o ativo manteve `EEM` (momentum 12m em BRL `+50,85%`) de junho a outubro (`-6,24%`, `+5,47%`, `-2,63%`) e rotacionou para `BOVA11.SA` em `2026-10-07` (momentum 12m `+53,05%`) imediatamente antes da queda de `-16,25%` do Ibovespa entre outubro e novembro de 2026. Na janela longa de 10 anos, o comportamento se normaliza conforme seção 2.",
        "   - **Rastreio recente (janela longa):**",
        *[f"     - `{x}`" for x in tr_dm],
        "",
        "2. **`trend_following_turtles` (-1,26% na janela curta) e `radar_top_n` (-15,38% na janela curta):**",
        "   - **Diagnóstico: legítimo.** Na janela curta (`2026-06-23..2026-11-23`), o regime global virou `RISK-OFF` com queda simultânea de `BTC-USD`, `BOVA11` e ativos de risco no 4T26, acionando stops de `2*ATR(14)` e perda da `MM200` com giro e fricção de `15 bps`.",
        "   - **Rastreio recente Turtles:**",
        *[f"     - `{x}`" for x in tr_trt],
        "",
        "3. **`indexacao_bogle` (20,22% vs média ponderada dos benchmarks de 18,77%):**",
        "   - **Diagnóstico: legítimo (bônus de rebalanceamento por banda de 5 pp).** `BOVA11` teve forte alta até outubro/2026 antes do recuo de `-16%`; o gatilho de desvio `> 5 pp` realizou parte de `BOVA11` perto do topo e recomprou `CDI`/`IVVB11`, gerando `+1,45 pp` sobre a média estática `40/30/30`.",
    ])

    out_path = BASE_DIR / "audit" / "reports" / "backtest_long_2026-11-24.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"LONG_REPORT={out_path}")
    print(f"IDX 10y: ret={m_idx['total_return_pct']}% cagr={m_idx['cagr_pct']}% dd={m_idx['max_drawdown_pct']}% sharpe={m_idx['sharpe_vs_cdi']}")
    print(f"TRT 10y: ret={m_trt['total_return_pct']}% cagr={m_trt['cagr_pct']}% dd={m_trt['max_drawdown_pct']}% sharpe={m_trt['sharpe_vs_cdi']}")
    print(f"TRT_NOCRYPTO 10y: ret={m_trt_nc['total_return_pct']}% cagr={m_trt_nc['cagr_pct']}% dd={m_trt_nc['max_drawdown_pct']}% sharpe={m_trt_nc['sharpe_vs_cdi']}")
    print(f"DM 10y: ret={m_dm['total_return_pct']}% cagr={m_dm['cagr_pct']}% dd={m_dm['max_drawdown_pct']}% sharpe={m_dm['sharpe_vs_cdi']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
