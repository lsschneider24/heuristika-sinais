"""Backtests completos (12+ anos de histórico, >= 10 anos efetivos), bandas de rebalanceamento e sensibilidade (Etapa 2E - A e B).
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


def _fetch_15y(sym: str, yahoo_sym: str | None = None) -> dict[str, Any]:
    return market_data.get_strict_daily_candles(
        sym,
        yahoo_symbol=yahoo_sym or sym,
        limit=4500,
        allow_fallback=False,
        range_str="15y",
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

    rolling_12m = [(vals[i] / vals[i - 252] - 1.0) * 100.0 for i in range(252, len(vals))] if len(vals) > 252 else []
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
        "annual_cost_pct": round(total_cost_pct / years, 2),
        "calendar_years": cal_years,
        "rolling_12m": roll_summary,
    }


def _benchmark_metrics_on_window(
    dates: list[str],
    px_maps: dict[str, dict[str, float]],
    cdi_map: dict[str, float],
    default_cdi: float,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    # CDI curve on exact dates
    cdi_curve = [{"date": dates[0], "value": 100.0}]
    v = 100.0
    for d in dates[1:]:
        v *= 1.0 + cdi_map.get(d, default_cdi)
        cdi_curve.append({"date": d, "value": v})
    out["CDI"] = _compute_extended_metrics(cdi_curve, cdi_map, default_cdi, 0.0, 0.0)

    for key, sym in (("BOVA11", "BOVA11.SA"), ("IVVB11", "IVVB11.SA")):
        px = px_maps.get(sym) or {}
        sub_dates = [d for d in dates if d in px]
        if len(sub_dates) >= 2 and px[sub_dates[0]] > 0:
            base = px[sub_dates[0]]
            bm_curve = [{"date": d, "value": (px[d] / base) * 100.0} for d in sub_dates]
            out[key] = _compute_extended_metrics(bm_curve, cdi_map, default_cdi, 0.0, 0.0)
        else:
            out[key] = {"total_return_pct": "indisponível", "cagr_pct": "indisponível", "volatility_ann_pct": "indisponível", "max_drawdown_pct": "indisponível", "sharpe_vs_cdi": "indisponível"}
    return out


def _apply_rebalance_band(
    current_w: dict[str, float],
    target_w: dict[str, float],
    band_rel_pct: float,
    min_order_pct: float = 2.0,
) -> dict[str, float]:
    """Aplica banda de rebalanceamento e tamanho mínimo de ordem.
    - Se band_rel_pct <= 0: sem banda (rebalanceia sempre).
    - Só opera um ativo se: sinal de entrada/saída mudou (0 <-> >0) OU |target - current| / max(target, current) > band_rel_pct/100,
      e |delta| >= min_order_pct/100.
    """
    if band_rel_pct <= 0.0:
        return dict(target_w)
    band = band_rel_pct / 100.0
    min_ord = min_order_pct / 100.0
    new_w: dict[str, float] = {}
    for sym in set(current_w) | set(target_w):
        cw = current_w.get(sym, 0.0)
        tw = target_w.get(sym, 0.0)
        if (cw == 0.0 and tw > 0.0) or (cw > 0.0 and tw == 0.0):
            new_w[sym] = tw
        elif max(cw, tw) > 0 and abs(tw - cw) / max(cw, tw) > band and abs(tw - cw) >= min_ord:
            new_w[sym] = tw
        else:
            new_w[sym] = cw
    tot = sum(new_w.values())
    if tot > 1.0:
        new_w = {k: v / tot for k, v in new_w.items() if v > 0}
    else:
        new_w = {k: v for k, v in new_w.items() if v > 0}
    return new_w


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
            total_cost_pct += (t_val / nav) * cost_rate * 100.0
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
    band_rel_pct: float = 0.0,
) -> tuple[dict[str, Any], list[str]]:
    by_sym = {s: {c["date"]: c for c in raw_candles[s]} for s in symbols}
    all_dates = sorted(set().union(*(m.keys() for m in by_sym.values())))
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

    for idx in range(start_bt_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending_w is not None:
            turn = sum(abs(pending_w.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pending_w) | set(weights)) * 0.5
            if turn > 0:
                total_turnover += turn
                total_cost_pct += turn * 2.0 * cost_rate * 100.0
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
            raw_target = {s: min(0.25, v / tot_iv) for s, v in inv_vols.items()} if tot_iv > 0 else {}
            pending_w = _apply_rebalance_band(weights, raw_target, band_rel_pct, 2.0)
            last_reb = cur_dt

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    return m, bt_dates


def _run_dual_momentum_long(
    px_brl: dict[str, dict[str, float]],
    cdi_map: dict[str, float],
    default_cdi: float,
    cost_rate: float,
    band_rel_pct: float = 0.0,
) -> tuple[dict[str, Any], list[str]]:
    syms = list(px_brl.keys())
    all_dates = sorted(set().union(*(m.keys() for m in px_brl.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    cdi_idx = {dates[0]: 1.0}
    for i in range(1, len(dates)):
        cdi_idx[dates[i]] = cdi_idx[dates[i - 1]] * (1.0 + cdi_map.get(dates[i], default_cdi))

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
            moms = {"SELIC_CDI": cdi_12m}
            for s in syms:
                hd = hist_dates[s]
                if len(hd) >= 253 and d_cur in px_brl[s]:
                    moms[s] = (px_brl[s][d_cur] / px_brl[s][hd[-253]]) - 1.0
            best = max(moms, key=lambda k: moms[k])
            # Banda para Dual Momentum: só troca se o novo líder superar o atual por margem relativa >= band_rel_pct/100 * 10pp (ou se atual for negativo vs CDI)
            if band_rel_pct > 0 and current in moms and best != current and best != "SELIC_CDI" and current != "SELIC_CDI":
                margin = (band_rel_pct / 100.0) * 0.10  # ex: 25% -> 2.5 pp de folga sobre momentum atual
                if moms[best] - moms[current] <= margin:
                    best = current
            pending = best

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    return m, bt_dates


def _run_risk_parity_long(
    px_brl: dict[str, dict[str, float]],
    asset_classes: dict[str, str],
    cdi_map: dict[str, float],
    default_cdi: float,
    cost_rate: float,
) -> tuple[dict[str, Any], list[str]]:
    syms = list(px_brl.keys())
    all_dates = sorted(set().union(*(m.keys() for m in px_brl.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    hist_px: dict[str, list[float]] = {s: [] for s in syms}
    start_idx = None
    full_univ_date = None
    for i, d in enumerate(dates):
        ready = 0
        for s in syms:
            if d in px_brl[s]:
                hist_px[s].append(px_brl[s][d])
            if len(hist_px[s]) >= 64:
                ready += 1
        if ready >= 4 and start_idx is None:
            start_idx = i
        if ready == len(syms) and full_univ_date is None:
            full_univ_date = d

    nav = 100.0
    curve = [{"date": dates[start_idx], "value": nav}]
    weights: dict[str, float] = {}
    pending_w: dict[str, float] | None = None
    last_reb = datetime.strptime(dates[start_idx], "%Y-%m-%d").date()
    total_turnover = 0.0
    total_cost_pct = 0.0
    hist_px = {s: [px_brl[s][d] for d in dates[: start_idx + 1] if d in px_brl[s]] for s in syms}

    for idx in range(start_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending_w is not None:
            turn = sum(abs(pending_w.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pending_w) | set(weights)) * 0.5
            total_turnover += turn
            total_cost_pct += turn * 2.0 * cost_rate * 100.0
            nav *= 1.0 - turn * 2.0 * cost_rate
            weights = pending_w
            pending_w = None

        r_cdi = cdi_map.get(d_cur, default_cdi)
        cash_w = max(0.0, 1.0 - sum(weights.values()))
        port_ret = cash_w * r_cdi
        for s, w in weights.items():
            if d_cur in px_brl[s] and d_prev in px_brl[s]:
                port_ret += w * (px_brl[s][d_cur] / px_brl[s][d_prev] - 1.0)
            else:
                port_ret += w * r_cdi
        nav *= 1.0 + port_ret
        curve.append({"date": d_cur, "value": nav})

        for s in syms:
            if d_cur in px_brl[s]:
                hist_px[s].append(px_brl[s][d_cur])

        cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
        if idx == start_idx + 1 or (cur_dt - last_reb).days >= 90:
            inv_vols: dict[str, float] = {}
            for s in syms:
                p_list = hist_px[s]
                if len(p_list) >= 64 and d_cur in px_brl[s]:
                    rets = [p_list[k] / p_list[k - 1] - 1.0 for k in range(-63, 0)]
                    mu = sum(rets) / len(rets)
                    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)) * math.sqrt(252)
                    if sd > 0:
                        inv_vols[s] = 1.0 / sd
            tot_iv = sum(inv_vols.values())
            raw_w = {s: min(0.35, v / tot_iv) for s, v in inv_vols.items()} if tot_iv > 0 else {}
            # Cap por classe <= 50%
            cls_tot: dict[str, float] = {}
            for s, w in raw_w.items():
                c = asset_classes[s]
                cls_tot[c] = cls_tot.get(c, 0.0) + w
            for s in list(raw_w.keys()):
                c = asset_classes[s]
                if cls_tot[c] > 0.50:
                    raw_w[s] *= 0.50 / cls_tot[c]
            tot_w = sum(raw_w.values())
            if tot_w > 0:
                pending_w = {s: w / tot_w for s, w in raw_w.items()}
            last_reb = cur_dt

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    return m, bt_dates


def _run_radar_top_n_long(
    px_maps: dict[str, dict[str, float]],
    symbols: list[str],
    cdi_map: dict[str, float],
    default_cdi: float,
    cost_rate: float,
) -> tuple[dict[str, Any], list[str], list[str]]:
    all_dates = sorted(set().union(*(px_maps[s].keys() for s in symbols if s in px_maps)))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    hist_px: dict[str, list[float]] = {s: [] for s in symbols}
    start_idx = None
    full_univ_date = None
    for i, d in enumerate(dates):
        ready = 0
        for s in symbols:
            if d in px_maps.get(s, {}):
                hist_px[s].append(px_maps[s][d])
            if len(hist_px[s]) >= 253:
                ready += 1
        if ready >= 5 and start_idx is None:
            start_idx = i
        if ready == len(symbols) and full_univ_date is None:
            full_univ_date = d

    nav = 100.0
    curve = [{"date": dates[start_idx], "value": nav}]
    weights: dict[str, float] = {}
    pending_w: dict[str, float] | None = None
    total_turnover = 0.0
    total_cost_pct = 0.0
    trace: list[str] = []
    hist_px = {s: [px_maps[s][d] for d in dates[: start_idx + 1] if d in px_maps.get(s, {})] for s in symbols}

    for idx in range(start_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending_w is not None:
            turn = sum(abs(pending_w.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pending_w) | set(weights)) * 0.5
            total_turnover += turn
            total_cost_pct += turn * 2.0 * cost_rate * 100.0
            nav *= 1.0 - turn * 2.0 * cost_rate
            weights = pending_w
            pending_w = None

        r_cdi = cdi_map.get(d_cur, default_cdi)
        cash_w = max(0.0, 1.0 - sum(weights.values()))
        port_ret = cash_w * r_cdi
        for s, w in weights.items():
            if d_cur in px_maps[s] and d_prev in px_maps[s]:
                port_ret += w * (px_maps[s][d_cur] / px_maps[s][d_prev] - 1.0)
            else:
                port_ret += w * r_cdi
        nav *= 1.0 + port_ret
        curve.append({"date": d_cur, "value": nav})

        for s in symbols:
            if d_cur in px_maps.get(s, {}):
                hist_px[s].append(px_maps[s][d_cur])

        if idx == start_idx + 1 or (idx - start_idx) % 21 == 0:
            scores: dict[str, float] = {}
            for s in symbols:
                pl = hist_px[s]
                if len(pl) >= 253 and d_cur in px_maps.get(s, {}):
                    mom_12_1 = (pl[-22] / pl[-253]) - 1.0
                    mm200 = sum(pl[-200:]) / 200.0
                    trend = 1.0 if pl[-1] > mm200 else 0.0
                    rets = [pl[k] / pl[k - 1] - 1.0 for k in range(-63, 0)]
                    mu = sum(rets) / len(rets)
                    vol = math.sqrt(sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)) * math.sqrt(252)
                    scores[s] = mom_12_1 * 0.5 + trend * 0.3 - vol * 0.2
            top5 = sorted(scores, key=lambda k: scores[k], reverse=True)[:5]
            pending_w = {s: 0.20 for s in top5}
            if d_cur >= "2026-01-01":
                trace.append(f"{d_cur}: top5={top5}")

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    return m, bt_dates, trace[-10:]


def main() -> int:
    cdi_info = market_data.fetch_bcb_cdi_series(start_date="2011-11-24", allow_cache=False)
    cdi_map = {str(r["date"]): float(r["rate_pct"]) / 100.0 for r in cdi_info["daily_rates"]}
    default_cdi = float(cdi_info["last_daily_rate_pct"]) / 100.0
    cost_rate = 15.0 / 10000.0

    cfg = market_data.load_strategies_config()
    radar_univ = [u["symbol"] for u in cfg["global_radar"]["universe"]]
    rp_univ = cfg["strategies"]["risk_parity_simplified"]["parametros"]["universe"]
    turtles_all = ["BOVA11.SA", "IVVB11.SA", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA", "GC=F", "BTC-USD"]

    fetch_syms = sorted(set(["BOVA11.SA", "IVVB11.SA", "^BVSP", "USDBRL=X"] + turtles_all + radar_univ + [u["symbol"] for u in rp_univ]))
    raw_candles: dict[str, list[dict[str, Any]]] = {}
    px_maps: dict[str, dict[str, float]] = {}
    series_ranges: list[str] = []
    for s in fetch_syms:
        res = _fetch_15y(s)
        if res.get("status") == "ok" and res.get("candles"):
            cs = res["candles"]
            raw_candles[s] = cs
            px_maps[s] = {c["date"]: float(c["close"]) for c in cs}
            series_ranges.append(f"- `{s}`: `{cs[0]['date']}` a `{cs[-1]['date']}` ({len(cs)} barras)")

    fx = px_maps["USDBRL=X"]
    dm_brl = {
        sym: ({d: px_maps[sym][d] * fx[d] for d in px_maps[sym] if d in fx} if is_usd else px_maps[sym])
        for sym, is_usd in (("IVV", True), ("VGK", True), ("EEM", True), ("BOVA11.SA", False))
    }
    rp_brl = {
        u["symbol"]: ({d: px_maps[u["symbol"]][d] * fx[d] for d in px_maps[u["symbol"]] if d in fx} if u["currency"] == "USD" else px_maps[u["symbol"]])
        for u in rp_univ
    }
    rp_classes = {u["symbol"]: u["asset_class"] for u in rp_univ}

    # Executa todas as estratégias na janela longa (12+ anos)
    results: list[tuple[str, dict[str, Any], dict[str, dict[str, Any]]]] = []
    m_idx, d_idx = _run_indexacao_long(px_maps, cdi_map, default_cdi, cost_rate)
    results.append(("indexacao_bogle", m_idx, _benchmark_metrics_on_window(d_idx, px_maps, cdi_map, default_cdi)))

    m_trt, d_trt = _run_turtles_progressive(raw_candles, turtles_all, cdi_map, default_cdi, cost_rate, band_rel_pct=25.0)
    results.append(("trend_following_turtles (c/ cripto, banda 25%)", m_trt, _benchmark_metrics_on_window(d_trt, px_maps, cdi_map, default_cdi)))

    turtles_nc = [s for s in turtles_all if s != "BTC-USD"]
    m_trt_nc, d_trt_nc = _run_turtles_progressive(raw_candles, turtles_nc, cdi_map, default_cdi, cost_rate, band_rel_pct=25.0)
    results.append(("trend_following_turtles_sem_cripto (banda 25%)", m_trt_nc, _benchmark_metrics_on_window(d_trt_nc, px_maps, cdi_map, default_cdi)))

    m_dm, d_dm = _run_dual_momentum_long(dm_brl, cdi_map, default_cdi, cost_rate, band_rel_pct=25.0)
    results.append(("dual_momentum_global (BRL, banda 25%)", m_dm, _benchmark_metrics_on_window(d_dm, px_maps, cdi_map, default_cdi)))

    m_rp, d_rp = _run_risk_parity_long(rp_brl, rp_classes, cdi_map, default_cdi, cost_rate)
    results.append(("risk_parity_simplified (BRL)", m_rp, _benchmark_metrics_on_window(d_rp, px_maps, cdi_map, default_cdi)))

    m_rad, d_rad, tr_rad = _run_radar_top_n_long(px_maps, radar_univ, cdi_map, default_cdi, cost_rate)
    results.append(("radar_top_n (c/ cripto)", m_rad, _benchmark_metrics_on_window(d_rad, px_maps, cdi_map, default_cdi)))

    radar_nc = [s for s in radar_univ if s not in ("BTC-USD", "ETH-USD")]
    m_rad_nc, d_rad_nc, _ = _run_radar_top_n_long(px_maps, radar_nc, cdi_map, default_cdi, cost_rate)
    results.append(("radar_top_n_sem_cripto", m_rad_nc, _benchmark_metrics_on_window(d_rad_nc, px_maps, cdi_map, default_cdi)))

    # Sensibilidade da banda de rebalanceamento (0%, 10%, 25%, 50%)
    sens_trt = []
    sens_dm = []
    for b in (0.0, 10.0, 25.0, 50.0):
        mt, _ = _run_turtles_progressive(raw_candles, turtles_all, cdi_map, default_cdi, cost_rate, band_rel_pct=b)
        sens_trt.append((b, mt))
        md, _ = _run_dual_momentum_long(dm_brl, cdi_map, default_cdi, cost_rate, band_rel_pct=b)
        sens_dm.append((b, md))

    lines = [
        f"# Relatório Completo de Backtests em Janela Longa (12+ Anos) e Sensibilidade de Banda — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Datas Reais das Séries (Yahoo Finance `range=15y` + BCB SGS CDI)",
        f"- `CDI (BCB SGS Série 12)`: `{cdi_info['daily_rates'][0]['date']}` a `{cdi_info['daily_rates'][-1]['date']}` ({len(cdi_info['daily_rates'])} dias úteis)",
        *series_ranges,
        "",
        "## 2. Resultados Completos (Todas as Estratégias + Benchmarks na Mesma Janela)",
        "",
    ]

    for name, m, bms in results:
        lines.extend([
            f"### `{name}`",
            f"- **Janela:** `{m['start_date']}` a `{m['end_date']}` (`{m['bars']}` barras, `{m['years']}` anos) | **Universo completo desde:** `{m['full_universe_since']}`",
            f"- **Métricas:** Retorno Total `{m['total_return_pct']}%` | **CAGR:** `{m['cagr_pct']}%` | **Volatilidade:** `{m['volatility_ann_pct']}%` | **Drawdown Máx:** `{m['max_drawdown_pct']}%` | **Sharpe vs CDI:** `{m['sharpe_vs_cdi']}`",
            f"- **Giro e Custos:** Giro anual `{m['annual_turnover_pct']}%` | Custo médio/ano `{m['annual_cost_pct']}%` | Custo total `{m['total_cost_pct']}%`",
            f"- **Benchmarks na mesma janela:**",
        ])
        for bk in ("CDI", "BOVA11", "IVVB11"):
            bm = bms[bk]
            lines.append(
                f"  - `{bk}`: Retorno `{bm['total_return_pct']}%` | CAGR `{bm['cagr_pct']}%` | Vol `{bm['volatility_ann_pct']}%` | MaxDD `{bm['max_drawdown_pct']}%` | Sharpe `{bm['sharpe_vs_cdi']}`"
            )
        lines.append(f"- **Janelas móveis 12m ({m['rolling_12m']['count']}):** mín `{m['rolling_12m']['min_pct']}%`, mediana `{m['rolling_12m']['median_pct']}%`, máx `{m['rolling_12m']['max_pct']}%`")
        lines.append(f"- **Por ano calendário:** `{m['calendar_years']}`")
        lines.append("")

    lines.extend([
        "## 3. Investigação do Giro Excessivo e Sensibilidade à Banda de Rebalanceamento (Bloco B)",
        "- **Origem do giro excessivo:** no `trend_following_turtles` (~974%/ano sem banda), a reponderação semanal por `1/ATR` ajustava os pesos de todos os ativos todas as semanas mesmo sem mudança de sinal de tendência, somada a whipsaws semanais em `BTC-USD`/`PETR4`. No `dual_momentum_global` (~485%/ano sem banda), empates próximos entre os líderes de 12m causavam trocas integrais (100%) quase todo mês.",
        "- **Regra implementada:** `rebalance_band_pct` (padrão `25.0%` relativo + ordem mínima `2.0%` para Turtles; margem relativa de momentum de `2.5 pp` para Dual Momentum quando `band=25%`).",
        "",
        "### Sensibilidade — `trend_following_turtles` (com cripto)",
        "| Banda (%) | CAGR (%) | Vol (%) | MaxDD (%) | Sharpe | Giro/ano (%) | Custo Total (%) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for b, mt in sens_trt:
        lbl = "Sem banda (0%)" if b == 0 else f"{int(b)}%"
        lines.append(f"| {lbl} | {mt['cagr_pct']} | {mt['volatility_ann_pct']} | {mt['max_drawdown_pct']} | {mt['sharpe_vs_cdi']} | {mt['annual_turnover_pct']} | {mt['total_cost_pct']} |")

    lines.extend([
        "",
        "### Sensibilidade — `dual_momentum_global` (BRL)",
        "| Banda (%) | CAGR (%) | Vol (%) | MaxDD (%) | Sharpe | Giro/ano (%) | Custo Total (%) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for b, md in sens_dm:
        lbl = "Sem banda (0%)" if b == 0 else f"{int(b)}%"
        lines.append(f"| {lbl} | {md['cagr_pct']} | {md['volatility_ann_pct']} | {md['max_drawdown_pct']} | {md['sharpe_vs_cdi']} | {md['annual_turnover_pct']} | {md['total_cost_pct']} |")

    lines.extend([
        "",
        "## 4. Rastreio Recente `radar_top_n`",
        *[f"- `{x}`" for x in tr_rad],
    ])

    out_path = BASE_DIR / "audit" / "reports" / "backtest_long_2026-11-24.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"LONG_REPORT={out_path}")
    for name, m, _ in results:
        print(f"STRAT {name}: {m['start_date']}..{m['end_date']} ({m['years']}y) cagr={m['cagr_pct']}% vol={m['volatility_ann_pct']}% dd={m['max_drawdown_pct']}% sharpe={m['sharpe_vs_cdi']} turn={m['annual_turnover_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
