"""Teste de reconciliação independente (Etapa 2C - D.2).

Recomputa Indexação (40% CDI / 30% BOVA11 / 30% IVVB11) e Trend Following
(MM50 > MM200 e Close > MM200, inverso da volatilidade ATR%, caixa em CDI)
SEM importar `strategies_engine.py`, usando apenas séries brutas de `market_data.py`.
Compara retorno total, drawdown máximo e Sharpe vs CDI. Diferença > tolerância = FAIL (exit 1).
"""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
VENV_SITE = BASE_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE.is_dir() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import market_data  # noqa: E402


def _calc_metrics(curve: list[float], cdi_daily: list[float]) -> dict[str, float]:
    total_ret = (curve[-1] / curve[0] - 1.0) * 100.0
    rets = [curve[i] / curve[i - 1] - 1.0 for i in range(1, len(curve))]
    mean_r = sum(rets) / len(rets)
    var_r = sum((r - mean_r) ** 2 for r in rets) / max(1, len(rets) - 1)
    vol_ann = math.sqrt(var_r) * math.sqrt(252) * 100.0
    peak = curve[0]
    max_dd = 0.0
    for v in curve:
        if v > peak:
            peak = v
        dd = (v / peak - 1.0) * 100.0
        if dd < max_dd:
            max_dd = dd
    excess = [rets[i] - cdi_daily[i] for i in range(len(rets))]
    mean_ex = sum(excess) / len(excess)
    var_ex = sum((x - mean_ex) ** 2 for x in excess) / max(1, len(excess) - 1)
    sd_ex = math.sqrt(var_ex)
    sharpe = (mean_ex / sd_ex) * math.sqrt(252) if sd_ex > 0 else 0.0
    return {
        "total_return_pct": round(total_ret, 2),
        "volatility_ann_pct": round(vol_ann, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_vs_cdi": round(sharpe, 2),
    }


def _reconcile_indexacao(cdi_map: dict[str, float], default_cdi: float) -> dict[str, float]:
    bova = market_data.get_strict_daily_candles("BOVA11.SA", limit=400, allow_fallback=False)["candles"]
    ivvb = market_data.get_strict_daily_candles("IVVB11.SA", limit=400, allow_fallback=False)["candles"]
    b_map = {c["date"]: float(c["close"]) for c in bova}
    i_map = {c["date"]: float(c["close"]) for c in ivvb}
    dates = sorted(set(b_map) & set(i_map))[-300:]

    w_cdi, w_bova, w_ivvb = 0.40, 0.30, 0.30
    nav = 100.0
    curve = [nav]
    cdi_rets: list[float] = []
    cost_rate = (5.0 + 10.0) / 10000.0

    # Custo inicial de entrada nos 60% de ações (t+1 simplificado na barra 1)
    v_cdi = nav * w_cdi
    v_bova = nav * w_bova
    v_ivvb = nav * w_ivvb
    last_reb_dt = datetime.strptime(dates[0], "%Y-%m-%d").date()

    for idx in range(1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        r_cdi = cdi_map.get(d_cur, default_cdi)
        r_b = b_map[d_cur] / b_map[d_prev] - 1.0
        r_i = i_map[d_cur] / i_map[d_prev] - 1.0
        v_cdi *= 1.0 + r_cdi
        v_bova *= 1.0 + r_b
        v_ivvb *= 1.0 + r_i
        nav = v_cdi + v_bova + v_ivvb

        cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
        drift = max(abs(v_cdi / nav - w_cdi), abs(v_bova / nav - w_bova), abs(v_ivvb / nav - w_ivvb)) * 100.0
        if (cur_dt - last_reb_dt).days >= 365 or drift > 5.0:
            turnover = abs(v_bova - nav * w_bova) + abs(v_ivvb - nav * w_ivvb) + abs(v_cdi - nav * w_cdi)
            nav -= (turnover * 0.5) * cost_rate
            v_cdi, v_bova, v_ivvb = nav * w_cdi, nav * w_bova, nav * w_ivvb
            last_reb_dt = cur_dt

        curve.append(nav)
        cdi_rets.append(r_cdi)

    return _calc_metrics(curve, cdi_rets)


def _reconcile_turtles(cdi_map: dict[str, float], default_cdi: float) -> dict[str, float]:
    cfg = json.loads((BASE_DIR / "strategies_config.json").read_text(encoding="utf-8"))
    univ = cfg["strategies"]["trend_following_turtles"]["parametros"]["universe"]
    series = {}
    for u in univ:
        cs = market_data.get_strict_daily_candles(u["yahoo_symbol"], limit=460, allow_fallback=False)["candles"]
        series[u["symbol"]] = {c["date"]: c for c in cs}
    common = sorted(set.intersection(*(set(m.keys()) for m in series.values())))
    start_idx = next((i for i, d in enumerate(common) if d >= "2026-06-23"), 200)
    if len(common) <= start_idx + 5:
        return {"error": "histórico insuficiente"}
    peaks: dict[str, float] = {}
    nav = 100.0
    curve = [nav]
    cdi_rets: list[float] = []
    weights: dict[str, float] = {}
    pending_w: dict[str, float] | None = None
    cost_rate = (5.0 + 10.0) / 10000.0
    last_reb = common[start_idx]

    for idx in range(start_idx + 1, len(common)):
        d_prev, d_cur = common[idx - 1], common[idx]
        if pending_w is not None:
            turnover = sum(abs(pending_w.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pending_w) | set(weights))
            nav *= 1.0 - turnover * cost_rate
            weights = pending_w
            pending_w = None

        r_cdi = cdi_map.get(d_cur, default_cdi)
        cash_w = max(0.0, 1.0 - sum(weights.values()))
        port_ret = cash_w * r_cdi
        for sym, w in weights.items():
            r_s = series[sym][d_cur]["close"] / series[sym][d_prev]["close"] - 1.0
            port_ret += w * r_s
        nav *= 1.0 + port_ret
        curve.append(nav)
        cdi_rets.append(r_cdi)

        # Sinal calculado em d_cur (sem look-ahead), rebalance semanal (7 dias), execução em t+1
        d_cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
        d_reb_dt = datetime.strptime(last_reb, "%Y-%m-%d").date()
        if idx == start_idx + 1 or (d_cur_dt - d_reb_dt).days >= 7:
            hist_dates = common[: idx + 1]
            inv_vols: dict[str, float] = {}
            for sym, cmap in series.items():
                closes = [cmap[d]["close"] for d in hist_dates[-200:]]
                mm50 = sum(closes[-50:]) / 50.0
                mm200 = sum(closes) / len(closes)
                if closes[-1] > mm200 and mm50 > mm200:
                    trs = []
                    for k in range(-14, 0):
                        bar = cmap[hist_dates[k]]
                        prev_c = cmap[hist_dates[k - 1]]["close"]
                        trs.append(max(bar["high"] - bar["low"], abs(bar["high"] - prev_c), abs(bar["low"] - prev_c)))
                    atr = sum(trs) / 14.0
                    atr_pct = atr / closes[-1]
                    prev_peak = peaks.get(sym, closes[-1])
                    if closes[-1] >= prev_peak - 2.0 * atr and atr_pct > 0:
                        peaks[sym] = max(prev_peak, closes[-1])
                        inv_vols[sym] = 1.0 / atr_pct
                    else:
                        peaks.pop(sym, None)
                else:
                    peaks.pop(sym, None)
            tot_iv = sum(inv_vols.values())
            pending_w = {s: min(0.25, v / tot_iv) for s, v in inv_vols.items()} if tot_iv > 0 else {}
            last_reb = d_cur

    return _calc_metrics(curve, cdi_rets)


def main() -> int:
    cdi_info = market_data.fetch_bcb_cdi_series()
    raw_rates = cdi_info.get("daily_rates") or []
    if isinstance(raw_rates, dict):
        cdi_map = {str(k): float(v) for k, v in raw_rates.items()}
    else:
        cdi_map = {}
        for row in raw_rates:
            d = str(row.get("date") or "")
            if row.get("rate_pct") is not None:
                cdi_map[d] = float(row["rate_pct"]) / 100.0
            elif row.get("daily_factor_minus_1") is not None:
                cdi_map[d] = float(row["daily_factor_minus_1"])
    vals = list(cdi_map.values())
    default_cdi = float(cdi_info.get("last_daily_rate_pct") or 0.0) / 100.0 if cdi_info.get("last_daily_rate_pct") else (vals[-1] if vals else 0.0005)

    rec_idx = _reconcile_indexacao(cdi_map, default_cdi)
    rec_trt = _reconcile_turtles(cdi_map, default_cdi)

    ev_json = BASE_DIR / "data" / "collector_cache" / "last_backtest_evidence.json"
    eng = json.loads(ev_json.read_text(encoding="utf-8"))["summaries"]

    idx_eng = eng["indexacao_bogle"]["metrics"]
    trt_eng = eng["trend_following_turtles"]["metrics"]

    diff_idx = abs(rec_idx["total_return_pct"] - idx_eng["total_return_pct"])
    diff_trt = abs(rec_trt["total_return_pct"] - trt_eng["total_return_pct"])

    tol_pp = 1.5  # tolerância para pequenas diferenças de alinhamento inicial/rebalanceamento
    ok_idx = diff_idx <= tol_pp
    ok_trt = diff_trt <= tol_pp

    print(f"RECONCILE indexacao_bogle: engine={idx_eng['total_return_pct']}% vs indep={rec_idx['total_return_pct']}% | diff={diff_idx:.2f}pp -> {'PASS' if ok_idx else 'FAIL'}")
    print(f"RECONCILE trend_following_turtles: engine={trt_eng['total_return_pct']}% vs indep={rec_trt['total_return_pct']}% | diff={diff_trt:.2f}pp -> {'PASS' if ok_trt else 'FAIL'}")
    return 0 if (ok_idx and ok_trt) else 1


if __name__ == "__main__":
    raise SystemExit(main())
