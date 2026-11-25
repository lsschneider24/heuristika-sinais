"""Diagnóstico completo da Etapa 2F (Itens 1, 2, 3 e 4)."""
from __future__ import annotations

import math
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import market_data
from audit.tools.run_long_backtests import (
    _fetch_15y,
    _apply_rebalance_band,
    _compute_extended_metrics,
)


def diag_risk_parity(px_maps, rp_univ, cdi_map, default_cdi, cost_rate):
    print("=" * 80)
    print("ITEM 1: RISK PARITY SIMPLIFIED")
    print("=" * 80)
    fx = px_maps["USDBRL=X"]
    rp_brl = {
        u["symbol"]: ({d: px_maps[u["symbol"]][d] * fx[d] for d in px_maps[u["symbol"]] if d in fx} if u["currency"] == "USD" else px_maps[u["symbol"]])
        for u in rp_univ
    }
    rp_classes = {u["symbol"]: u["asset_class"] for u in rp_univ}
    syms = list(rp_brl.keys())
    all_dates = sorted(set().union(*(m.keys() for m in rp_brl.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    # (d) Verificar alinhamento de datas e sentido USD->BRL
    sample_dates = ["2012-01-03", "2015-01-05", "2020-03-23", "2024-11-25", "2026-11-24"]
    print("(d) Amostra USD->BRL:")
    for sd in sample_dates:
        # pega data mais próxima
        cand = [d for d in dates if d >= sd]
        if cand:
            d = cand[0]
            print(f"  {d}: USDBRL={fx.get(d)} | IVV_USD={px_maps['IVV'].get(d)} | IVV_BRL={rp_brl['IVV'].get(d)} | BOVA11={rp_brl['BOVA11.SA'].get(d)}")

    # Simular exatamente como _run_risk_parity_long gravando pesos, retornos mensais USD vs FX, e drawdown
    hist_px = {s: [] for s in syms}
    start_idx = None
    for i, d in enumerate(dates):
        ready = 0
        for s in syms:
            if d in rp_brl[s]:
                hist_px[s].append(rp_brl[s][d])
            if len(hist_px[s]) >= 64:
                ready += 1
        if ready >= 4 and start_idx is None:
            start_idx = i
            break

    nav = 100.0
    peak_nav = 100.0
    peak_date = dates[start_idx]
    worst_dd = 0.0
    worst_dd_info = {}
    weights = {}
    pending_w = None
    last_reb = datetime.strptime(dates[start_idx], "%Y-%m-%d").date()
    hist_px = {s: [rp_brl[s][d] for d in dates[: start_idx + 1] if d in rp_brl[s]] for s in syms}
    weight_snapshots = []
    cap_violations = []
    curve = [{"date": dates[start_idx], "value": nav}]

    for idx in range(start_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending_w is not None:
            turn = sum(abs(pending_w.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pending_w) | set(weights)) * 0.5
            nav *= 1.0 - turn * 2.0 * cost_rate
            weights = pending_w
            pending_w = None

        r_cdi = cdi_map.get(d_cur, default_cdi)
        cash_w = max(0.0, 1.0 - sum(weights.values()))
        port_ret = cash_w * r_cdi
        for s, w in weights.items():
            if d_cur in rp_brl[s] and d_prev in rp_brl[s]:
                port_ret += w * (rp_brl[s][d_cur] / rp_brl[s][d_prev] - 1.0)
            else:
                port_ret += w * r_cdi
        nav *= 1.0 + port_ret
        curve.append({"date": d_cur, "value": nav})

        if nav > peak_nav:
            peak_nav = nav
            peak_date = d_cur
        dd = (nav / peak_nav) - 1.0
        if dd < worst_dd:
            worst_dd = dd
            worst_dd_info = {
                "peak_date": peak_date,
                "peak_nav": round(peak_nav, 2),
                "trough_date": d_cur,
                "trough_nav": round(nav, 2),
                "dd_pct": round(dd * 100.0, 2),
                "weights": {k: round(v * 100.0, 2) for k, v in sorted(weights.items(), key=lambda x: -x[1])},
            }

        for s in syms:
            if d_cur in rp_brl[s]:
                hist_px[s].append(rp_brl[s][d_cur])

        cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
        if idx == start_idx + 1 or (cur_dt - last_reb).days >= 90:
            inv_vols = {}
            for s in syms:
                p_list = hist_px[s]
                if len(p_list) >= 64 and d_cur in rp_brl[s]:
                    rets = [p_list[k] / p_list[k - 1] - 1.0 for k in range(-63, 0)]
                    mu = sum(rets) / len(rets)
                    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)) * math.sqrt(252)
                    if sd > 0:
                        inv_vols[s] = 1.0 / sd
            tot_iv = sum(inv_vols.values())
            raw_w = {s: min(0.35, v / tot_iv) for s, v in inv_vols.items()} if tot_iv > 0 else {}
            cls_tot = {}
            for s, w in raw_w.items():
                c = rp_classes[s]
                cls_tot[c] = cls_tot.get(c, 0.0) + w
            for s in list(raw_w.keys()):
                c = rp_classes[s]
                if cls_tot[c] > 0.50:
                    raw_w[s] *= 0.50 / cls_tot[c]
            tot_w = sum(raw_w.values())
            if tot_w > 0:
                pending_w = {s: w / tot_w for s, w in raw_w.items()}
                # Check caps
                cls_after = {}
                for s, w in pending_w.items():
                    cls_after[rp_classes[s]] = cls_after.get(rp_classes[s], 0.0) + w
                max_a = max(pending_w.values())
                max_c = max(cls_after.values())
                if max_a > 0.3501 or max_c > 0.5001:
                    cap_violations.append((d_cur, round(max_a * 100, 2), round(max_c * 100, 2), {k: round(v * 100, 1) for k, v in pending_w.items()}))
                weight_snapshots.append((d_cur, {k: round(v * 100, 1) for k, v in pending_w.items()}))
            last_reb = cur_dt

    print(f"(b) Rebalanceamentos: {len(weight_snapshots)} | Violações de teto (35% ativo / 50% classe) após renormalização: {len(cap_violations)}")
    if cap_violations:
        print("  Primeiras 3 violações:", cap_violations[:3])
        print("  Última violação:", cap_violations[-1])
    print(f"(c) Pior drawdown: {worst_dd_info}")

    # (a) Decomposição mensal / anual por ativo (USD vs FX)
    print("(a) Retorno acumulado por ativo na mesma janela (USD vs Câmbio USDBRL vs BRL):")
    d0, d1 = dates[start_idx], dates[-1]
    fx0 = fx.get(d0) or fx[min(d for d in fx if d >= d0)]
    fx1 = fx.get(d1) or fx[max(d for d in fx if d <= d1)]
    fx_tot = (fx1 / fx0) - 1.0
    print(f"  USDBRL ({d0} -> {d1}): {fx0:.4f} -> {fx1:.4f} ({fx_tot*100:.2f}%)")
    for u in rp_univ:
        s = u["symbol"]
        m_brl = rp_brl[s]
        ds = [d for d in dates[start_idx:] if d in m_brl]
        r_brl = (m_brl[ds[-1]] / m_brl[ds[0]]) - 1.0
        if u["currency"] == "USD":
            m_usd = px_maps[s]
            r_usd = (m_usd[ds[-1]] / m_usd[ds[0]]) - 1.0
            print(f"  {s:<10} (USD): USD={r_usd*100:7.2f}% | FX~={fx_tot*100:6.2f}% | BRL={r_brl*100:7.2f}%")
        else:
            print(f"  {s:<10} (BRL): BRL={r_brl*100:7.2f}%")

    # (e) Recomputação independente simples com tetos CORRETOS (35% ativo, 50% classe sem estourar após normalização, sobra vai para CDI)
    # E também versão sem teto estourado (água-viva / water-filling até 100% respeitando caps)
    def run_rp_clean(waterfill: bool):
        hist_p = {s: [rp_brl[s][d] for d in dates[: start_idx + 1] if d in rp_brl[s]] for s in syms}
        nv = 100.0
        crv = [{"date": dates[start_idx], "value": nv}]
        w_cur = {}
        p_w = None
        l_reb = datetime.strptime(dates[start_idx], "%Y-%m-%d").date()
        t_turn = 0.0
        t_cost = 0.0
        for idx in range(start_idx + 1, len(dates)):
            d_prev, d_cur = dates[idx - 1], dates[idx]
            if p_w is not None:
                trn = sum(abs(p_w.get(s, 0.0) - w_cur.get(s, 0.0)) for s in set(p_w) | set(w_cur)) * 0.5
                t_turn += trn
                t_cost += trn * 2.0 * cost_rate * 100.0
                nv *= 1.0 - trn * 2.0 * cost_rate
                w_cur = p_w
                p_w = None
            r_cdi = cdi_map.get(d_cur, default_cdi)
            cw = max(0.0, 1.0 - sum(w_cur.values()))
            pret = cw * r_cdi
            for s, w in w_cur.items():
                if d_cur in rp_brl[s] and d_prev in rp_brl[s]:
                    pret += w * (rp_brl[s][d_cur] / rp_brl[s][d_prev] - 1.0)
                else:
                    pret += w * r_cdi
            nv *= 1.0 + pret
            crv.append({"date": d_cur, "value": nv})
            for s in syms:
                if d_cur in rp_brl[s]:
                    hist_p[s].append(rp_brl[s][d_cur])
            cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
            if idx == start_idx + 1 or (cur_dt - l_reb).days >= 90:
                iv = {}
                for s in syms:
                    pl = hist_p[s]
                    if len(pl) >= 64 and d_cur in rp_brl[s]:
                        rts = [pl[k] / pl[k - 1] - 1.0 for k in range(-63, 0)]
                        mu = sum(rts) / len(rts)
                        sd = math.sqrt(sum((r - mu) ** 2 for r in rts) / max(1, len(rts) - 1)) * math.sqrt(252)
                        if sd > 0:
                            iv[s] = 1.0 / sd
                if iv:
                    tot = sum(iv.values())
                    w_new = {s: v / tot for s, v in iv.items()}
                    if waterfill:
                        # Redistribuição iterativa respeitando <= 0.35 por ativo e <= 0.50 por classe
                        for _ in range(15):
                            # cap ativo
                            for s in list(w_new):
                                if w_new[s] > 0.35:
                                    w_new[s] = 0.35
                            # cap classe
                            ct = {}
                            for s, val in w_new.items():
                                ct[rp_classes[s]] = ct.get(rp_classes[s], 0.0) + val
                            for s in list(w_new):
                                c = rp_classes[s]
                                if ct[c] > 0.50:
                                    w_new[s] *= 0.50 / ct[c]
                            rem = 1.0 - sum(w_new.values())
                            if rem <= 1e-6:
                                break
                            # elegíveis que ainda têm folga no ativo e na classe
                            ct = {}
                            for s, val in w_new.items():
                                ct[rp_classes[s]] = ct.get(rp_classes[s], 0.0) + val
                            elig = [s for s in w_new if w_new[s] < 0.35 - 1e-6 and ct[rp_classes[s]] < 0.50 - 1e-6]
                            if not elig:
                                break
                            elig_tot = sum(w_new[s] for s in elig)
                            for s in elig:
                                w_new[s] += rem * (w_new[s] / elig_tot if elig_tot > 0 else 1.0 / len(elig))
                    else:
                        # apenas cap sem renormalizar (sobra em CDI)
                        for s in list(w_new):
                            w_new[s] = min(0.35, w_new[s])
                        ct = {}
                        for s, val in w_new.items():
                            ct[rp_classes[s]] = ct.get(rp_classes[s], 0.0) + val
                        for s in list(w_new):
                            c = rp_classes[s]
                            if ct[c] > 0.50:
                                w_new[s] *= 0.50 / ct[c]
                    p_w = w_new
                l_reb = cur_dt
        return _compute_extended_metrics(crv, cdi_map, default_cdi, t_turn, t_cost)

    m_wf = run_rp_clean(True)
    m_cdi = run_rp_clean(False)
    print(f"(e) Com tetos rígidos + redistribuição (waterfill): CAGR={m_wf['cagr_pct']}% Vol={m_wf['volatility_ann_pct']}% DD={m_wf['max_drawdown_pct']}% Sharpe={m_wf['sharpe_vs_cdi']}")
    print(f"(e) Com tetos rígidos + sobra em CDI: CAGR={m_cdi['cagr_pct']}% Vol={m_cdi['volatility_ann_pct']}% DD={m_cdi['max_drawdown_pct']}% Sharpe={m_cdi['sharpe_vs_cdi']}")

    # Verificar também por que TLT / BOVA11 / DBC tiveram esse desempenho e se RP em janela mais recente ou em USD muda
    # E verificar RP com caps vs sem caps
    print("\n--- Decomposição de anos com pior retorno do Risk Parity atual ---")
    by_yr = {}
    for i in range(1, len(curve)):
        yr = curve[i]["date"][:4]
        by_yr.setdefault(yr, []).append((curve[i-1]["value"], curve[i]["value"]))
    for yr in sorted(by_yr):
        r_yr = (by_yr[yr][-1][1] / by_yr[yr][0][0] - 1.0) * 100.0
        print(f"  {yr}: {r_yr:6.2f}%")


def diag_turtles(raw_candles, turtles_all, cdi_map, default_cdi, cost_rate):
    print("\n" + "=" * 80)
    print("ITEM 2: TREND FOLLOWING TURTLES TURNOVER DECOMPOSITION")
    print("=" * 80)
    by_sym = {s: {c["date"]: c for c in raw_candles[s]} for s in turtles_all}
    all_dates = sorted(set().union(*(m.keys() for m in by_sym.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]

    hist_bars = {s: [] for s in turtles_all}
    start_bt_idx = None
    for idx, d in enumerate(dates):
        ready_cnt = 0
        for s in turtles_all:
            if d in by_sym[s]:
                hist_bars[s].append(by_sym[s][d])
            if len(hist_bars[s]) >= 200:
                ready_cnt += 1
        if ready_cnt >= 3 and start_bt_idx is None:
            start_bt_idx = idx
            break

    for band in (0.0, 25.0):
        hist_bars = {s: [] for s in turtles_all}
        for d in dates[:start_bt_idx]:
            for s in turtles_all:
                if d in by_sym[s]:
                    hist_bars[s].append(by_sym[s][d])
        weights = {}
        pending_w = None
        peaks = {}
        last_reb = datetime.strptime(dates[start_bt_idx], "%Y-%m-%d").date()
        nav = 100.0
        turn_sig = 0.0
        turn_atr = 0.0
        turn_renorm = 0.0
        reb_events = 0
        total_turn = 0.0
        total_cost = 0.0

        # Também atribuir retorno por ativo
        attrib = {s: 0.0 for s in turtles_all}
        attrib["CAIXA_CDI"] = 0.0

        for idx in range(start_bt_idx + 1, len(dates)):
            d_prev, d_cur = dates[idx - 1], dates[idx]
            if pending_w is not None:
                pw, cause_info = pending_w
                turn = sum(abs(pw.get(s, 0.0) - weights.get(s, 0.0)) for s in set(pw) | set(weights)) * 0.5
                if turn > 0:
                    reb_events += 1
                    total_turn += turn
                    total_cost += turn * 2.0 * cost_rate * 100.0
                    nav *= 1.0 - turn * 2.0 * cost_rate
                    turn_sig += cause_info["sig"]
                    turn_atr += cause_info["atr"]
                    turn_renorm += cause_info["renorm"]
                    weights = pw
                pending_w = None

            cash_w = max(0.0, 1.0 - sum(weights.values()))
            r_cdi = cdi_map.get(d_cur, default_cdi)
            port_ret = cash_w * r_cdi
            attrib["CAIXA_CDI"] += math.log1p(cash_w * r_cdi)
            for s, w in weights.items():
                if d_cur in by_sym[s] and d_prev in by_sym[s]:
                    r_s = by_sym[s][d_cur]["close"] / by_sym[s][d_prev]["close"] - 1.0
                    port_ret += w * r_s
                    attrib[s] += w * r_s
                else:
                    port_ret += w * r_cdi
                    attrib["CAIXA_CDI"] += w * r_cdi
            nav *= 1.0 + port_ret

            for s in turtles_all:
                if d_cur in by_sym[s]:
                    hist_bars[s].append(by_sym[s][d_cur])

            cur_dt = datetime.strptime(d_cur, "%Y-%m-%d").date()
            if (cur_dt - last_reb).days >= 7:
                inv_vols = {}
                for s in turtles_all:
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
                new_w = _apply_rebalance_band(weights, raw_target, band, 2.0)

                # Decompor o turnover entre `weights` e `new_w`
                c_sig = 0.0
                c_atr = 0.0
                for s in set(weights) | set(new_w):
                    cw = weights.get(s, 0.0)
                    nw = new_w.get(s, 0.0)
                    if (cw == 0.0 and nw > 0.0) or (cw > 0.0 and nw == 0.0):
                        c_sig += abs(nw - cw) * 0.5
                    else:
                        c_atr += abs(nw - cw) * 0.5
                # Checar se houve renormalização tot > 1.0 em _apply_rebalance_band
                c_ren = 0.0
                pending_w = (new_w, {"sig": c_sig, "atr": c_atr, "renorm": c_ren})
                last_reb = cur_dt

        yrs = (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[start_bt_idx], "%Y-%m-%d")).days / 365.25
        print(f"Banda {band}% ({yrs:.2f} anos): events={reb_events} | giro/ano={total_turn/yrs*100:.1f}% | custo_total={total_cost:.2f}% | nav_final={nav:.2f}")
        print(f"  Decomposição do giro: entrada/saída (sinal)={turn_sig/yrs*100:.1f}%/ano ({turn_sig/max(1e-9,total_turn)*100:.1f}%) | ajuste peso/ATR={turn_atr/yrs*100:.1f}%/ano ({turn_atr/max(1e-9,total_turn)*100:.1f}%)")
        if band == 25.0:
            print("  Soma de retornos ponderados (atribuição simples) na banda 25%:")
            for k, v in sorted(attrib.items(), key=lambda x: -x[1]):
                print(f"    {k:<12}: {v*100:6.2f}%")


def diag_dual_momentum(px_maps, cdi_map, default_cdi, cost_rate):
    print("\n" + "=" * 80)
    print("ITEM 4: DUAL MOMENTUM WORST DRAWDOWN")
    print("=" * 80)
    fx = px_maps["USDBRL=X"]
    dm_brl = {
        sym: ({d: px_maps[sym][d] * fx[d] for d in px_maps[sym] if d in fx} if is_usd else px_maps[sym])
        for sym, is_usd in (("IVV", True), ("VGK", True), ("EEM", True), ("BOVA11.SA", False))
    }
    syms = list(dm_brl.keys())
    all_dates = sorted(set().union(*(m.keys() for m in dm_brl.values())))
    dates = [d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]
    cdi_idx = {dates[0]: 1.0}
    for i in range(1, len(dates)):
        cdi_idx[dates[i]] = cdi_idx[dates[i - 1]] * (1.0 + cdi_map.get(dates[i], default_cdi))

    hist_dates = {s: [] for s in syms}
    start_idx = None
    for i, d in enumerate(dates):
        ready = 0
        for s in syms:
            if d in dm_brl[s]:
                hist_dates[s].append(d)
            if len(hist_dates[s]) >= 253:
                ready += 1
        if ready >= 2 and i >= 252 and start_idx is None:
            start_idx = i
            break

    nav = 100.0
    peak_nav = 100.0
    peak_date = dates[start_idx]
    worst_dd = 0.0
    worst_info = {}
    current = "SELIC_CDI"
    pending = None
    hist_dates = {s: [d for d in dates[: start_idx + 1] if d in dm_brl[s]] for s in syms}
    dd_events = []
    in_worst = False
    signals_log = []

    for idx in range(start_idx + 1, len(dates)):
        d_prev, d_cur = dates[idx - 1], dates[idx]
        if pending is not None and pending != current:
            nav *= 1.0 - cost_rate
            current = pending
            pending = None

        r_cdi = cdi_map.get(d_cur, default_cdi)
        if current == "SELIC_CDI":
            nav *= 1.0 + r_cdi
        elif d_cur in dm_brl[current] and d_prev in dm_brl[current]:
            nav *= dm_brl[current][d_cur] / dm_brl[current][d_prev]
        else:
            nav *= 1.0 + r_cdi

        if nav > peak_nav:
            peak_nav = nav
            peak_date = d_cur
        dd = (nav / peak_nav) - 1.0
        if dd < worst_dd:
            worst_dd = dd
            worst_info = {
                "peak_date": peak_date,
                "peak_nav": round(peak_nav, 2),
                "trough_date": d_cur,
                "trough_nav": round(nav, 2),
                "dd_pct": round(dd * 100.0, 2),
                "holding_at_trough": current,
            }

        for s in syms:
            if d_cur in dm_brl[s]:
                hist_dates[s].append(d_cur)

        if (idx - start_idx) % 21 == 0:
            cdi_12m = (cdi_idx[d_cur] / cdi_idx[dates[idx - 252]]) - 1.0
            moms = {"SELIC_CDI": cdi_12m}
            for s in syms:
                hd = hist_dates[s]
                if len(hd) >= 253 and d_cur in dm_brl[s]:
                    moms[s] = (dm_brl[s][d_cur] / dm_brl[s][hd[-253]]) - 1.0
            best = max(moms, key=lambda k: moms[k])
            if current in moms and best != current and best != "SELIC_CDI" and current != "SELIC_CDI":
                if moms[best] - moms[current] <= 0.025:
                    best = current
            signals_log.append((d_cur, current, best, {k: round(v * 100, 1) for k, v in moms.items()}))
            pending = best

    print(f"Pior drawdown: {worst_info}")
    # Duração até recuperar peak_nav
    rec_date = "Não recuperou"
    found_peak = False
    # Reconstruir duração simples
    p_dt = datetime.strptime(worst_info["peak_date"], "%Y-%m-%d").date()
    t_dt = datetime.strptime(worst_info["trough_date"], "%Y-%m-%d").date()
    print(f"Duração pico->vale: {(t_dt - p_dt).days} dias")
    print("Sinais 12m durante a janela do pior drawdown:")
    for dt_s, cur_s, bst_s, moms_s in signals_log:
        if worst_info["peak_date"] <= dt_s <= worst_info["trough_date"] or (dt_s >= worst_info["trough_date"] and dt_s <= "2023-12-31"):
            if dt_s >= worst_info["peak_date"]:
                print(f"  {dt_s}: atual={cur_s} -> prox={bst_s} | moms={moms_s}")
                if len([1 for x in signals_log if worst_info["peak_date"] <= x[0] <= dt_s]) > 14:
                    break


def main():
    cdi_info = market_data.fetch_bcb_cdi_series(start_date="2011-11-24", allow_cache=False)
    cdi_map = {str(r["date"]): float(r["rate_pct"]) / 100.0 for r in cdi_info["daily_rates"]}
    default_cdi = float(cdi_info["last_daily_rate_pct"]) / 100.0
    cost_rate = 15.0 / 10000.0

    cfg = market_data.load_strategies_config()
    rp_univ = cfg["strategies"]["risk_parity_simplified"]["parametros"]["universe"]
    turtles_all = ["BOVA11.SA", "IVVB11.SA", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA", "GC=F", "BTC-USD"]
    fetch_syms = sorted(set(["BOVA11.SA", "IVVB11.SA", "USDBRL=X", "IVV", "VGK", "EEM"] + turtles_all + [u["symbol"] for u in rp_univ]))
    raw_candles = {}
    px_maps = {}
    for s in fetch_syms:
        res = _fetch_15y(s)
        if res.get("status") == "ok" and res.get("candles"):
            raw_candles[s] = res["candles"]
            px_maps[s] = {c["date"]: float(c["close"]) for c in res["candles"]}

    diag_risk_parity(px_maps, rp_univ, cdi_map, default_cdi, cost_rate)
    diag_turtles(raw_candles, turtles_all, cdi_map, default_cdi, cost_rate)
    diag_dual_momentum(px_maps, cdi_map, default_cdi, cost_rate)


if __name__ == "__main__":
    main()
