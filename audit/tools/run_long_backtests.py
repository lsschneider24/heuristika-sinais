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

import calendar_fill  # noqa: E402
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
    rolling_36m = [((vals[i] / vals[i - 756]) ** (1.0 / 3.0) - 1.0) * 100.0 for i in range(756, len(vals))] if len(vals) > 756 else []
    r36_sorted = sorted(rolling_36m)
    roll36_summary = {
        "count": len(r36_sorted),
        "min_ann_pct": round(r36_sorted[0], 2) if r36_sorted else None,
        "median_ann_pct": round(r36_sorted[len(r36_sorted) // 2], 2) if r36_sorted else None,
        "max_ann_pct": round(r36_sorted[-1], 2) if r36_sorted else None,
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
        "rolling_36m_ann": roll36_summary,
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
    dates = sorted(d for d in (set(b_map) | set(i_map)) if datetime.strptime(d, "%Y-%m-%d").weekday() < 5 and d >= max(min(b_map), min(i_map)))
    _f, _ = calendar_fill.ffill_price_maps({"B": b_map, "I": i_map}, dates)
    b_map, i_map = _f["B"], _f["I"]
    dates = [d for d in dates if d in b_map and d in i_map]
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
    variant: str = "A",
    max_fill: int = calendar_fill.DEFAULT_MAX_FILL,
) -> tuple[dict[str, Any], list[str]]:
    """Variantes autorizadas (Etapa 3): A=semanal (controle); B=mensal (21 pregões);
    C=semanal com reentrada após stop 2xATR somente após novo máximo de 55 dias."""
    by_sym = {s: {c["date"]: c for c in raw_candles[s]} for s in symbols}
    all_dates = sorted(set().union(*(m.keys() for m in by_sym.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]
    by_sym, ffill_log = calendar_fill.ffill_candle_maps(by_sym, dates, max_fill)

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
    stopped: dict[str, bool] = {}
    turn_events: list[tuple[str, float]] = []
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
                turn_events.append((d_cur, turn))
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
        check_now = ((idx - start_bt_idx) % 21 == 0) if variant == "B" else ((cur_dt - last_reb).days >= 7)
        if check_now:
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
                    if variant == "C" and stopped.get(s):
                        if closes[-1] >= max(closes[-55:]):
                            stopped.pop(s, None)
                        else:
                            continue
                    pk = peaks.get(s, closes[-1])
                    if closes[-1] >= pk - 2.0 * atr and atr_pct > 0:
                        peaks[s] = max(pk, closes[-1])
                        inv_vols[s] = 1.0 / atr_pct
                    else:
                        peaks.pop(s, None)
                        if variant == "C":
                            stopped[s] = True
                else:
                    peaks.pop(s, None)
            tot_iv = sum(inv_vols.values())
            raw_target = {s: min(0.25, v / tot_iv) for s, v in inv_vols.items()} if tot_iv > 0 else {}
            pending_w = _apply_rebalance_band(weights, raw_target, band_rel_pct, 2.0)
            last_reb = cur_dt

    bt_dates = [p["date"] for p in curve]
    m = _compute_extended_metrics(curve, cdi_map, default_cdi, total_turnover, total_cost_pct)
    m["full_universe_since"] = full_univ_date or bt_dates[0]
    m["ffill_points"] = ffill_log
    m["_curve"] = curve
    m["_turn_events"] = turn_events
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
    px_brl, _ = calendar_fill.ffill_price_maps(px_brl, dates)

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
    px_brl, _ = calendar_fill.ffill_price_maps(px_brl, dates)

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
                # Usa último preço conhecido (forward-fill em feriados EUA/B3) para não excluir ativos em feriados locais
                if len(p_list) >= 64:
                    rets = [p_list[k] / p_list[k - 1] - 1.0 for k in range(-63, 0)]
                    mu = sum(rets) / len(rets)
                    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)) * math.sqrt(252)
                    if sd > 0:
                        inv_vols[s] = 1.0 / sd
            tot_iv = sum(inv_vols.values())
            raw_w = {s: v / tot_iv for s, v in inv_vols.items()} if tot_iv > 0 else {}
            # Water-filling iterativo respeitando teto <= 35% por ativo e <= 50% por classe sem estourar após normalização
            for _ in range(15):
                for s in list(raw_w.keys()):
                    if raw_w[s] > 0.35:
                        raw_w[s] = 0.35
                cls_tot: dict[str, float] = {}
                for s, w in raw_w.items():
                    c = asset_classes[s]
                    cls_tot[c] = cls_tot.get(c, 0.0) + w
                for s in list(raw_w.keys()):
                    c = asset_classes[s]
                    if cls_tot[c] > 0.50:
                        raw_w[s] *= 0.50 / cls_tot[c]
                rem = 1.0 - sum(raw_w.values())
                if rem <= 1e-6:
                    break
                cls_tot = {}
                for s, w in raw_w.items():
                    c = asset_classes[s]
                    cls_tot[c] = cls_tot.get(c, 0.0) + w
                elig = [s for s in raw_w if raw_w[s] < 0.35 - 1e-6 and cls_tot[asset_classes[s]] < 0.50 - 1e-6]
                if not elig:
                    break
                e_tot = sum(raw_w[s] for s in elig)
                for s in elig:
                    room_a = 0.35 - raw_w[s]
                    room_c = 0.50 - cls_tot[asset_classes[s]]
                    add = min(room_a, room_c, rem * (raw_w[s] / e_tot if e_tot > 0 else 1.0 / len(elig)))
                    raw_w[s] += max(0.0, add)
            if raw_w:
                pending_w = raw_w
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
    equal_weight: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    all_dates = sorted(set().union(*(px_maps[s].keys() for s in symbols if s in px_maps)))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]
    px_maps, _ = calendar_fill.ffill_price_maps({s: px_maps[s] for s in symbols if s in px_maps}, dates)
    symbols = [s for s in symbols if s in px_maps]

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
            if equal_weight:
                top5 = sorted(scores)
            pending_w = {s: 1.0 / len(top5) for s in top5} if top5 else {}
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

    # Etapa 3: regra de calendário — grade única de dias úteis (B3 ∪ EUA ∪ cripto) com forward-fill <= 5 datas (sinalizado)
    grid = sorted(d for d in set().union(*(m.keys() for m in px_maps.values())) if datetime.strptime(d, "%Y-%m-%d").weekday() < 5)
    px_maps, ffill_global = calendar_fill.ffill_price_maps(px_maps, grid)

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
        lines.append(f"- **Janelas móveis 3 anos anualizadas ({m['rolling_36m_ann']['count']}):** mín `{m['rolling_36m_ann']['min_ann_pct']}% a.a.`, mediana `{m['rolling_36m_ann']['median_ann_pct']}% a.a.`, máx `{m['rolling_36m_ann']['max_ann_pct']}% a.a.`")
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

    # ===== Etapa 3: variantes autorizadas do Trend Following (A controle, B mensal, C reentrada 55d) =====
    CUT = "2022-01-01"

    def _split(m: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        crv = m["_curve"]
        ev = m["_turn_events"]
        out = []
        for lo, hi in (("0000", CUT), (CUT, "9999")):
            sub = [p for p in crv if lo <= p["date"] < hi]
            if lo != "0000":
                prev = [p for p in crv if p["date"] < lo]
                if prev:
                    sub = [prev[-1]] + sub
            t = sum(x for d, x in ev if lo <= d < hi)
            out.append(_compute_extended_metrics(sub, cdi_map, default_cdi, t, t * 2.0 * cost_rate * 100.0))
        return out[0], out[1]

    def _passes(v: dict[str, Any], a: dict[str, Any]) -> tuple[bool, str]:
        red = 1.0 - (v["annual_turnover_pct"] / a["annual_turnover_pct"]) if a["annual_turnover_pct"] > 0 else 0.0
        ok_t = red >= 0.40
        ok_d = v["max_drawdown_pct"] >= a["max_drawdown_pct"] - 2.0
        ok_s = v["sharpe_vs_cdi"] >= a["sharpe_vs_cdi"]
        return ok_t and ok_d and ok_s, f"giro -{round(red * 100, 1)}% ({'ok' if ok_t else 'falha'}), DD {v['max_drawdown_pct']} vs {a['max_drawdown_pct']} ({'ok' if ok_d else 'falha'}), Sharpe {v['sharpe_vs_cdi']} vs {a['sharpe_vs_cdi']} ({'ok' if ok_s else 'falha'})"

    variants: dict[str, dict[str, Any]] = {}
    for uni_lbl, uni in (("c/ cripto", turtles_all), ("s/ cripto", turtles_nc)):
        for v in ("A", "B", "C"):
            mv, _ = _run_turtles_progressive(raw_candles, uni, cdi_map, default_cdi, cost_rate, band_rel_pct=25.0, variant=v)
            ins, oos = _split(mv)
            variants[f"{v}|{uni_lbl}"] = {"full": mv, "ins": ins, "oos": oos}

    decision_lines: list[str] = []
    winner = "A"
    cands = []
    for v in ("B", "C"):
        ok_all = True
        for uni_lbl in ("c/ cripto", "s/ cripto"):
            ok_i, why_i = _passes(variants[f"{v}|{uni_lbl}"]["ins"], variants[f"A|{uni_lbl}"]["ins"])
            decision_lines.append(f"- Variante `{v}` {uni_lbl}, seleção (até 2021): {'PASSA' if ok_i else 'NÃO PASSA'} — {why_i}")
            ok_all = ok_all and ok_i
        if ok_all:
            cands.append(v)
    if cands:
        best = max(cands, key=lambda v: variants[f"{v}|c/ cripto"]["ins"]["sharpe_vs_cdi"])
        ok_oos = True
        for uni_lbl in ("c/ cripto", "s/ cripto"):
            ok_o, why_o = _passes(variants[f"{best}|{uni_lbl}"]["oos"], variants[f"A|{uni_lbl}"]["oos"])
            decision_lines.append(f"- Confirmação fora da amostra (2022+) `{best}` {uni_lbl}: {'CONFIRMA' if ok_o else 'NÃO CONFIRMA'} — {why_o}")
            ok_oos = ok_oos and ok_o
        if ok_oos:
            winner = best
    decision_lines.append(f"- **Decisão:** variante adotada = `{winner}`" + (" (regra atual mantida)" if winner == "A" else ""))

    def _row(lbl: str, mm: dict[str, Any]) -> str:
        return f"| {lbl} | {mm['start_date']}..{mm['end_date']} | {mm['cagr_pct']} | {mm['volatility_ann_pct']} | {mm['max_drawdown_pct']} | {mm['sharpe_vs_cdi']} | {mm['annual_turnover_pct']} | {mm['annual_cost_pct']} |"

    # ===== Etapa 3: radar_top_n vs pesos iguais no mesmo universo =====
    m_ew, d_ew, _ = _run_radar_top_n_long(px_maps, radar_univ, cdi_map, default_cdi, cost_rate, equal_weight=True)
    m_ew_nc, d_ew_nc, _ = _run_radar_top_n_long(px_maps, radar_nc, cdi_map, default_cdi, cost_rate, equal_weight=True)

    lines.extend([
        "",
        "## 4. Rastreio Recente `radar_top_n`",
        *[f"- `{x}`" for x in tr_rad],
        "",
        "## 5. Regra de calendário (Etapa 3)",
        "- Grade única de dias úteis (B3 ∪ EUA ∪ cripto em dias úteis); ativo sem preço numa data usa o último preço válido por até 5 datas consecutivas (sinalizado), nunca é excluído da carteira nem do ranking.",
        f"- Pontos preenchidos por série (grade global): `{ {k: v for k, v in sorted(ffill_global.items()) if v} }`",
        f"- Pontos preenchidos Turtles (c/ cripto): `{ {k: v for k, v in sorted(m_trt.get('ffill_points', {}).items()) if v} }`",
        "",
        "## 6. Trend Following — variantes autorizadas (banda 25%, seleção até 2021, confirmação 2022+)",
        "| Variante | Janela | CAGR (%) | Vol (%) | MaxDD (%) | Sharpe | Giro/ano (%) | Custo/ano (%) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for key, vv in variants.items():
        for per in ("full", "ins", "oos"):
            lines.append(_row(f"{key} [{ {'full': 'completo', 'ins': 'seleção', 'oos': 'confirmação'}[per] }]", vv[per]))
    lines.extend(["", *decision_lines, ""])
    lines.extend([
        "## 7. Seleção vs Universo — `radar_top_n` vs pesos iguais (mesmo universo, mesmo rebalanceamento mensal e custos)",
        "| Carteira | Janela | CAGR (%) | Vol (%) | MaxDD (%) | Sharpe | Giro/ano (%) | Custo/ano (%) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        _row("radar_top_n c/ cripto", m_rad),
        _row("pesos iguais c/ cripto", m_ew),
        _row("radar_top_n s/ cripto", m_rad_nc),
        _row("pesos iguais s/ cripto", m_ew_nc),
        f"- Efeito da seleção (Top-5 − pesos iguais): c/ cripto `{round(m_rad['cagr_pct'] - m_ew['cagr_pct'], 2)} pp`; s/ cripto `{round(m_rad_nc['cagr_pct'] - m_ew_nc['cagr_pct'], 2)} pp`.",
        f"- Efeito do universo cripto (pesos iguais c/ − s/ cripto): `{round(m_ew['cagr_pct'] - m_ew_nc['cagr_pct'], 2)} pp`.",
        "",
        "## 8. Avisos",
        f"- Universo escolhido hoje (viés de sobrevivência e de seleção). Cripto: Turtles c/ `{m_trt['cagr_pct']}%` vs s/ `{m_trt_nc['cagr_pct']}%`; Radar c/ `{m_rad['cagr_pct']}%` vs s/ `{m_rad_nc['cagr_pct']}%`.",
    ])

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_path = BASE_DIR / "audit" / "reports" / f"backtest_long_{stamp}.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    from audit.run_audit import _update_reports_manifest
    _update_reports_manifest(BASE_DIR / "audit" / "reports", out_path)
    print(f"LONG_REPORT={out_path}")
    print(f"TREND_WINNER={winner}")
    print("\n".join(decision_lines))
    for key, vv in variants.items():
        print(f"VAR {key}: " + " | ".join(f"{p}: cagr={vv[p]['cagr_pct']} dd={vv[p]['max_drawdown_pct']} sh={vv[p]['sharpe_vs_cdi']} turn={vv[p]['annual_turnover_pct']}" for p in ("full", "ins", "oos")))
    print(f"EW c/={m_ew['cagr_pct']} s/={m_ew_nc['cagr_pct']} | RADAR c/={m_rad['cagr_pct']} s/={m_rad_nc['cagr_pct']}")
    for name, m, _ in results:
        print(f"STRAT {name}: {m['start_date']}..{m['end_date']} ({m['years']}y) cagr={m['cagr_pct']}% vol={m['volatility_ann_pct']}% dd={m['max_drawdown_pct']}% sharpe={m['sharpe_vs_cdi']} turn={m['annual_turnover_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
