"""Módulo Radar Global de Oportunidades (Etapa 2B — Motor Determinístico).

Regras de governança:
- Custo zero, modo estrito (allow_fallback=False -> 'indisponível' quando faltar dado).
- Toda saída de candidato é rotulada como 'CANDIDATO A ESTUDO' (nunca 'compre/venda').
- Score rotulado explicitamente como 'pontuação heurística, sem poder preditivo comprovado'.
- Valuation global opcional (data/global_valuation.json): não verificado = 'indisponível'.
"""

from __future__ import annotations

from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any

import database
import market_data

BASE_DIR = Path(__file__).resolve().parent
GLOBAL_VALUATION_PATH = BASE_DIR / "data" / "global_valuation.json"
INDISPONIVEL = market_data.INDISPONIVEL
DADOS_DESATUALIZADOS = market_data.DADOS_DESATUALIZADOS


def load_global_valuation(
    valuation_path: Path | str | None = None,
    reference_today: date | str | None = None,
) -> dict[str, Any]:
    """Carrega snapshot opcional de valuation global. Registros sem verified=True viram 'indisponível'."""
    path = Path(valuation_path) if valuation_path else GLOBAL_VALUATION_PATH
    if not path.is_file():
        return {"status": INDISPONIVEL, "is_stale": False, "records": {}}

    raw = json.loads(path.read_text(encoding="utf-8"))
    collected_str = str(raw.get("collected_at") or "").strip()
    max_age = int(raw.get("max_age_days", 90))
    if isinstance(reference_today, str):
        today_dt = datetime.strptime(reference_today[:10], "%Y-%m-%d").date()
    elif isinstance(reference_today, date):
        today_dt = reference_today
    else:
        today_dt = datetime.now().date()

    is_stale = False
    age_days: int | str = INDISPONIVEL
    if collected_str:
        try:
            ref_dt = datetime.strptime(collected_str[:10], "%Y-%m-%d").date()
            age_days = max(0, (today_dt - ref_dt).days)
            is_stale = age_days > max_age
        except ValueError:
            age_days = INDISPONIVEL

    norm_records: dict[str, dict[str, Any]] = {}
    for sym, rec in (raw.get("records") or {}).items():
        if not isinstance(rec, dict) or not bool(rec.get("verified", False)):
            norm_records[sym] = {
                "status": INDISPONIVEL,
                "pe_ratio": INDISPONIVEL,
                "dividend_yield_pct": INDISPONIVEL,
                "source": rec.get("source", INDISPONIVEL) if isinstance(rec, dict) else INDISPONIVEL,
                "collected_at": rec.get("collected_at", INDISPONIVEL) if isinstance(rec, dict) else INDISPONIVEL,
                "verified": False,
                "freshness_label": INDISPONIVEL,
            }
        else:
            norm_records[sym] = {
                "status": DADOS_DESATUALIZADOS if is_stale else "ok",
                "pe_ratio": rec.get("pe_ratio", INDISPONIVEL),
                "dividend_yield_pct": rec.get("dividend_yield_pct", INDISPONIVEL),
                "source": rec.get("source", INDISPONIVEL),
                "collected_at": rec.get("collected_at", collected_str),
                "verified": True,
                "freshness_label": DADOS_DESATUALIZADOS if is_stale else "em_dia",
            }

    return {
        "status": DADOS_DESATUALIZADOS if is_stale else "ok",
        "collected_at": collected_str or INDISPONIVEL,
        "age_days": age_days,
        "max_age_days": max_age,
        "is_stale": is_stale,
        "records": norm_records,
    }


def _pct_return_over_window(closes: list[float], lookback: int) -> float | str:
    if len(closes) <= lookback or closes[-lookback - 1] <= 0:
        return INDISPONIVEL
    return round(((closes[-1] / closes[-lookback - 1]) - 1.0) * 100.0, 2)


def _compute_vol_and_dd(closes: list[float]) -> tuple[float | str, float | str, float | str]:
    if len(closes) < 20:
        return INDISPONIVEL, INDISPONIVEL, INDISPONIVEL
    rets = [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(rets) < 10:
        return INDISPONIVEL, INDISPONIVEL, INDISPONIVEL
    mean_r = sum(rets) / len(rets)
    var_r = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    vol_ann = round(math.sqrt(max(0.0, var_r)) * math.sqrt(252.0) * 100.0, 2)

    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = ((c / peak) - 1.0) * 100.0 if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    curr_dd = ((closes[-1] / peak) - 1.0) * 100.0 if peak > 0 else 0.0
    return vol_ann, round(curr_dd, 2), round(max_dd, 2)


def compute_asset_radar_metrics(
    asset: dict[str, Any],
    candles_res: dict[str, Any],
    benchmark_closes: list[float] | None,
    fx_candles_res: dict[str, Any] | None,
    score_weights: dict[str, float],
) -> dict[str, Any]:
    """Calcula métricas puras, retorno USD/BRL com decomposição cambial e score heurístico."""
    sym = asset["symbol"]
    if not isinstance(candles_res, dict) or candles_res.get("status") != "ok" or not isinstance(candles_res.get("candles"), list):
        return {
            "symbol": sym,
            "name": asset.get("name", sym),
            "asset_class": asset.get("asset_class", INDISPONIVEL),
            "region": asset.get("region", INDISPONIVEL),
            "currency": asset.get("currency", INDISPONIVEL),
            "br_equivalent": asset.get("br_equivalent"),
            "label": "CANDIDATO A ESTUDO",
            "status": INDISPONIVEL,
            "last_price": INDISPONIVEL,
            "ret_3m_pct": INDISPONIVEL,
            "ret_6m_pct": INDISPONIVEL,
            "ret_12m_pct": INDISPONIVEL,
            "momentum_12_1_pct": INDISPONIVEL,
            "trend_above_mm200": INDISPONIVEL,
            "trend_mm50_above_mm200": INDISPONIVEL,
            "rel_strength_12m_pp": INDISPONIVEL,
            "volatility_ann_pct": INDISPONIVEL,
            "current_drawdown_pct": INDISPONIVEL,
            "max_drawdown_pct": INDISPONIVEL,
            "return_usd_12m_pct": INDISPONIVEL,
            "fx_effect_12m_pct": INDISPONIVEL,
            "return_brl_12m_pct": INDISPONIVEL,
            "score": INDISPONIVEL,
            "score_breakdown": {},
            "data_used": {"source": INDISPONIVEL, "bars": 0, "price_adjusted": False},
        }

    candles = candles_res["candles"]
    closes = [float(c["close"]) for c in candles if c.get("close") is not None]
    last_px = round(closes[-1], 4) if closes else INDISPONIVEL

    r3 = _pct_return_over_window(closes, 63)
    r6 = _pct_return_over_window(closes, 126)
    r12 = _pct_return_over_window(closes, 252)

    if len(closes) > 252 and closes[-253] > 0 and closes[-22] > 0:
        mom_12_1: float | str = round(((closes[-22] / closes[-253]) - 1.0) * 100.0, 2)
    else:
        mom_12_1 = INDISPONIVEL

    mm50 = sum(closes[-50:]) / 50.0 if len(closes) >= 50 else None
    mm200 = sum(closes[-200:]) / 200.0 if len(closes) >= 200 else None
    above_200 = (closes[-1] > mm200) if (mm200 is not None and closes) else INDISPONIVEL
    mm50_gt_200 = (mm50 > mm200) if (mm50 is not None and mm200 is not None) else INDISPONIVEL

    vol_ann, curr_dd, max_dd = _compute_vol_and_dd(closes)

    rel_strength: float | str = INDISPONIVEL
    if isinstance(r12, (int, float)) and isinstance(benchmark_closes, list) and len(benchmark_closes) > 252:
        bench_r12 = _pct_return_over_window(benchmark_closes, 252)
        if isinstance(bench_r12, (int, float)):
            rel_strength = round(r12 - bench_r12, 2)

    # Retorno em USD e em BRL com efeito cambial separado
    currency = asset.get("currency", "USD")
    fx_closes = (
        [float(x["close"]) for x in fx_candles_res["candles"]]
        if isinstance(fx_candles_res, dict) and fx_candles_res.get("status") == "ok" and isinstance(fx_candles_res.get("candles"), list)
        else None
    )
    fx_12m = _pct_return_over_window(fx_closes, 252) if fx_closes else INDISPONIVEL

    ret_usd_12m: float | str = INDISPONIVEL
    ret_brl_12m: float | str = INDISPONIVEL
    fx_effect_12m: float | str = INDISPONIVEL

    if isinstance(r12, (int, float)):
        if currency == "USD":
            ret_usd_12m = r12
            if isinstance(fx_12m, (int, float)):
                fx_effect_12m = fx_12m
                ret_brl_12m = round(((1.0 + r12 / 100.0) * (1.0 + fx_12m / 100.0) - 1.0) * 100.0, 2)
        elif currency == "BRL":
            ret_brl_12m = r12
            if isinstance(fx_12m, (int, float)) and (1.0 + fx_12m / 100.0) > 0:
                fx_effect_12m = fx_12m
                ret_usd_12m = round(((1.0 + r12 / 100.0) / (1.0 + fx_12m / 100.0) - 1.0) * 100.0, 2)

    # Score heurístico composto (0 a 100) com decomposição transparente
    w_mom = float(score_weights.get("momentum_12_1", 0.30))
    w_trd = float(score_weights.get("trend", 0.25))
    w_rel = float(score_weights.get("relative_strength", 0.20))
    w_vol = float(score_weights.get("low_volatility", 0.15))
    w_dd = float(score_weights.get("drawdown_control", 0.10))

    if isinstance(mom_12_1, (int, float)) and isinstance(vol_ann, (int, float)) and isinstance(max_dd, (int, float)):
        s_mom = max(0.0, min(100.0, 50.0 + mom_12_1 * 1.25))
        s_trd = (50.0 if above_200 is True else 0.0) + (50.0 if mm50_gt_200 is True else 0.0)
        s_rel = max(0.0, min(100.0, 50.0 + (float(rel_strength) * 2.0 if isinstance(rel_strength, (int, float)) else 0.0)))
        s_vol = max(0.0, min(100.0, 100.0 - vol_ann * 1.8))
        s_dd = max(0.0, min(100.0, 100.0 - abs(float(max_dd)) * 2.0))

        c_mom = round(s_mom * w_mom, 2)
        c_trd = round(s_trd * w_trd, 2)
        c_rel = round(s_rel * w_rel, 2)
        c_vol = round(s_vol * w_vol, 2)
        c_dd = round(s_dd * w_dd, 2)
        total_score: float | str = round(c_mom + c_trd + c_rel + c_vol + c_dd, 2)
        breakdown = {
            "momentum_12_1": {"raw_0_100": round(s_mom, 1), "weight": w_mom, "contribution": c_mom},
            "trend": {"raw_0_100": round(s_trd, 1), "weight": w_trd, "contribution": c_trd},
            "relative_strength": {"raw_0_100": round(s_rel, 1), "weight": w_rel, "contribution": c_rel},
            "low_volatility": {"raw_0_100": round(s_vol, 1), "weight": w_vol, "contribution": c_vol},
            "drawdown_control": {"raw_0_100": round(s_dd, 1), "weight": w_dd, "contribution": c_dd},
        }
    else:
        total_score = INDISPONIVEL
        breakdown = {}

    return {
        "symbol": sym,
        "name": asset.get("name", sym),
        "asset_class": asset.get("asset_class", INDISPONIVEL),
        "region": asset.get("region", INDISPONIVEL),
        "currency": currency,
        "br_equivalent": asset.get("br_equivalent"),
        "label": "CANDIDATO A ESTUDO",
        "status": "ok",
        "last_price": last_px,
        "ret_3m_pct": r3,
        "ret_6m_pct": r6,
        "ret_12m_pct": r12,
        "momentum_12_1_pct": mom_12_1,
        "trend_above_mm200": above_200,
        "trend_mm50_above_mm200": mm50_gt_200,
        "rel_strength_12m_pp": rel_strength,
        "volatility_ann_pct": vol_ann,
        "current_drawdown_pct": curr_dd,
        "max_drawdown_pct": max_dd,
        "return_usd_12m_pct": ret_usd_12m,
        "fx_effect_12m_pct": fx_effect_12m,
        "return_brl_12m_pct": ret_brl_12m,
        "score": total_score,
        "score_note": "Pontuação heurística, sem poder preditivo comprovado.",
        "score_breakdown": breakdown,
        "data_used": {
            "source": candles_res.get("source", INDISPONIVEL),
            "bars": len(candles),
            "start_date": candles[0]["date"],
            "end_date": candles[-1]["date"],
            "price_adjusted": bool(candles_res.get("price_adjusted", False)),
        },
    }


def classify_market_regime(
    regime_candles: dict[str, dict[str, Any]],
    regime_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Classifica regime em RISK-ON / NEUTRO / RISK-OFF / 'indisponível'.
    Regra de agregação: RISK-ON se >= 3 de 4 sinais forem risk-on;
    RISK-OFF se >= 3 de 4 forem risk-off; caso contrário NEUTRO.
    ^TNX e ^IRX são lidos diretamente em % (ex.: 4.25 = 4,25%, nunca multiplicados por 10).
    """
    min_dir = int(regime_cfg.get("min_signals_for_direction", 3))
    vix_on = float(regime_cfg.get("vix_risk_on_below", 18.0))
    vix_off = float(regime_cfg.get("vix_risk_off_above", 25.0))
    yc_on = float(regime_cfg.get("yield_curve_risk_on_above", 0.25))
    yc_off = float(regime_cfg.get("yield_curve_risk_off_below", -0.25))

    signals: list[dict[str, Any]] = []

    # 1. VIX (^VIX)
    vix_res = regime_candles.get(regime_cfg.get("vix_symbol", "^VIX")) or {}
    if vix_res.get("status") == "ok" and vix_res.get("candles"):
        vix_val = round(float(vix_res["candles"][-1]["close"]), 2)
        if vix_val < vix_on:
            st = "RISK-ON"
        elif vix_val > vix_off:
            st = "RISK-OFF"
        else:
            st = "NEUTRO"
        signals.append({
            "id": "vix",
            "name": "Volatilidade Implícita (VIX)",
            "value": vix_val,
            "unit": "pts",
            "signal": st,
            "rule": f"Convenção: < {vix_on} Risk-On | > {vix_off} Risk-Off",
        })
    else:
        signals.append({"id": "vix", "name": "Volatilidade Implícita (VIX)", "value": INDISPONIVEL, "signal": INDISPONIVEL})

    # 2. Curva de Juros EUA (^TNX - ^IRX) em pontos percentuais (% a.a.)
    tnx_res = regime_candles.get(regime_cfg.get("yield_10y_symbol", "^TNX")) or {}
    irx_res = regime_candles.get(regime_cfg.get("yield_3m_symbol", "^IRX")) or {}
    if (
        tnx_res.get("status") == "ok" and tnx_res.get("candles")
        and irx_res.get("status") == "ok" and irx_res.get("candles")
    ):
        y10 = float(tnx_res["candles"][-1]["close"])
        y3m = float(irx_res["candles"][-1]["close"])
        spread_pp = round(y10 - y3m, 2)
        if spread_pp > yc_on:
            st = "RISK-ON"
        elif spread_pp < yc_off:
            st = "RISK-OFF"
        else:
            st = "NEUTRO"
        signals.append({
            "id": "yield_curve",
            "name": "Curva de Juros EUA (10Y - 3M)",
            "value": spread_pp,
            "y10_pct": round(y10, 2),
            "y3m_pct": round(y3m, 2),
            "unit": "pp (% a.a.)",
            "signal": st,
            "rule": f"Convenção: > +{yc_on} pp Risk-On | < {yc_off} pp Risk-Off (^TNX e ^IRX em %)",
        })
    else:
        signals.append({"id": "yield_curve", "name": "Curva de Juros EUA (10Y - 3M)", "value": INDISPONIVEL, "signal": INDISPONIVEL})

    # 3. Dólar DXY (DX-Y.NYB vs MM50/MM200)
    dxy_res = regime_candles.get(regime_cfg.get("dxy_symbol", "DX-Y.NYB")) or {}
    if dxy_res.get("status") == "ok" and dxy_res.get("candles") and len(dxy_res["candles"]) >= 50:
        dxy_closes = [float(c["close"]) for c in dxy_res["candles"]]
        d_now = dxy_closes[-1]
        d_mm50 = sum(dxy_closes[-50:]) / 50.0
        d_mm200 = sum(dxy_closes[-200:]) / 200.0 if len(dxy_closes) >= 200 else d_mm50
        if d_now < d_mm50:
            st = "RISK-ON"
        elif d_now > d_mm50 and d_now > d_mm200:
            st = "RISK-OFF"
        else:
            st = "NEUTRO"
        signals.append({
            "id": "dxy",
            "name": "Índice Dólar (DXY vs MM50/MM200)",
            "value": round(d_now, 2),
            "unit": "pts",
            "signal": st,
            "rule": "Convenção: DXY < MM50 Risk-On | DXY > MM50 e MM200 Risk-Off",
        })
    else:
        signals.append({"id": "dxy", "name": "Índice Dólar (DXY vs MM50/MM200)", "value": INDISPONIVEL, "signal": INDISPONIVEL})

    # 4. Spread de Crédito Proxy (HYG / IEF vs MM50)
    hyg_res = regime_candles.get(regime_cfg.get("credit_hyg_symbol", "HYG")) or {}
    ief_res = regime_candles.get(regime_cfg.get("credit_ief_symbol", "IEF")) or {}
    if (
        hyg_res.get("status") == "ok" and hyg_res.get("candles")
        and ief_res.get("status") == "ok" and ief_res.get("candles")
    ):
        h_map = {c["date"]: float(c["close"]) for c in hyg_res["candles"]}
        i_map = {c["date"]: float(c["close"]) for c in ief_res["candles"]}
        common = sorted(set(h_map.keys()) & set(i_map.keys()))
        ratios = [h_map[d] / i_map[d] for d in common if i_map[d] > 0]
        if len(ratios) >= 50:
            r_now = ratios[-1]
            r_mm50 = sum(ratios[-50:]) / 50.0
            st = "RISK-ON" if r_now > r_mm50 else "RISK-OFF"
            signals.append({
                "id": "credit_spread",
                "name": "Proxy Spread Crédito (HYG/IEF vs MM50)",
                "value": round(r_now, 4),
                "unit": "ratio",
                "signal": st,
                "rule": "Convenção: HYG/IEF > MM50 Risk-On | < MM50 Risk-Off",
            })
        else:
            signals.append({"id": "credit_spread", "name": "Proxy Spread Crédito (HYG/IEF vs MM50)", "value": INDISPONIVEL, "signal": INDISPONIVEL})
    else:
        signals.append({"id": "credit_spread", "name": "Proxy Spread Crédito (HYG/IEF vs MM50)", "value": INDISPONIVEL, "signal": INDISPONIVEL})

    available_signals = [s for s in signals if s["signal"] != INDISPONIVEL]
    avail_count = len(available_signals)
    on_count = sum(1 for s in available_signals if s["signal"] == "RISK-ON")
    off_count = sum(1 for s in available_signals if s["signal"] == "RISK-OFF")

    if avail_count == 0:
        regime = INDISPONIVEL
    elif on_count >= min_dir:
        regime = "RISK-ON"
    elif off_count >= min_dir:
        regime = "RISK-OFF"
    else:
        regime = "NEUTRO"

    return {
        "regime": regime,
        "available_count": avail_count,
        "total_signals": 4,
        "availability_label": f"{avail_count} de 4 sinais disponíveis",
        "risk_on_count": on_count,
        "risk_off_count": off_count,
        "aggregation_rule": regime_cfg.get("aggregation_rule"),
        "convention_note": regime_cfg.get("convention_note"),
        "signals": signals,
    }


def compute_correlation_matrix(
    candles_by_symbol: dict[str, dict[str, Any]],
    symbols: list[str],
    window_days: int = 126,
) -> dict[str, dict[str, float | str]]:
    """Matriz de correlação de Pearson sobre retornos diários alinhados."""
    ret_maps: dict[str, dict[str, float]] = {}
    for sym in symbols:
        res = candles_by_symbol.get(sym) or {}
        if res.get("status") != "ok" or not isinstance(res.get("candles"), list):
            continue
        candles = res["candles"][-(window_days + 1):]
        rmap = {}
        for i in range(1, len(candles)):
            p0 = float(candles[i - 1]["close"])
            p1 = float(candles[i]["close"])
            if p0 > 0:
                rmap[candles[i]["date"]] = (p1 / p0) - 1.0
        ret_maps[sym] = rmap

    matrix: dict[str, dict[str, float | str]] = {}
    for s1 in symbols:
        matrix[s1] = {}
        for s2 in symbols:
            if s1 == s2:
                matrix[s1][s2] = 1.0 if s1 in ret_maps else INDISPONIVEL
                continue
            if s1 not in ret_maps or s2 not in ret_maps:
                matrix[s1][s2] = INDISPONIVEL
                continue
            common = sorted(set(ret_maps[s1].keys()) & set(ret_maps[s2].keys()))
            if len(common) < 20:
                matrix[s1][s2] = INDISPONIVEL
                continue
            x = [ret_maps[s1][d] for d in common]
            y = [ret_maps[s2][d] for d in common]
            mx = sum(x) / len(x)
            my = sum(y) / len(y)
            num = sum((a - mx) * (b - my) for a, b in zip(x, y))
            den_x = math.sqrt(sum((a - mx) ** 2 for a in x))
            den_y = math.sqrt(sum((b - my) ** 2 for b in y))
            if den_x == 0 or den_y == 0:
                matrix[s1][s2] = INDISPONIVEL
            else:
                matrix[s1][s2] = round(num / (den_x * den_y), 2)
    return matrix


def check_portfolio_concentration(
    weights: list[dict[str, Any]],
    universe_map: dict[str, dict[str, Any]],
    max_bucket_pct: float = 55.0,
) -> list[dict[str, Any]]:
    """Detecta alertas de concentração por região, classe e moeda nas carteiras simuladas."""
    by_region: dict[str, float] = {}
    by_class: dict[str, float] = {}
    by_curr: dict[str, float] = {}

    for item in weights:
        sym = item.get("symbol", "")
        w = float(item.get("target_weight_pct", 0.0))
        meta = universe_map.get(sym) or {}
        reg = item.get("region") or meta.get("region") or ("Brasil" if sym.endswith(".SA") or "CDI" in sym else "Global")
        cls = item.get("asset_class") or meta.get("asset_class") or "Outros"
        cur = item.get("currency") or meta.get("currency") or ("BRL" if sym.endswith(".SA") or "CDI" in sym else "USD")
        by_region[reg] = round(by_region.get(reg, 0.0) + w, 2)
        by_class[cls] = round(by_class.get(cls, 0.0) + w, 2)
        by_curr[cur] = round(by_curr.get(cur, 0.0) + w, 2)

    alerts: list[dict[str, Any]] = []
    for dim, buckets in (("região", by_region), ("classe", by_class), ("moeda", by_curr)):
        for name, pct in buckets.items():
            if pct > max_bucket_pct:
                alerts.append({
                    "dimension": dim,
                    "bucket": name,
                    "weight_pct": pct,
                    "limit_pct": max_bucket_pct,
                    "message": f"Concentração elevada em {dim} '{name}': {pct}% (acima de {max_bucket_pct}%).",
                })
    return alerts


def build_candidate_explanation(
    cand: dict[str, Any],
    valuation: dict[str, Any],
    corr_matrix: dict[str, dict[str, float | str]],
    portfolio_symbols: list[str],
    high_corr_threshold: float = 0.75,
) -> dict[str, Any]:
    """Constrói motivos A FAVOR, CONTRA e DADOS USADOS para um CANDIDATO A ESTUDO."""
    sym = cand["symbol"]
    favor: list[str] = []
    contra: list[str] = []

    if cand["status"] == INDISPONIVEL:
        contra.append(f"Dados de preço {INDISPONIVEL} na janela consultada.")
        return {
            "symbol": sym,
            "label": "CANDIDATO A ESTUDO",
            "a_favor": favor,
            "contra": contra,
            "dados_usados": cand.get("data_used", {}),
            "valuation": valuation,
        }

    if cand.get("trend_above_mm200") is True:
        favor.append("Preço de fechamento acima da MM200 (tendência primária positiva).")
    elif cand.get("trend_above_mm200") is False:
        contra.append("Preço abaixo da MM200 (tendência primária negativa).")

    if cand.get("trend_mm50_above_mm200") is True:
        favor.append("MM50 acima da MM200 (estrutura de alta intermediária).")
    elif cand.get("trend_mm50_above_mm200") is False:
        contra.append("MM50 abaixo da MM200 (cruzamento baixista).")

    if isinstance(cand.get("momentum_12_1_pct"), (int, float)):
        if cand["momentum_12_1_pct"] > 0:
            favor.append(f"Momentum 12-1 positivo de +{cand['momentum_12_1_pct']}%.")
        else:
            contra.append(f"Momentum 12-1 negativo de {cand['momentum_12_1_pct']}%.")

    if isinstance(cand.get("rel_strength_12m_pp"), (int, float)):
        if cand["rel_strength_12m_pp"] > 0:
            favor.append(f"Força relativa de +{cand['rel_strength_12m_pp']} pp frente ao benchmark global ACWI.")
        else:
            contra.append(f"Desempenho inferior ao ACWI em 12m ({cand['rel_strength_12m_pp']} pp).")

    if isinstance(cand.get("volatility_ann_pct"), (int, float)) and cand["volatility_ann_pct"] > 25.0:
        contra.append(f"Volatilidade anualizada elevada ({cand['volatility_ann_pct']}% a.a.).")

    if isinstance(cand.get("max_drawdown_pct"), (int, float)) and abs(cand["max_drawdown_pct"]) > 20.0:
        contra.append(f"Drawdown máximo recente severo ({cand['max_drawdown_pct']}%).")

    if cand.get("currency") == "USD":
        contra.append("Exposição cambial em USD (impostos e IOF não modelados).")

    # Verifica correlação alta com ativos já na carteira simulada
    row_corr = corr_matrix.get(sym) or {}
    for p_sym in portfolio_symbols:
        if p_sym == sym:
            continue
        rho = row_corr.get(p_sym)
        if isinstance(rho, (int, float)) and rho >= high_corr_threshold:
            contra.append(f"Correlação alta (ρ = {rho}) com {p_sym} já presente na carteira simulada.")

    if valuation.get("status") == INDISPONIVEL:
        contra.append(f"Valuation manual {INDISPONIVEL} (não verificado).")
    elif valuation.get("status") == DADOS_DESATUALIZADOS:
        contra.append(f"Valuation com status '{DADOS_DESATUALIZADOS}'.")

    return {
        "symbol": sym,
        "label": "CANDIDATO A ESTUDO",
        "a_favor": favor,
        "contra": contra,
        "dados_usados": cand.get("data_used", {}),
        "valuation": valuation,
    }


def scan_global_opportunities(
    market_ctx: dict[str, Any] | None = None,
    asset_class_filter: str | None = None,
    region_filter: str | None = None,
) -> dict[str, Any]:
    """Executa o Radar Global completo de forma determinística e estrita."""
    ctx = market_ctx or {}
    cfg = market_data.load_strategies_config()
    radar_cfg = cfg.get("global_radar") or {}
    universe = radar_cfg.get("universe") or []
    score_weights = radar_cfg.get("score_weights") or {}
    bench_sym = radar_cfg.get("benchmark_symbol", "ACWI")
    fx_sym = radar_cfg.get("fx_symbol", "USDBRL=X")
    regime_cfg = radar_cfg.get("regime_rules") or {}
    corr_win = int(radar_cfg.get("correlation_window_days", 126))
    corr_thresh = float(radar_cfg.get("high_correlation_threshold", 0.75))

    candles_cache = dict(ctx.get("candles_by_symbol") or {})

    def _get_candles(sym: str, y_sym: str | None = None) -> dict[str, Any]:
        if sym in candles_cache:
            return candles_cache[sym]
        if y_sym and y_sym in candles_cache:
            return candles_cache[y_sym]
        res = market_data.get_strict_daily_candles(sym, yahoo_symbol=y_sym or sym, limit=300, allow_fallback=False)
        candles_cache[sym] = res
        return res

    bench_res = _get_candles(bench_sym, bench_sym)
    bench_closes = (
        [float(c["close"]) for c in bench_res["candles"]]
        if bench_res.get("status") == "ok" and isinstance(bench_res.get("candles"), list)
        else None
    )
    fx_res = _get_candles(fx_sym, fx_sym)

    # Regime macro (4 sinais)
    regime_symbols = [
        regime_cfg.get("vix_symbol", "^VIX"),
        regime_cfg.get("yield_10y_symbol", "^TNX"),
        regime_cfg.get("yield_3m_symbol", "^IRX"),
        regime_cfg.get("dxy_symbol", "DX-Y.NYB"),
        regime_cfg.get("credit_hyg_symbol", "HYG"),
        regime_cfg.get("credit_ief_symbol", "IEF"),
    ]
    regime_candles = {rs: _get_candles(rs, rs) for rs in regime_symbols}
    regime_info = classify_market_regime(regime_candles, regime_cfg)

    valuation_info = ctx.get("global_valuation") or load_global_valuation(
        reference_today=ctx.get("reference_today"),
    )

    # Coleta candles do universo e calcula métricas
    all_candidates: list[dict[str, Any]] = []
    for asset in universe:
        c_res = _get_candles(asset["symbol"], asset.get("yahoo_symbol"))
        metrics = compute_asset_radar_metrics(asset, c_res, bench_closes, fx_res, score_weights)
        all_candidates.append(metrics)

    # Ativos já presentes nas carteiras simuladas para detectar alta correlação
    portfolio_symbols: list[str] = []
    for p in database.list_strategy_portfolios():
        for w in p.get("current_weights", []):
            if w.get("symbol"):
                portfolio_symbols.append(w["symbol"])
    portfolio_symbols = sorted(set(portfolio_symbols))

    corr_symbols = [a["symbol"] for a in universe if candles_cache.get(a["symbol"], {}).get("status") == "ok"]
    corr_matrix = compute_correlation_matrix(candles_cache, corr_symbols[:10], window_days=corr_win)

    val_records = valuation_info.get("records") or {}
    for cand in all_candidates:
        sym = cand["symbol"]
        val_rec = val_records.get(sym, {"status": INDISPONIVEL, "verified": False})
        exp = build_candidate_explanation(cand, val_rec, corr_matrix, portfolio_symbols, corr_thresh)
        cand["a_favor"] = exp["a_favor"]
        cand["contra"] = exp["contra"]
        cand["valuation"] = val_rec

    # Ordena por score decrescente (indisponível vai para o fim)
    all_candidates.sort(
        key=lambda x: (1, float(x["score"])) if isinstance(x["score"], (int, float)) else (0, -9999.0),
        reverse=True,
    )

    filtered = all_candidates
    if asset_class_filter and asset_class_filter != "Todas":
        filtered = [c for c in filtered if c.get("asset_class") == asset_class_filter]
    if region_filter and region_filter != "Todas":
        filtered = [c for c in filtered if c.get("region") == region_filter]

    return {
        "label": "CANDIDATO A ESTUDO",
        "score_disclaimer": radar_cfg.get("score_disclaimer", "Pontuação heurística, sem poder preditivo comprovado."),
        "regime": regime_info,
        "candidates": filtered,
        "all_count": len(all_candidates),
        "correlation_matrix": corr_matrix,
        "correlation_window_days": corr_win,
        "governance_warnings": (cfg.get("governance") or {}).get("backtest_warnings", []),
    }


def explain_candidate(symbol: str, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retorna explicação detalhada (A FAVOR, CONTRA, DADOS USADOS) de um CANDIDATO A ESTUDO."""
    radar = scan_global_opportunities(market_ctx=market_ctx)
    target = next((c for c in radar["candidates"] if c["symbol"].upper() == symbol.upper()), None)
    if not target:
        return {"found": False, "symbol": symbol, "status": INDISPONIVEL}
    return {
        "found": True,
        "symbol": target["symbol"],
        "label": "CANDIDATO A ESTUDO",
        "score": target["score"],
        "score_disclaimer": radar["score_disclaimer"],
        "score_breakdown": target["score_breakdown"],
        "a_favor": target["a_favor"],
        "contra": target["contra"],
        "dados_usados": target["data_used"],
        "valuation": target["valuation"],
        "regime": radar["regime"],
    }
