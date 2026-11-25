"""Motor Determinístico do Gerente de Estratégias de Investimento (Camada A).

Regras rígidas:
- Somente funções determinísticas e puras (nenhum cálculo feito por LLM).
- Modo estrito: allow_fallback=False; dado ausente retorna 'indisponível' (nunca estimado).
- Point-in-time: estratégias fundamentalistas (Dividendos, Value, Qualidade) não fazem
  backtest histórico retroativo; executam apenas paper trading prospectivo.
- Estratégias baseadas em preço executam backtest diário base 100 sem look-ahead bias
  (decisão no fechamento t, execução em t+1 com corretagem + slippage).
- Calendários: união de datas com forward-fill limitado (<= 5 datas) e sinalizado; ativo nunca é
  excluído por diferença de calendário (B3/EUA/cripto); lacunas globais (> N dias) são detectadas.
"""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any

import calendar_fill
import database
import global_radar
import market_data

INDISPONIVEL = market_data.INDISPONIVEL
_MAX_FFILL = calendar_fill.DEFAULT_MAX_FILL


# ==============================================================================
# UTILITÁRIOS MATEMÁTICOS E ALINHAMENTO DE CALENDÁRIOS
# ==============================================================================
def sma(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / float(period)


def calc_atr_from_candles(candles: list[dict[str, Any]], period: int = 14) -> float | None:
    if len(candles) <= period or period <= 0:
        return None
    trs: list[float] = []
    for i in range(1, len(candles)):
        h = float(candles[i]["high"])
        l = float(candles[i]["low"])
        prev_c = float(candles[i - 1]["close"])
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / float(period)


def align_price_series(
    series_map: dict[str, list[dict[str, Any]]],
    max_gap_days: int = 1,
) -> dict[str, Any]:
    """Alinha séries diárias pela interseção exata de datas, sem forward-fill além de N dias.
    Registra lacunas entre pregões consecutivos superiores a max_gap_days úteis/corridos.
    """
    valid_symbols = [
        sym for sym, rows in series_map.items()
        if isinstance(rows, list) and len(rows) > 0
    ]
    if not valid_symbols:
        return {"dates": [], "aligned": {}, "gaps": [], "limiting_asset": INDISPONIVEL}

    date_maps: dict[str, dict[str, dict[str, Any]]] = {}
    earliest_by_sym: dict[str, str] = {}
    for sym in valid_symbols:
        dmap = {str(r["date"]): r for r in series_map[sym] if r.get("date") and r.get("close") is not None}
        if not dmap:
            return {"dates": [], "aligned": {}, "gaps": [], "limiting_asset": sym}
        date_maps[sym] = dmap
        earliest_by_sym[sym] = min(dmap.keys())

    # Etapa 3 (regra de calendário): união das datas a partir do início do ativo mais recente,
    # com forward-fill limitado (calendar_fill.DEFAULT_MAX_FILL) e sinalizado; nunca exclui ativo.
    limiting_asset = max(earliest_by_sym.items(), key=lambda kv: kv[1])[0]
    start_common = earliest_by_sym[limiting_asset]
    union_dates = sorted(d for d in set().union(*(set(dm.keys()) for dm in date_maps.values())) if d >= start_common)
    ffill_log: dict[str, int] = {}
    for sym in valid_symbols:
        dm = date_maps[sym]
        last = None
        run = 0
        n_fill = 0
        for d in union_dates:
            if d in dm:
                last = dm[d]
                run = 0
            elif last is not None and run < _MAX_FFILL:
                c = float(last["close"])
                dm[d] = {"date": d, "open": c, "high": c, "low": c, "close": c, "ffill": True}
                run += 1
                n_fill += 1
            else:
                run += 1
        ffill_log[sym] = n_fill
    common_dates = [d for d in union_dates if all(d in date_maps[s] for s in valid_symbols)]

    gaps: list[dict[str, Any]] = []
    # Em calendário B3/EUA fins de semana dão 3 dias corridos e feriados prolongados 4-5 dias.
    # Marcamos lacunas atípicas quando o salto excede (max_gap_days + 3) dias corridos.
    calendar_threshold = int(max_gap_days) + 3
    for i in range(1, len(common_dates)):
        d_prev = datetime.strptime(common_dates[i - 1], "%Y-%m-%d").date()
        d_curr = datetime.strptime(common_dates[i], "%Y-%m-%d").date()
        diff_days = (d_curr - d_prev).days
        if diff_days > calendar_threshold:
            gaps.append({
                "from": common_dates[i - 1],
                "to": common_dates[i],
                "calendar_days": diff_days,
            })

    aligned = {
        sym: [date_maps[sym][d] for d in common_dates]
        for sym in valid_symbols
    }
    return {
        "dates": common_dates,
        "aligned": aligned,
        "gaps": gaps,
        "limiting_asset": limiting_asset,
        "ffill_points": ffill_log,
    }


def compute_performance_metrics(
    equity_curve: list[dict[str, Any]],
    cdi_annual_pct: float | str | None = None,
) -> dict[str, Any]:
    """Calcula métricas institucionais sobre uma curva base 100."""
    if not equity_curve or len(equity_curve) < 2:
        return {
            "base": 100.0,
            "final_value": INDISPONIVEL,
            "total_return_pct": INDISPONIVEL,
            "return_12m_pct": INDISPONIVEL,
            "volatility_ann_pct": INDISPONIVEL,
            "max_drawdown_pct": INDISPONIVEL,
            "current_drawdown_pct": INDISPONIVEL,
            "sharpe_vs_cdi": INDISPONIVEL,
        }

    vals = [float(pt["value"]) for pt in equity_curve]
    start_val = vals[0]
    end_val = vals[-1]
    total_ret = ((end_val / start_val) - 1.0) * 100.0 if start_val > 0 else 0.0

    # Retorno 12m (últimos 252 pregões, se disponíveis)
    if len(vals) >= 252 and vals[-252] > 0:
        ret_12m: float | str = round(((end_val / vals[-252]) - 1.0) * 100.0, 2)
    else:
        ret_12m = round(total_ret, 2)

    daily_rets = [
        (vals[i] / vals[i - 1]) - 1.0
        for i in range(1, len(vals))
        if vals[i - 1] > 0
    ]
    n_days = len(daily_rets)
    if n_days >= 2:
        mean_r = sum(daily_rets) / n_days
        var_r = sum((r - mean_r) ** 2 for r in daily_rets) / (n_days - 1)
        vol_ann = math.sqrt(max(0.0, var_r)) * math.sqrt(252.0) * 100.0
        ann_ret = ((end_val / start_val) ** (252.0 / n_days) - 1.0) * 100.0 if start_val > 0 else 0.0
    else:
        vol_ann = 0.0
        ann_ret = total_ret

    peak = vals[0]
    max_dd = 0.0
    for v in vals:
        if v > peak:
            peak = v
        dd = ((v / peak) - 1.0) * 100.0 if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    curr_dd = ((end_val / peak) - 1.0) * 100.0 if peak > 0 else 0.0

    sharpe: float | str = INDISPONIVEL
    if isinstance(cdi_annual_pct, (int, float)) and vol_ann > 0.05:
        sharpe = round((ann_ret - float(cdi_annual_pct)) / vol_ann, 2)

    return {
        "base": 100.0,
        "final_value": round(end_val, 2),
        "total_return_pct": round(total_ret, 2),
        "return_12m_pct": ret_12m,
        "volatility_ann_pct": round(vol_ann, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "current_drawdown_pct": round(curr_dd, 2),
        "sharpe_vs_cdi": sharpe,
        "trading_days": n_days,
    }


def _build_cdi_curve_on_dates(
    dates: list[str],
    cdi_data: dict[str, Any],
) -> list[dict[str, Any]] | str:
    """Constrói curva base 100 do CDI real usando Série 12 SGS/BCB alinhada às datas."""
    if not dates or not isinstance(cdi_data, dict) or cdi_data.get("status") == INDISPONIVEL:
        return INDISPONIVEL
    rates_list = cdi_data.get("daily_rates")
    if not isinstance(rates_list, list) or not rates_list:
        return INDISPONIVEL
    rate_map = {str(r["date"]): float(r["rate_pct"]) / 100.0 for r in rates_list if r.get("date")}
    sorted_rate_dates = sorted(rate_map.keys())
    if not sorted_rate_dates:
        return INDISPONIVEL
    fallback_rate = rate_map[sorted_rate_dates[-1]]

    val = 100.0
    curve = [{"date": dates[0], "value": 100.0}]
    for dt in dates[1:]:
        r = rate_map.get(dt, fallback_rate)
        val *= (1.0 + r)
        curve.append({"date": dt, "value": round(val, 4)})
    return curve


def _build_asset_curve_on_dates(
    dates: list[str],
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]] | str:
    if not dates or not isinstance(candles, list) or len(candles) < 2:
        return INDISPONIVEL
    cmap = {str(c["date"]): float(c["close"]) for c in candles if c.get("date") and c.get("close")}
    if dates[0] not in cmap or cmap[dates[0]] <= 0:
        # Tenta alinhar pela interseção
        common = [d for d in dates if d in cmap and cmap[d] > 0]
        if len(common) < 2:
            return INDISPONIVEL
        base_px = cmap[common[0]]
        return [{"date": d, "value": round((cmap[d] / base_px) * 100.0, 4)} for d in common]
    base_px = cmap[dates[0]]
    curve = []
    last_val = 100.0
    for d in dates:
        px = cmap.get(d)
        if px and px > 0:
            last_val = round((px / base_px) * 100.0, 4)
        curve.append({"date": d, "value": last_val})
    return curve


# ==============================================================================
# INTERFACE BASE DAS ESTRATÉGIAS
# ==============================================================================
class BaseStrategy:
    strategy_id: str = ""
    supports_historical_backtest: bool = False
    backtest_mode: str = "prospective_paper_only"

    def __init__(self, cfg: dict[str, Any]):
        self.full_cfg = cfg
        self.meta = cfg["strategies"][self.strategy_id]
        self.params = self.meta.get("parametros") or {}
        self.gov = cfg.get("governance") or {}
        self.bt_cfg = cfg.get("backtest") or {}

    def metadata(self) -> dict[str, Any]:
        return {
            "id": self.strategy_id,
            "phase": self.meta.get("phase", 1),
            "enabled": bool(self.meta.get("enabled", False)),
            "nome": self.meta.get("nome"),
            "estilo": self.meta.get("estilo"),
            "investidor_inspiracao": self.meta.get("investidor_inspiracao"),
            "fundamento": self.meta.get("fundamento"),
            "regras_selecao": self.meta.get("regras_selecao", []),
            "regras_rebalanceamento": self.meta.get("regras_rebalanceamento", []),
            "principal_risco": self.meta.get("principal_risco"),
            "ultima_atualizacao": self.meta.get("ultima_atualizacao"),
            "parametros": self.params,
            "supports_historical_backtest": self.supports_historical_backtest,
            "backtest_mode": self.backtest_mode,
        }

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError


# ==============================================================================
# ESTRATÉGIA 1: DIVIDENDOS (INSPIRAÇÃO: LUIZ BARSI) — POINT-IN-TIME ONLY
# ==============================================================================
class DividendosBarsiStrategy(BaseStrategy):
    strategy_id = "dividendos_barsi"
    supports_historical_backtest = False
    backtest_mode = "prospective_paper_only"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = market_ctx or {}
        max_age = int(self.gov.get("fundamentals_max_age_days", 90))
        ref_today = ctx.get("reference_today")
        fundamentals = ctx.get("fundamentals") or market_data.load_b3_fundamentals(
            max_age_days=max_age,
            reference_today=ref_today,
        )

        min_dy = float(self.params.get("min_dy_12m_pct", 6.0))
        max_payout = float(self.params.get("max_payout_pct", 80.0))
        min_years = int(self.params.get("min_years_paying", 5))
        max_nd = float(self.params.get("max_net_debt_ebitda", 3.0))
        min_roe = float(self.params.get("min_roe_pct", 12.0))
        financial_sectors = set(self.params.get("financial_sectors") or ["Bancos", "Seguros"])
        min_assets = int(self.params.get("min_assets", 10))
        max_assets = int(self.params.get("max_assets", 15))
        max_asset_w = float(self.params.get("max_weight_per_asset_pct", 10.0))
        max_sector_w = float(self.params.get("max_weight_per_sector_pct", 25.0))

        alerts: list[dict[str, str]] = []
        if fundamentals.get("is_stale"):
            alerts.append({
                "level": "warning",
                "code": "STALE_FUNDAMENTALS",
                "message": (
                    f"Snapshot fundamentalista com {fundamentals.get('age_days')} dias "
                    f"(limite {max_age} dias): {market_data.DADOS_DESATUALIZADOS}."
                ),
            })

        eligible: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        missing_count = 0

        for st in fundamentals.get("stocks", []):
            vals = st.get("values") or {}
            dy = vals.get("dy_12m_pct")
            payout = vals.get("payout_pct")
            yrs = vals.get("years_paying")
            nd = vals.get("net_debt_ebitda")
            roe = vals.get("roe_pct")
            sector = st.get("sector", INDISPONIVEL)
            is_financial = sector in financial_sectors

            if not st.get("liquid_b3"):
                rejected.append({"symbol": st["symbol"], "reason": "Baixa liquidez B3"})
                continue
            if st.get("evento_corporativo"):
                rejected.append({
                    "symbol": st["symbol"],
                    "reason": f"Evento corporativo ativo: {st.get('corporate_event_reason') or 'mudança recente de política de dividendos'}",
                })
                continue
            req_vals = (dy, payout, yrs, roe, sector) if is_financial else (dy, payout, yrs, nd, sector)
            if any(v == INDISPONIVEL or v is None for v in req_vals):
                missing_count += 1
                rejected.append({
                    "symbol": st["symbol"],
                    "reason": f"Dado {INDISPONIVEL} ({', '.join(st.get('missing_fields', []))})",
                })
                continue

            reasons = []
            if float(dy) < min_dy:
                reasons.append(f"DY {dy}% < {min_dy}%")
            if float(payout) > max_payout:
                reasons.append(f"Payout {payout}% > {max_payout}%")
            if int(yrs) < min_years:
                reasons.append(f"Anos pagando {yrs} < {min_years}")
            if is_financial:
                if float(roe) < min_roe:
                    reasons.append(f"ROE {roe}% < {min_roe}%")
            elif float(nd) > max_nd:
                reasons.append(f"Dív.Líq/EBITDA {nd}x > {max_nd}x")

            if reasons:
                rejected.append({"symbol": st["symbol"], "reason": "; ".join(reasons)})
                continue

            eligible.append({
                "symbol": st["symbol"],
                "yahoo_symbol": st["yahoo_symbol"],
                "name": st["name"],
                "sector": sector,
                "dy_12m_pct": float(dy),
                "payout_pct": float(payout),
                "years_paying": int(yrs),
                "net_debt_ebitda": None if is_financial else float(nd),
                "roe_pct": float(roe) if (roe is not None and roe != INDISPONIVEL) else None,
                "data_date": st.get("reference_date"),
            })

        if missing_count > 0:
            alerts.append({
                "level": "info",
                "code": "MISSING_FUNDAMENTALS",
                "message": f"{missing_count} ativo(s) do universo com campo '{INDISPONIVEL}' ignorados na seleção.",
            })

        # Ordena por DY 12m decrescente e respeita teto por setor (25%) e por ativo (10%)
        eligible.sort(key=lambda x: x["dy_12m_pct"], reverse=True)
        selected: list[dict[str, Any]] = []
        sector_counts: dict[str, int] = {}
        # Com peso base <= 10% (min 10 ativos), teto de 25% por setor permite até 2 ativos por setor (20%)
        # ou 3 ativos se peso diluído <= 8.33%. Usamos cap iterativo exato abaixo.
        for cand in eligible:
            if len(selected) >= max_assets:
                break
            sec = cand["sector"]
            # Limite preliminar conservador para evitar violar 25% por setor ao normalizar
            max_per_sec_count = max(1, int(max_sector_w // (100.0 / max_assets)))
            if sector_counts.get(sec, 0) >= max_per_sec_count:
                continue
            selected.append(cand)
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

        if len(selected) < min_assets:
            alerts.append({
                "level": "warning",
                "code": "BELOW_MIN_ASSETS",
                "message": f"Apenas {len(selected)} ativos elegíveis (mínimo configurado: {min_assets}).",
            })

        # Distribui pesos respeitando teto de 10% por ativo e 25% por setor
        target_weights = _allocate_with_caps(
            selected,
            max_asset_pct=max_asset_w,
            max_sector_pct=max_sector_w,
        )

        allocated_pct = round(sum(x["target_weight_pct"] for x in target_weights), 2)
        completeness_msg = None
        if len(selected) < min_assets or allocated_pct < 99.9:
            rem_cdi = round(max(0.0, 100.0 - allocated_pct), 2)
            completeness_msg = f"carteira incompleta: {len(selected)} de {min_assets} ativos"
            if rem_cdi > 0:
                target_weights.append({
                    "symbol": "SELIC_CDI",
                    "name": "Tesouro Selic / CDI (Caixa Residual)",
                    "asset_class": "Renda Fixa",
                    "sector": "Renda Fixa / Liquidez",
                    "target_weight_pct": rem_cdi,
                    "dy_12m_pct": INDISPONIVEL,
                    "payout_pct": INDISPONIVEL,
                    "years_paying": INDISPONIVEL,
                    "net_debt_ebitda": INDISPONIVEL,
                })
            alerts.append({
                "level": "warning",
                "code": "INCOMPLETE_PORTFOLIO",
                "message": f"{completeness_msg}. Restante ({rem_cdi}%) alocado em CDI.",
            })

        backtest_info = {
            "mode": "prospective_paper_only",
            "available": False,
            "reason": (
                "Governança point-in-time: estratégias fundamentalistas (Dividendos) não realizam "
                "backtest histórico com snapshot atual para evitar look-ahead e viés retrospectivo. "
                "Acompanhamento exclusivo via paper trading prospectivo a partir de "
                f"{fundamentals.get('reference_date')}."
            ),
            "curve": [],
            "metrics": {
                "base": 100.0,
                "final_value": INDISPONIVEL,
                "total_return_pct": INDISPONIVEL,
                "return_12m_pct": INDISPONIVEL,
                "volatility_ann_pct": INDISPONIVEL,
                "max_drawdown_pct": INDISPONIVEL,
                "sharpe_vs_cdi": INDISPONIVEL,
            },
            "benchmarks": {},
            "warnings": self.gov.get("backtest_warnings", []),
        }

        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "target_weights": target_weights,
            "rejected": rejected,
            "alerts": alerts,
            "portfolio_completeness": completeness_msg or f"completa: {len(selected)} ativos",
            "fundamentals_status": fundamentals.get("freshness_label"),
            "fundamentals_reference_date": fundamentals.get("reference_date"),
            "backtest": backtest_info,
            "rule_used": (
                f"DY >= {min_dy}%, Payout <= {max_payout}%, {min_years}+ anos, "
                f"Dív.Líq/EBITDA <= {max_nd}x, teto {max_asset_w}%/ativo e {max_sector_w}%/setor."
            ),
        }


def _allocate_with_caps(
    items: list[dict[str, Any]],
    max_asset_pct: float,
    max_sector_pct: float,
) -> list[dict[str, Any]]:
    if not items:
        return []
    n = len(items)
    raw_w = min(max_asset_pct, round(100.0 / n, 2))
    weights = [raw_w for _ in items]

    # Garante teto setorial
    sec_totals: dict[str, float] = {}
    for idx, it in enumerate(items):
        sec = it["sector"]
        sec_totals[sec] = sec_totals.get(sec, 0.0) + weights[idx]
    for idx, it in enumerate(items):
        sec = it["sector"]
        if sec_totals[sec] > max_sector_pct and sec_totals[sec] > 0:
            scale = max_sector_pct / sec_totals[sec]
            weights[idx] = round(weights[idx] * scale, 2)

    # Redistribui eventual sobra apenas onde não estourar os tetos
    total = sum(weights)
    rem = round(100.0 - total, 2)
    if rem > 0.01:
        for _ in range(5):
            if rem <= 0.01:
                break
            for idx, it in enumerate(items):
                sec = it["sector"]
                cur_sec = sum(weights[j] for j, x in enumerate(items) if x["sector"] == sec)
                room_asset = max_asset_pct - weights[idx]
                room_sec = max_sector_pct - cur_sec
                add = min(rem, room_asset, room_sec)
                if add > 0.01:
                    weights[idx] = round(weights[idx] + add, 2)
                    rem = round(rem - add, 2)

    out = []
    for it, w in zip(items, weights):
        out.append({
            "symbol": it["symbol"],
            "name": it["name"],
            "asset_class": it["sector"],
            "sector": it["sector"],
            "target_weight_pct": round(w, 2),
            "dy_12m_pct": it["dy_12m_pct"],
            "payout_pct": it["payout_pct"],
            "years_paying": it["years_paying"],
            "net_debt_ebitda": it["net_debt_ebitda"],
            "roe_pct": it.get("roe_pct"),
        })
    return out


# ==============================================================================
# ESTRATÉGIA 2: INDEXAÇÃO PASSIVA (INSPIRAÇÃO: JOHN BOGLE) — BACKTEST t+1
# ==============================================================================
class IndexacaoBogleStrategy(BaseStrategy):
    strategy_id = "indexacao_bogle"
    supports_historical_backtest = True
    backtest_mode = "historical_price_t_plus_1"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = market_ctx or {}
        allocs = self.params.get("target_allocations") or []
        drift_band = float(self.params.get("drift_threshold_pp", 5.0))
        rebal_days = int(self.params.get("rebalance_period_days", 365))
        max_dd_alert = float(self.params.get("max_drawdown_alert_pct", 15.0))
        max_gap = int(self.bt_cfg.get("max_gap_days", 1))
        brokerage_bps = float(self.bt_cfg.get("brokerage_bps", 5.0))
        slippage_bps = float(self.bt_cfg.get("slippage_bps", 10.0))

        cdi_data = ctx.get("cdi_data") or market_data.fetch_bcb_cdi_series()
        series_map: dict[str, list[dict[str, Any]]] = {}
        target_weights: list[dict[str, Any]] = []
        alerts: list[dict[str, str]] = []
        price_sources: dict[str, str] = {}

        for item in allocs:
            sym = item["symbol"]
            target_weights.append({
                "symbol": sym,
                "name": item.get("label", sym),
                "asset_class": item.get("asset_class", sym),
                "target_weight_pct": float(item["target_weight_pct"]),
            })
            if item.get("source_type") == "BCB_CDI":
                price_sources[sym] = cdi_data.get("source", INDISPONIVEL)
                continue
            c_res = (ctx.get("candles_by_symbol") or {}).get(sym)
            if c_res is None:
                c_res = market_data.get_strict_daily_candles(
                    sym,
                    yahoo_symbol=item.get("yahoo_symbol"),
                    allow_fallback=False,
                )
            price_sources[sym] = c_res.get("source", INDISPONIVEL)
            if c_res.get("status") == "ok" and isinstance(c_res.get("candles"), list):
                series_map[sym] = c_res["candles"]
            else:
                alerts.append({
                    "level": "warning",
                    "code": "MISSING_PRICE_DATA",
                    "message": f"Série de preços para {sym} está '{INDISPONIVEL}'.",
                })

        if len(series_map) < 2 or cdi_data.get("status") == INDISPONIVEL:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": target_weights,
                "alerts": alerts + [{
                    "level": "warning",
                    "code": "BACKTEST_UNAVAILABLE",
                    "message": f"Backtest histórico {INDISPONIVEL} por falta de série real (sem estimativa).",
                }],
                "backtest": {
                    "mode": self.backtest_mode,
                    "available": False,
                    "reason": f"Dados reais {INDISPONIVEL}.",
                    "curve": [],
                    "metrics": compute_performance_metrics([]),
                    "benchmarks": {},
                    "warnings": self.gov.get("backtest_warnings", []),
                },
                "rule_used": f"Alocação fixa 40/30/30 com banda de desvio > {drift_band} pp ou rebalanceamento anual.",
            }

        aligned_info = align_price_series(series_map, max_gap_days=max_gap)
        dates = aligned_info["dates"]
        if len(dates) < 10:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": target_weights,
                "alerts": alerts + [{
                    "level": "warning",
                    "code": "INSUFFICIENT_OVERLAP",
                    "message": f"Interseção de datas insuficiente ({len(dates)} pregões): {INDISPONIVEL}.",
                }],
                "backtest": {
                    "mode": self.backtest_mode,
                    "available": False,
                    "reason": f"Interseção insuficiente ({len(dates)} pregões).",
                    "curve": [],
                    "metrics": compute_performance_metrics([]),
                    "benchmarks": {},
                    "warnings": self.gov.get("backtest_warnings", []),
                },
                "rule_used": "Alocação fixa 40/30/30.",
            }

        cdi_rates_map = {
            str(r["date"]): float(r["rate_pct"]) / 100.0
            for r in (cdi_data.get("daily_rates") or [])
            if r.get("date")
        }
        last_cdi_r = float(cdi_data.get("last_daily_rate_pct") or 0.0) / 100.0

        # Simulação diária sem look-ahead (sinal observado no fechamento t executa em t+1)
        weights_cfg = {it["symbol"]: float(it["target_weight_pct"]) / 100.0 for it in allocs}
        equity = 100.0
        holdings = {sym: equity * w for sym, w in weights_cfg.items()}
        curve = [{"date": dates[0], "value": 100.0}]
        pending_rebalance = False
        last_rebal_idx = 0
        cost_rate = (brokerage_bps + slippage_bps) / 10000.0
        rebalance_events = 0

        for t in range(1, len(dates)):
            dt = dates[t]
            # 1. Executa rebalanceamento sinalizado em t-1 (sem look-ahead)
            if pending_rebalance:
                total_eq = sum(holdings.values())
                turnover = 0.0
                new_holdings = {}
                for sym, w_tgt in weights_cfg.items():
                    tgt_val = total_eq * w_tgt
                    turnover += abs(tgt_val - holdings.get(sym, 0.0))
                    new_holdings[sym] = tgt_val
                tx_cost = (turnover * 0.5) * cost_rate
                total_after = max(0.0, total_eq - tx_cost)
                scale = total_after / total_eq if total_eq > 0 else 1.0
                holdings = {sym: val * scale for sym, val in new_holdings.items()}
                pending_rebalance = False
                last_rebal_idx = t
                rebalance_events += 1

            # 2. Aplica retorno real do dia t-1 -> t
            for sym in list(holdings.keys()):
                if sym == "SELIC_CDI":
                    r = cdi_rates_map.get(dt, last_cdi_r)
                    holdings[sym] *= (1.0 + r)
                else:
                    p_prev = float(aligned_info["aligned"][sym][t - 1]["close"])
                    p_curr = float(aligned_info["aligned"][sym][t]["close"])
                    if p_prev > 0:
                        holdings[sym] *= (p_curr / p_prev)

            total_eq = sum(holdings.values())
            curve.append({"date": dt, "value": round(total_eq, 4)})

            # 3. No fechamento de t, avalia desvio ou prazo para agendar execução em t+1
            max_drift_pp = 0.0
            if total_eq > 0:
                for sym, w_tgt in weights_cfg.items():
                    cur_w = holdings[sym] / total_eq
                    drift_pp = abs(cur_w - w_tgt) * 100.0
                    if drift_pp > max_drift_pp:
                        max_drift_pp = drift_pp
            if max_drift_pp > drift_band or (t - last_rebal_idx) >= int(rebal_days * 252 / 365):
                pending_rebalance = True

        cdi_annual = cdi_data.get("annual_rate_pct")
        metrics = compute_performance_metrics(curve, cdi_annual_pct=cdi_annual)
        if isinstance(metrics["max_drawdown_pct"], (int, float)) and abs(metrics["max_drawdown_pct"]) > max_dd_alert:
            alerts.append({
                "level": "warning",
                "code": "DRAWDOWN_LIMIT",
                "message": f"Drawdown máximo ({metrics['max_drawdown_pct']}%) ultrapassou o limite de -{max_dd_alert}%.",
            })

        benchmarks = _compute_benchmarks_for_dates(dates, ctx, cdi_data)
        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "target_weights": target_weights,
            "alerts": alerts,
            "price_sources": price_sources,
            "backtest": {
                "mode": self.backtest_mode,
                "available": True,
                "start_date": dates[0],
                "end_date": dates[-1],
                "limiting_asset": aligned_info["limiting_asset"],
                "calendar_gaps": aligned_info["gaps"],
                "rebalance_events": rebalance_events,
                "brokerage_bps": brokerage_bps,
                "slippage_bps": slippage_bps,
                "curve": curve,
                "metrics": metrics,
                "benchmarks": benchmarks,
                "warnings": self.gov.get("backtest_warnings", []),
            },
            "rule_used": f"Alocação 40% CDI / 30% BOVA11 / 30% IVVB11; rebalanceia em t+1 se desvio > {drift_band} pp ou anual.",
        }


# ==============================================================================
# ESTRATÉGIA 3: TREND FOLLOWING (INSPIRAÇÃO: TURTLES) — BACKTEST t+1
# ==============================================================================
class TrendFollowingTurtlesStrategy(BaseStrategy):
    strategy_id = "trend_following_turtles"
    supports_historical_backtest = True
    backtest_mode = "historical_price_t_plus_1"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = market_ctx or {}
        fast_n = int(self.params.get("fast_ma_days", 50))
        slow_n = int(self.params.get("slow_ma_days", 200))
        atr_n = int(self.params.get("atr_period_days", 14))
        atr_mult = float(self.params.get("atr_stop_multiplier", 2.0))
        max_w = float(self.params.get("max_weight_per_asset_pct", 25.0))
        rebal_days = int(self.params.get("rebalance_period_days", 7))
        max_dd_alert = float(self.params.get("max_drawdown_alert_pct", 20.0))
        max_gap = int(self.bt_cfg.get("max_gap_days", 1))
        brokerage_bps = float(self.bt_cfg.get("brokerage_bps", 5.0))
        slippage_bps = float(self.bt_cfg.get("slippage_bps", 10.0))
        universe = self.params.get("universe") or []

        cdi_data = ctx.get("cdi_data") or market_data.fetch_bcb_cdi_series()
        series_map: dict[str, list[dict[str, Any]]] = {}
        asset_meta: dict[str, dict[str, Any]] = {}
        alerts: list[dict[str, str]] = []

        for item in universe:
            sym = item["symbol"]
            asset_meta[sym] = item
            c_res = (ctx.get("candles_by_symbol") or {}).get(sym)
            if c_res is None:
                c_res = market_data.get_strict_daily_candles(
                    sym,
                    yahoo_symbol=item.get("yahoo_symbol"),
                    limit=max(420, slow_n + 260),
                    allow_fallback=False,
                )
            if c_res.get("status") == "ok" and isinstance(c_res.get("candles"), list) and len(c_res["candles"]) >= slow_n + 5:
                series_map[sym] = c_res["candles"]
            else:
                alerts.append({
                    "level": "info",
                    "code": "ASSET_HISTORY_UNAVAILABLE",
                    "message": f"{sym}: histórico mínimo ({slow_n}+ pregões) {INDISPONIVEL}.",
                })

        if not series_map or cdi_data.get("status") == INDISPONIVEL:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts + [{
                    "level": "warning",
                    "code": "BACKTEST_UNAVAILABLE",
                    "message": f"Trend Following {INDISPONIVEL} por falta de séries históricas suficientes.",
                }],
                "backtest": {
                    "mode": self.backtest_mode,
                    "available": False,
                    "reason": f"Dados históricos ou CDI {INDISPONIVEL}.",
                    "curve": [],
                    "metrics": compute_performance_metrics([]),
                    "benchmarks": {},
                    "warnings": self.gov.get("backtest_warnings", []),
                },
                "rule_used": f"Entrada Close > MM{slow_n} e MM{fast_n} > MM{slow_n}; saída < MM{slow_n} ou {atr_mult}x ATR({atr_n}).",
            }

        aligned_info = align_price_series(series_map, max_gap_days=max_gap)
        all_dates = aligned_info["dates"]
        if len(all_dates) <= slow_n + 5:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts + [{
                    "level": "warning",
                    "code": "INSUFFICIENT_HISTORY",
                    "message": f"Interseção comum ({len(all_dates)} pregões) menor que MM{slow_n}.",
                }],
                "backtest": {
                    "mode": self.backtest_mode,
                    "available": False,
                    "reason": f"Interseção menor que {slow_n} pregões.",
                    "curve": [],
                    "metrics": compute_performance_metrics([]),
                    "benchmarks": {},
                    "warnings": self.gov.get("backtest_warnings", []),
                },
                "rule_used": "Trend Following MM50/MM200 + ATR.",
            }

        cdi_rates_map = {
            str(r["date"]): float(r["rate_pct"]) / 100.0
            for r in (cdi_data.get("daily_rates") or [])
            if r.get("date")
        }
        last_cdi_r = float(cdi_data.get("last_daily_rate_pct") or 0.0) / 100.0

        reentry_n = int(self.params.get("reentry_new_high_days", 0) or 0)
        stopped_global: set[str] = set()

        def compute_signals_at(idx: int, active_peaks: dict[str, float], stopped: set[str] | None = None) -> dict[str, float]:
            stopped = stopped_global if stopped is None else stopped
            raw_inv_atr: dict[str, float] = {}
            for sym, candles in aligned_info["aligned"].items():
                sub = candles[: idx + 1]
                closes = [float(x["close"]) for x in sub]
                c_now = closes[-1]
                m_fast = sma(closes, fast_n)
                m_slow = sma(closes, slow_n)
                atr_val = calc_atr_from_candles(sub, atr_n)
                if m_fast is None or m_slow is None or atr_val is None or c_now <= 0:
                    continue

                if not (c_now > m_slow and m_fast > m_slow):
                    active_peaks.pop(sym, None)
                    continue
                # Variante C (autorizada): após stop 2xATR, reentra só com novo máximo de N dias
                if reentry_n and sym in stopped:
                    if c_now >= max(closes[-reentry_n:]):
                        stopped.discard(sym)
                    else:
                        continue
                prev_peak = active_peaks.get(sym, c_now)
                peak = max(prev_peak, c_now)
                stop_atr = peak - (atr_mult * atr_val)
                if c_now > stop_atr:
                    atr_pct = max(atr_val / c_now, 0.002)
                    raw_inv_atr[sym] = 1.0 / atr_pct
                    active_peaks[sym] = peak
                else:
                    active_peaks.pop(sym, None)
                    if reentry_n:
                        stopped.add(sym)

            if not raw_inv_atr:
                return {"CAIXA_CDI": 1.0}

            total_inv = sum(raw_inv_atr.values())
            w_map: dict[str, float] = {}
            cap = max_w / 100.0
            for sym, val in raw_inv_atr.items():
                w_map[sym] = min(cap, val / total_inv)
            allocated = sum(w_map.values())
            if allocated < 0.999:
                w_map["CAIXA_CDI"] = max(0.0, 1.0 - allocated)
            return w_map

        start_idx = slow_n
        bt_dates = all_dates[start_idx:]
        peaks: dict[str, float] = {}
        current_weights = compute_signals_at(start_idx, peaks)
        pending_weights: dict[str, float] | None = None
        equity = 100.0
        holdings = {k: equity * w for k, w in current_weights.items()}
        curve = [{"date": bt_dates[0], "value": 100.0}]
        cost_rate = (brokerage_bps + slippage_bps) / 10000.0
        rebalance_events = 0
        step_days = max(1, round(rebal_days * 5 / 7))

        for k in range(1, len(bt_dates)):
            idx = start_idx + k
            dt = bt_dates[k]

            if pending_weights is not None:
                total_eq = sum(holdings.values())
                all_keys = set(holdings.keys()) | set(pending_weights.keys())
                turnover = sum(abs((total_eq * pending_weights.get(s, 0.0)) - holdings.get(s, 0.0)) for s in all_keys)
                tx_cost = (turnover * 0.5) * cost_rate
                total_after = max(0.0, total_eq - tx_cost)
                holdings = {s: total_after * w for s, w in pending_weights.items() if w > 0}
                current_weights = pending_weights
                pending_weights = None
                rebalance_events += 1

            for sym in list(holdings.keys()):
                if sym == "CAIXA_CDI":
                    holdings[sym] *= (1.0 + cdi_rates_map.get(dt, last_cdi_r))
                else:
                    p_prev = float(aligned_info["aligned"][sym][idx - 1]["close"])
                    p_curr = float(aligned_info["aligned"][sym][idx]["close"])
                    if p_prev > 0:
                        holdings[sym] *= (p_curr / p_prev)

            total_eq = sum(holdings.values())
            curve.append({"date": dt, "value": round(total_eq, 4)})

            if k % step_days == 0 or k == len(bt_dates) - 1:
                next_w = compute_signals_at(idx, peaks)
                if next_w != current_weights:
                    pending_weights = next_w

        # Alvo atual no último pregão
        latest_weights_map = compute_signals_at(len(all_dates) - 1, dict(peaks), set(stopped_global))
        target_weights = []
        for sym, w in sorted(latest_weights_map.items(), key=lambda kv: kv[1], reverse=True):
            if sym == "CAIXA_CDI":
                target_weights.append({
                    "symbol": "CAIXA_CDI",
                    "name": "Caixa Remunerado (100% CDI)",
                    "asset_class": "Renda Fixa",
                    "target_weight_pct": round(w * 100.0, 2),
                })
            else:
                target_weights.append({
                    "symbol": sym,
                    "name": asset_meta[sym].get("symbol", sym),
                    "asset_class": asset_meta[sym].get("asset_class", "Ações"),
                    "target_weight_pct": round(w * 100.0, 2),
                })

        metrics = compute_performance_metrics(curve, cdi_annual_pct=cdi_data.get("annual_rate_pct"))
        if isinstance(metrics["max_drawdown_pct"], (int, float)) and abs(metrics["max_drawdown_pct"]) > max_dd_alert:
            alerts.append({
                "level": "warning",
                "code": "DRAWDOWN_LIMIT",
                "message": f"Drawdown máximo ({metrics['max_drawdown_pct']}%) excedeu -{max_dd_alert}%.",
            })

        benchmarks = _compute_benchmarks_for_dates(bt_dates, ctx, cdi_data)
        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "target_weights": target_weights,
            "alerts": alerts,
            "backtest": {
                "mode": self.backtest_mode,
                "available": True,
                "start_date": bt_dates[0],
                "end_date": bt_dates[-1],
                "limiting_asset": aligned_info["limiting_asset"],
                "calendar_gaps": aligned_info["gaps"],
                "rebalance_events": rebalance_events,
                "brokerage_bps": brokerage_bps,
                "slippage_bps": slippage_bps,
                "curve": curve,
                "metrics": metrics,
                "benchmarks": benchmarks,
                "warnings": self.gov.get("backtest_warnings", []),
            },
            "rule_used": f"Entrada Close > MM{slow_n} & MM{fast_n} > MM{slow_n}; peso ~ 1/ATR({atr_n}); caixa no CDI.",
        }


# ==============================================================================
# ESTRUTURA PRONTA DA FASE 2 (VALUE, QUALIDADE, FATORIAL)
# ==============================================================================
class Phase2PlaceholderStrategy(BaseStrategy):
    supports_historical_backtest = False
    backtest_mode = "prospective_paper_only"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "target_weights": [],
            "alerts": [{
                "level": "info",
                "code": "PHASE_2_READY",
                "message": "Estrutura registrada no catálogo e configurada para ativação na Fase 2.",
            }],
            "backtest": {
                "mode": self.backtest_mode,
                "available": False,
                "reason": "Estratégia estruturada para ativação na Fase 2 (paper trading prospectivo).",
                "curve": [],
                "metrics": compute_performance_metrics([]),
                "benchmarks": {},
                "warnings": self.gov.get("backtest_warnings", []),
            },
            "rule_used": "; ".join(self.meta.get("regras_selecao", [])),
        }


class ValueGrahamStrategy(Phase2PlaceholderStrategy):
    strategy_id = "value_graham"


class QualidadeCompoundersStrategy(Phase2PlaceholderStrategy):
    strategy_id = "qualidade_compounders"


class FatorialMultifactorStrategy(Phase2PlaceholderStrategy):
    strategy_id = "fatorial_multifactor"
    supports_historical_backtest = True
    backtest_mode = "historical_price_t_plus_1"


# ==============================================================================
# ESTRATÉGIAS GLOBAIS DA ETAPA 2B (SOMENTE PREÇO, BACKTEST t+1 COM CUSTOS)
# ==============================================================================
def _build_base_currency_series(
    candles: list[dict[str, Any]],
    asset_currency: str,
    base_currency: str,
    fx_map: dict[str, float] | None,
) -> list[dict[str, Any]] | None:
    """Converte série de preços para a moeda-base configurada (BRL ou USD) sem misturar moedas."""
    if asset_currency == base_currency:
        return candles
    if not fx_map:
        return None
    converted: list[dict[str, Any]] = []
    fx_dates = sorted(fx_map)
    import bisect
    for c in candles:
        dt = c["date"]
        fx = fx_map.get(dt)
        if not fx:
            # Regra de calendário: câmbio ausente na data usa a última cotação válida (até _MAX_FFILL datas)
            pos = bisect.bisect_left(fx_dates, dt) - 1
            if pos >= 0 and (bisect.bisect_left(fx_dates, dt) - pos) <= 1:
                prev_dt = fx_dates[pos]
                if (datetime.strptime(dt, "%Y-%m-%d") - datetime.strptime(prev_dt, "%Y-%m-%d")).days <= _MAX_FFILL + 2:
                    fx = fx_map[prev_dt]
        if not fx or fx <= 0:
            continue
        mult = fx if (asset_currency == "USD" and base_currency == "BRL") else (1.0 / fx)
        converted.append({
            "date": dt,
            "open": float(c["open"]) * mult,
            "high": float(c["high"]) * mult,
            "low": float(c["low"]) * mult,
            "close": float(c["close"]) * mult,
        })
    return converted if len(converted) >= 2 else None


class DualMomentumGlobalStrategy(BaseStrategy):
    strategy_id = "dual_momentum_global"
    supports_historical_backtest = True
    backtest_mode = "historical_price_t_plus_1"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = market_ctx or {}
        lookback = int(self.params.get("lookback_days", 252))
        rebal_days = int(self.params.get("rebalance_period_days", 30))
        base_curr = str(self.params.get("base_currency") or self.gov.get("base_currency", "BRL")).upper()
        candidates_cfg = self.params.get("candidates") or []
        usd_rf_sym = str(self.params.get("usd_risk_free_symbol", "SHY"))
        max_dd_alert = float(self.params.get("max_drawdown_alert_pct", 18.0))
        max_gap = int(self.bt_cfg.get("max_gap_days", 1))
        brokerage_bps = float(self.bt_cfg.get("brokerage_bps", 5.0))
        slippage_bps = float(self.bt_cfg.get("slippage_bps", 10.0))

        cdi_data = ctx.get("cdi_data") or market_data.fetch_bcb_cdi_series()
        candles_cache = ctx.get("candles_by_symbol") or {}
        alerts: list[dict[str, str]] = []

        # Carrega câmbio USDBRL=X se necessário para converter entre USD e BRL
        fx_res = candles_cache.get("USDBRL=X")
        if fx_res is None:
            fx_res = market_data.get_strict_daily_candles("USDBRL=X", yahoo_symbol="USDBRL=X", limit=420, allow_fallback=False)
        fx_map = (
            {c["date"]: float(c["close"]) for c in fx_res["candles"]}
            if isinstance(fx_res, dict) and fx_res.get("status") == "ok" and isinstance(fx_res.get("candles"), list)
            else None
        )

        series_map: dict[str, list[dict[str, Any]]] = {}
        meta_by_sym: dict[str, dict[str, Any]] = {}
        for item in candidates_cfg:
            sym = item["symbol"]
            meta_by_sym[sym] = item
            c_res = candles_cache.get(sym)
            if c_res is None:
                c_res = market_data.get_strict_daily_candles(sym, yahoo_symbol=item.get("yahoo_symbol", sym), limit=420, allow_fallback=False)
            if c_res.get("status") != "ok" or not isinstance(c_res.get("candles"), list):
                alerts.append({"level": "info", "code": "MISSING_ASSET", "message": f"{sym}: {INDISPONIVEL}."})
                continue
            conv = _build_base_currency_series(c_res["candles"], item.get("currency", "USD"), base_curr, fx_map)
            if conv and len(conv) > lookback + 5:
                series_map[sym] = conv
            else:
                alerts.append({"level": "info", "code": "INSUFFICIENT_OR_NO_FX", "message": f"{sym}: série em {base_curr} {INDISPONIVEL}."})

        # Ativo livre de risco na mesma moeda-base
        rf_sym = "SELIC_CDI" if base_curr == "BRL" else usd_rf_sym
        if base_curr == "USD":
            rf_res = candles_cache.get(usd_rf_sym) or market_data.get_strict_daily_candles(usd_rf_sym, yahoo_symbol=usd_rf_sym, limit=420, allow_fallback=False)
            if rf_res.get("status") == "ok" and isinstance(rf_res.get("candles"), list) and len(rf_res["candles"]) > lookback + 5:
                series_map[usd_rf_sym] = rf_res["candles"]
            else:
                series_map = {}

        if not series_map or (base_curr == "BRL" and cdi_data.get("status") == INDISPONIVEL):
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts + [{"level": "warning", "code": "BACKTEST_UNAVAILABLE", "message": f"Dual Momentum em {base_curr} {INDISPONIVEL}."}],
                "backtest": {"mode": self.backtest_mode, "available": False, "reason": f"Dados {INDISPONIVEL}.", "curve": [], "metrics": compute_performance_metrics([]), "benchmarks": {}, "warnings": self.gov.get("backtest_warnings", [])},
                "rule_used": f"Momentum 12m em {base_curr} vs ativo livre de risco em {base_curr} ({rf_sym}).",
            }

        aligned_info = align_price_series(series_map, max_gap_days=max_gap)
        all_dates = aligned_info["dates"]
        if len(all_dates) <= lookback + 5:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts,
                "backtest": {"mode": self.backtest_mode, "available": False, "reason": "Histórico comum insuficiente.", "curve": [], "metrics": compute_performance_metrics([]), "benchmarks": {}, "warnings": self.gov.get("backtest_warnings", [])},
                "rule_used": f"Dual Momentum ({base_curr}).",
            }

        cdi_rates_map = {str(r["date"]): float(r["rate_pct"]) / 100.0 for r in (cdi_data.get("daily_rates") or []) if r.get("date")}
        last_cdi_r = float(cdi_data.get("last_daily_rate_pct") or 0.0) / 100.0

        # Constrói índice acumulado do ativo livre de risco em BRL (CDI) para comparação na mesma moeda
        cdi_idx = [1.0]
        for dt in all_dates[1:]:
            cdi_idx.append(cdi_idx[-1] * (1.0 + cdi_rates_map.get(dt, last_cdi_r)))

        cand_syms = [s for s in series_map.keys() if s != usd_rf_sym]

        def pick_leader_at(idx: int) -> str:
            if base_curr == "BRL":
                rf_ret = (cdi_idx[idx] / cdi_idx[idx - lookback]) - 1.0
            else:
                rf_candles = aligned_info["aligned"][usd_rf_sym]
                rf_ret = (float(rf_candles[idx]["close"]) / float(rf_candles[idx - lookback]["close"])) - 1.0

            best_sym = rf_sym
            best_ret = rf_ret
            for sym in cand_syms:
                c_list = aligned_info["aligned"][sym]
                p0 = float(c_list[idx - lookback]["close"])
                p1 = float(c_list[idx]["close"])
                if p0 > 0:
                    r = (p1 / p0) - 1.0
                    if r > best_ret:
                        best_ret = r
                        best_sym = sym
            return best_sym

        start_idx = lookback
        bt_dates = all_dates[start_idx:]
        current_sym = pick_leader_at(start_idx)
        pending_sym: str | None = None
        equity = 100.0
        curve = [{"date": bt_dates[0], "value": 100.0}]
        cost_rate = (brokerage_bps + slippage_bps) / 10000.0
        rebalance_events = 0
        step_days = max(1, round(rebal_days * 21 / 30))

        for k in range(1, len(bt_dates)):
            idx = start_idx + k
            dt = bt_dates[k]
            if pending_sym is not None and pending_sym != current_sym:
                equity *= (1.0 - cost_rate)
                current_sym = pending_sym
                pending_sym = None
                rebalance_events += 1

            if current_sym == "SELIC_CDI":
                equity *= (1.0 + cdi_rates_map.get(dt, last_cdi_r))
            else:
                p_prev = float(aligned_info["aligned"][current_sym][idx - 1]["close"])
                p_curr = float(aligned_info["aligned"][current_sym][idx]["close"])
                if p_prev > 0:
                    equity *= (p_curr / p_prev)
            curve.append({"date": dt, "value": round(equity, 4)})

            if k % step_days == 0:
                nxt = pick_leader_at(idx)
                if nxt != current_sym:
                    pending_sym = nxt

        latest_sym = pick_leader_at(len(all_dates) - 1)
        target_weights = [{
            "symbol": latest_sym,
            "name": "Tesouro Selic / CDI (Proteção)" if latest_sym == "SELIC_CDI" else latest_sym,
            "asset_class": "Renda Fixa" if latest_sym == "SELIC_CDI" else "Global / Momentum",
            "region": "Brasil" if latest_sym in ("SELIC_CDI", "BOVA11.SA") else (meta_by_sym.get(latest_sym, {}).get("region", "Global")),
            "currency": base_curr,
            "br_equivalent": meta_by_sym.get(latest_sym, {}).get("br_equivalent"),
            "target_weight_pct": 100.0,
        }]

        metrics = compute_performance_metrics(curve, cdi_annual_pct=cdi_data.get("annual_rate_pct"))
        if isinstance(metrics["max_drawdown_pct"], (int, float)) and abs(metrics["max_drawdown_pct"]) > max_dd_alert:
            alerts.append({"level": "warning", "code": "DRAWDOWN_LIMIT", "message": f"Drawdown {metrics['max_drawdown_pct']}% excedeu -{max_dd_alert}%."})

        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "base_currency": base_curr,
            "risk_free_symbol": rf_sym,
            "target_weights": target_weights,
            "alerts": alerts,
            "backtest": {
                "mode": self.backtest_mode,
                "available": True,
                "start_date": bt_dates[0],
                "end_date": bt_dates[-1],
                "limiting_asset": aligned_info["limiting_asset"],
                "calendar_gaps": aligned_info["gaps"],
                "rebalance_events": rebalance_events,
                "brokerage_bps": brokerage_bps,
                "slippage_bps": slippage_bps,
                "curve": curve,
                "metrics": metrics,
                "benchmarks": _compute_benchmarks_for_dates(bt_dates, ctx, cdi_data),
                "warnings": self.gov.get("backtest_warnings", []),
            },
            "rule_used": f"Dual Momentum ({lookback}d) em {base_curr} contra {rf_sym} (mesma moeda); troca em t+1.",
        }


class RiskParitySimplifiedStrategy(BaseStrategy):
    strategy_id = "risk_parity_simplified"
    supports_historical_backtest = True
    backtest_mode = "historical_price_t_plus_1"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = market_ctx or {}
        vol_win = int(self.params.get("vol_window_days", 63))
        rebal_days = int(self.params.get("rebalance_period_days", 90))
        max_asset_pct = float(self.params.get("max_weight_per_asset_pct", 35.0))
        max_class_pct = float(self.params.get("max_weight_per_class_pct", 50.0))
        max_dd_alert = float(self.params.get("max_drawdown_alert_pct", 15.0))
        universe = self.params.get("universe") or []
        max_gap = int(self.bt_cfg.get("max_gap_days", 1))
        brokerage_bps = float(self.bt_cfg.get("brokerage_bps", 5.0))
        slippage_bps = float(self.bt_cfg.get("slippage_bps", 10.0))

        cdi_data = ctx.get("cdi_data") or market_data.fetch_bcb_cdi_series()
        candles_cache = ctx.get("candles_by_symbol") or {}
        base_curr = str(self.gov.get("base_currency", "BRL")).upper()
        fx_res = candles_cache.get("USDBRL=X")
        if fx_res is None and any(str(u.get("currency", "USD")).upper() != base_curr for u in universe):
            fx_res = market_data.get_strict_daily_candles("USDBRL=X", yahoo_symbol="USDBRL=X", limit=360, allow_fallback=False)
        fx_map = (
            {c["date"]: float(c["close"]) for c in fx_res["candles"]}
            if isinstance(fx_res, dict) and fx_res.get("status") == "ok" and isinstance(fx_res.get("candles"), list)
            else None
        )
        series_map: dict[str, list[dict[str, Any]]] = {}
        meta_by_sym: dict[str, dict[str, Any]] = {}
        alerts: list[dict[str, str]] = []

        for item in universe:
            sym = item["symbol"]
            meta_by_sym[sym] = item
            c_res = candles_cache.get(sym) or market_data.get_strict_daily_candles(sym, yahoo_symbol=item.get("yahoo_symbol", sym), limit=360, allow_fallback=False)
            if c_res.get("status") == "ok" and isinstance(c_res.get("candles"), list) and len(c_res["candles"]) > vol_win + 5:
                asset_curr = str(item.get("currency", "USD")).upper()
                conv = _build_base_currency_series(c_res["candles"], asset_curr, base_curr, fx_map)
                if conv and len(conv) > vol_win + 5:
                    series_map[sym] = conv
                else:
                    alerts.append({"level": "info", "code": "MISSING_FX", "message": f"{sym}: câmbio {base_curr} {INDISPONIVEL}."})
            else:
                alerts.append({"level": "info", "code": "MISSING_ASSET", "message": f"{sym}: {INDISPONIVEL}."})

        if len(series_map) < 2:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts + [{"level": "warning", "code": "BACKTEST_UNAVAILABLE", "message": f"Paridade de risco {INDISPONIVEL}."}],
                "backtest": {"mode": self.backtest_mode, "available": False, "reason": f"Dados {INDISPONIVEL}.", "curve": [], "metrics": compute_performance_metrics([]), "benchmarks": {}, "warnings": self.gov.get("backtest_warnings", [])},
                "rule_used": "Inverso da volatilidade sem alavancagem.",
            }

        aligned_info = align_price_series(series_map, max_gap_days=max_gap)
        all_dates = aligned_info["dates"]
        if len(all_dates) <= vol_win + 5:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts,
                "backtest": {"mode": self.backtest_mode, "available": False, "reason": "Histórico insuficiente.", "curve": [], "metrics": compute_performance_metrics([]), "benchmarks": {}, "warnings": self.gov.get("backtest_warnings", [])},
                "rule_used": "Inverso da volatilidade sem alavancagem.",
            }

        def calc_weights_at(idx: int) -> dict[str, float]:
            inv_vols: dict[str, float] = {}
            for sym, candles in aligned_info["aligned"].items():
                sub = [float(c["close"]) for c in candles[idx - vol_win: idx + 1]]
                rets = [(sub[i] / sub[i - 1]) - 1.0 for i in range(1, len(sub)) if sub[i - 1] > 0]
                if len(rets) < 10:
                    continue
                m = sum(rets) / len(rets)
                v = math.sqrt(max(1e-8, sum((r - m) ** 2 for r in rets) / (len(rets) - 1)))
                inv_vols[sym] = 1.0 / max(v, 0.0015)

            if not inv_vols:
                return {}
            tot = sum(inv_vols.values())
            w_pct = {s: (val / tot) * 100.0 for s, val in inv_vols.items()}

            # Aplica teto por ativo (35%) e teto por classe (50%) com water-filling sem violar tetos
            for _ in range(12):
                for s in list(w_pct.keys()):
                    if w_pct[s] > max_asset_pct:
                        w_pct[s] = max_asset_pct
                cls_sums: dict[str, float] = {}
                for s, w in w_pct.items():
                    cl = meta_by_sym[s].get("asset_class", "Outros")
                    cls_sums[cl] = cls_sums.get(cl, 0.0) + w
                for s in list(w_pct.keys()):
                    cl = meta_by_sym[s].get("asset_class", "Outros")
                    if cls_sums[cl] > max_class_pct and cls_sums[cl] > 0:
                        w_pct[s] *= max_class_pct / cls_sums[cl]
                rem = 100.0 - sum(w_pct.values())
                if rem <= 0.01:
                    break
                cls_sums = {}
                for s, w in w_pct.items():
                    cl = meta_by_sym[s].get("asset_class", "Outros")
                    cls_sums[cl] = cls_sums.get(cl, 0.0) + w
                elig = [
                    s for s in w_pct
                    if w_pct[s] < max_asset_pct - 0.01 and cls_sums[meta_by_sym[s].get("asset_class", "Outros")] < max_class_pct - 0.01
                ]
                if not elig:
                    break
                e_tot = sum(w_pct[s] for s in elig)
                for s in elig:
                    cl = meta_by_sym[s].get("asset_class", "Outros")
                    room_a = max_asset_pct - w_pct[s]
                    room_c = max_class_pct - cls_sums[cl]
                    add = min(room_a, room_c, rem * (w_pct[s] / e_tot if e_tot > 0 else 1.0 / len(elig)))
                    w_pct[s] += max(0.0, add)

            final_sum = sum(w_pct.values())
            if final_sum > 100.0001:
                return {s: w / final_sum for s, w in w_pct.items()}
            return {s: w / 100.0 for s, w in w_pct.items()}

        start_idx = vol_win
        bt_dates = all_dates[start_idx:]
        current_w = calc_weights_at(start_idx)
        pending_w: dict[str, float] | None = None
        equity = 100.0
        holdings = {s: equity * w for s, w in current_w.items()}
        curve = [{"date": bt_dates[0], "value": 100.0}]
        cost_rate = (brokerage_bps + slippage_bps) / 10000.0
        rebalance_events = 0
        step_days = max(1, round(rebal_days * 63 / 90))

        for k in range(1, len(bt_dates)):
            idx = start_idx + k
            dt = bt_dates[k]
            if pending_w is not None:
                total_eq = sum(holdings.values())
                turnover = sum(abs((total_eq * pending_w.get(s, 0.0)) - holdings.get(s, 0.0)) for s in set(holdings) | set(pending_w))
                total_after = max(0.0, total_eq - (turnover * 0.5) * cost_rate)
                holdings = {s: total_after * w for s, w in pending_w.items()}
                current_w = pending_w
                pending_w = None
                rebalance_events += 1

            for sym in list(holdings.keys()):
                p_prev = float(aligned_info["aligned"][sym][idx - 1]["close"])
                p_curr = float(aligned_info["aligned"][sym][idx]["close"])
                if p_prev > 0:
                    holdings[sym] *= (p_curr / p_prev)
            curve.append({"date": dt, "value": round(sum(holdings.values()), 4)})

            if k % step_days == 0:
                pending_w = calc_weights_at(idx)

        latest_w = calc_weights_at(len(all_dates) - 1)
        target_weights = [
            {
                "symbol": sym,
                "name": sym,
                "asset_class": meta_by_sym[sym].get("asset_class", "Global"),
                "region": meta_by_sym[sym].get("region", "Global"),
                "currency": meta_by_sym[sym].get("currency", "USD"),
                "br_equivalent": meta_by_sym[sym].get("br_equivalent"),
                "target_weight_pct": round(w * 100.0, 2),
            }
            for sym, w in sorted(latest_w.items(), key=lambda kv: kv[1], reverse=True)
        ]

        metrics = compute_performance_metrics(curve, cdi_annual_pct=cdi_data.get("annual_rate_pct"))
        if isinstance(metrics["max_drawdown_pct"], (int, float)) and abs(metrics["max_drawdown_pct"]) > max_dd_alert:
            alerts.append({"level": "warning", "code": "DRAWDOWN_LIMIT", "message": f"Drawdown {metrics['max_drawdown_pct']}% excedeu -{max_dd_alert}%."})

        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "target_weights": target_weights,
            "alerts": alerts,
            "backtest": {
                "mode": self.backtest_mode,
                "available": True,
                "start_date": bt_dates[0],
                "end_date": bt_dates[-1],
                "limiting_asset": aligned_info["limiting_asset"],
                "calendar_gaps": aligned_info["gaps"],
                "rebalance_events": rebalance_events,
                "brokerage_bps": brokerage_bps,
                "slippage_bps": slippage_bps,
                "curve": curve,
                "metrics": metrics,
                "benchmarks": _compute_benchmarks_for_dates(bt_dates, ctx, cdi_data),
                "warnings": self.gov.get("backtest_warnings", []),
            },
            "rule_used": f"Paridade de risco simplificada (1/vol {vol_win}d, sem alavancagem, teto {max_asset_pct}%/ativo e {max_class_pct}%/classe).",
        }


class RadarTopNStrategy(BaseStrategy):
    strategy_id = "radar_top_n"
    supports_historical_backtest = True
    backtest_mode = "historical_price_t_plus_1"

    def run(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = market_ctx or {}
        top_n = int(self.params.get("top_n", 5))
        min_hist = int(self.params.get("min_history_days", 252))
        rebal_days = int(self.params.get("rebalance_period_days", 30))
        max_dd_alert = float(self.params.get("max_drawdown_alert_pct", 22.0))
        max_gap = int(self.bt_cfg.get("max_gap_days", 1))
        brokerage_bps = float(self.bt_cfg.get("brokerage_bps", 5.0))
        slippage_bps = float(self.bt_cfg.get("slippage_bps", 10.0))

        radar_cfg = self.full_cfg.get("global_radar") or {}
        universe = radar_cfg.get("universe") or []
        score_weights = radar_cfg.get("score_weights") or {}
        bench_sym = radar_cfg.get("benchmark_symbol", "ACWI")

        cdi_data = ctx.get("cdi_data") or market_data.fetch_bcb_cdi_series()
        candles_cache = ctx.get("candles_by_symbol") or {}
        series_map: dict[str, list[dict[str, Any]]] = {}
        meta_by_sym: dict[str, dict[str, Any]] = {}
        alerts: list[dict[str, str]] = []

        for item in universe:
            sym = item["symbol"]
            meta_by_sym[sym] = item
            c_res = candles_cache.get(sym) or market_data.get_strict_daily_candles(sym, yahoo_symbol=item.get("yahoo_symbol", sym), limit=420, allow_fallback=False)
            if c_res.get("status") == "ok" and isinstance(c_res.get("candles"), list) and len(c_res["candles"]) > min_hist + 5:
                series_map[sym] = c_res["candles"]

        bench_res = candles_cache.get(bench_sym) or market_data.get_strict_daily_candles(bench_sym, yahoo_symbol=bench_sym, limit=420, allow_fallback=False)
        bench_map = {c["date"]: float(c["close"]) for c in (bench_res.get("candles") or [])} if bench_res.get("status") == "ok" else {}

        if len(series_map) < top_n:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts + [{"level": "warning", "code": "BACKTEST_UNAVAILABLE", "message": f"Radar Top-N {INDISPONIVEL} (histórico mínimo {min_hist}d insuficiente)."}],
                "backtest": {"mode": self.backtest_mode, "available": False, "reason": "Histórico insuficiente.", "curve": [], "metrics": compute_performance_metrics([]), "benchmarks": {}, "warnings": self.gov.get("backtest_warnings", [])},
                "rule_used": f"Top {top_n} do score heurístico do Radar Global.",
            }

        aligned_info = align_price_series(series_map, max_gap_days=max_gap)
        all_dates = aligned_info["dates"]
        if len(all_dates) <= min_hist + 5:
            return {
                "strategy_id": self.strategy_id,
                "metadata": self.metadata(),
                "target_weights": [],
                "alerts": alerts,
                "backtest": {"mode": self.backtest_mode, "available": False, "reason": "Interseção insuficiente.", "curve": [], "metrics": compute_performance_metrics([]), "benchmarks": {}, "warnings": self.gov.get("backtest_warnings", [])},
                "rule_used": f"Top {top_n} do score heurístico.",
            }

        def pick_top_n_at(idx: int) -> dict[str, float]:
            dt_slice = all_dates[: idx + 1]
            bench_closes = [bench_map[d] for d in dt_slice if d in bench_map] if bench_map else None
            scored: list[tuple[float, str]] = []
            for sym, candles in aligned_info["aligned"].items():
                sub_res = {"status": "ok", "source": "aligned", "price_adjusted": True, "candles": candles[: idx + 1]}
                m = global_radar.compute_asset_radar_metrics(meta_by_sym[sym], sub_res, bench_closes, None, score_weights)
                if isinstance(m.get("score"), (int, float)):
                    scored.append((float(m["score"]), sym))
            scored.sort(reverse=True)
            chosen = [sym for _, sym in scored[:top_n]]
            if not chosen:
                return {}
            w = 1.0 / len(chosen)
            return {s: w for s in chosen}

        start_idx = min_hist
        bt_dates = all_dates[start_idx:]
        current_w = pick_top_n_at(start_idx)
        pending_w: dict[str, float] | None = None
        equity = 100.0
        holdings = {s: equity * w for s, w in current_w.items()}
        curve = [{"date": bt_dates[0], "value": 100.0}]
        cost_rate = (brokerage_bps + slippage_bps) / 10000.0
        rebalance_events = 0
        step_days = max(1, round(rebal_days * 21 / 30))

        for k in range(1, len(bt_dates)):
            idx = start_idx + k
            dt = bt_dates[k]
            if pending_w is not None:
                total_eq = sum(holdings.values())
                turnover = sum(abs((total_eq * pending_w.get(s, 0.0)) - holdings.get(s, 0.0)) for s in set(holdings) | set(pending_w))
                total_after = max(0.0, total_eq - (turnover * 0.5) * cost_rate)
                holdings = {s: total_after * w for s, w in pending_w.items()}
                current_w = pending_w
                pending_w = None
                rebalance_events += 1

            for sym in list(holdings.keys()):
                p_prev = float(aligned_info["aligned"][sym][idx - 1]["close"])
                p_curr = float(aligned_info["aligned"][sym][idx]["close"])
                if p_prev > 0:
                    holdings[sym] *= (p_curr / p_prev)
            curve.append({"date": dt, "value": round(sum(holdings.values()), 4)})

            if k % step_days == 0:
                nxt = pick_top_n_at(idx)
                if nxt and nxt != current_w:
                    pending_w = nxt

        latest_w = pick_top_n_at(len(all_dates) - 1)
        target_weights = [
            {
                "symbol": sym,
                "name": meta_by_sym[sym].get("name", sym),
                "asset_class": meta_by_sym[sym].get("asset_class", "Global"),
                "region": meta_by_sym[sym].get("region", "Global"),
                "currency": meta_by_sym[sym].get("currency", "USD"),
                "br_equivalent": meta_by_sym[sym].get("br_equivalent"),
                "target_weight_pct": round(w * 100.0, 2),
            }
            for sym, w in latest_w.items()
        ]

        metrics = compute_performance_metrics(curve, cdi_annual_pct=cdi_data.get("annual_rate_pct"))
        if isinstance(metrics["max_drawdown_pct"], (int, float)) and abs(metrics["max_drawdown_pct"]) > max_dd_alert:
            alerts.append({"level": "warning", "code": "DRAWDOWN_LIMIT", "message": f"Drawdown {metrics['max_drawdown_pct']}% excedeu -{max_dd_alert}%."})

        return {
            "strategy_id": self.strategy_id,
            "metadata": self.metadata(),
            "score_disclaimer": radar_cfg.get("score_disclaimer", "Pontuação heurística, sem poder preditivo comprovado."),
            "target_weights": target_weights,
            "alerts": alerts,
            "backtest": {
                "mode": self.backtest_mode,
                "available": True,
                "start_date": bt_dates[0],
                "end_date": bt_dates[-1],
                "limiting_asset": aligned_info["limiting_asset"],
                "calendar_gaps": aligned_info["gaps"],
                "rebalance_events": rebalance_events,
                "brokerage_bps": brokerage_bps,
                "slippage_bps": slippage_bps,
                "curve": curve,
                "metrics": metrics,
                "benchmarks": _compute_benchmarks_for_dates(bt_dates, ctx, cdi_data),
                "warnings": self.gov.get("backtest_warnings", []),
            },
            "rule_used": f"Radar Top-{top_n} (pontuação heurística sem poder preditivo comprovado); rebalanceamento mensal t+1.",
        }


STRATEGY_CATALOG: dict[str, type[BaseStrategy]] = {
    "dividendos_barsi": DividendosBarsiStrategy,
    "indexacao_bogle": IndexacaoBogleStrategy,
    "trend_following_turtles": TrendFollowingTurtlesStrategy,
    "dual_momentum_global": DualMomentumGlobalStrategy,
    "risk_parity_simplified": RiskParitySimplifiedStrategy,
    "radar_top_n": RadarTopNStrategy,
    "value_graham": ValueGrahamStrategy,
    "qualidade_compounders": QualidadeCompoundersStrategy,
    "fatorial_multifactor": FatorialMultifactorStrategy,
}


def _compute_benchmarks_for_dates(
    dates: list[str],
    ctx: dict[str, Any],
    cdi_data: dict[str, Any],
) -> dict[str, Any]:
    """Calcula curvas base 100 e métricas dos benchmarks de retorno total (CDI, BOVA11.SA, IVVB11.SA)
    e da referência de índice de preço (^BVSP rotulado 'índice de preço, sem dividendos').
    """
    cdi_annual = cdi_data.get("annual_rate_pct")
    cdi_curve = _build_cdi_curve_on_dates(dates, cdi_data)
    out: dict[str, Any] = {
        "CDI": {
            "label": "CDI (BCB SGS Série 12)",
            "return_type": "total_return_cdi",
            "curve": cdi_curve if isinstance(cdi_curve, list) else [],
            "metrics": compute_performance_metrics(cdi_curve, cdi_annual) if isinstance(cdi_curve, list) else compute_performance_metrics([]),
        }
    }

    bench_defs = (
        ("BOVA11", "BOVA11.SA", "BOVA11.SA (Ajustado)", "total_return_adjusted"),
        ("IVVB11", "IVVB11.SA", "IVVB11.SA (Ajustado)", "total_return_adjusted"),
        ("IBOV_PRICE", "^BVSP", "Ibovespa ^BVSP (índice de preço, sem dividendos)", "price_index_only"),
    )
    candles_cache = ctx.get("candles_by_symbol") or {}
    for key, y_sym, label, rtype in bench_defs:
        c_res = candles_cache.get(key) or candles_cache.get(y_sym)
        if c_res is None:
            c_res = market_data.get_strict_daily_candles(y_sym, yahoo_symbol=y_sym, allow_fallback=False)
        if c_res.get("status") == "ok" and isinstance(c_res.get("candles"), list):
            b_curve = _build_asset_curve_on_dates(dates, c_res["candles"])
            if isinstance(b_curve, list):
                out[key] = {
                    "label": label,
                    "return_type": rtype,
                    "price_adjusted": bool(c_res.get("price_adjusted", False)),
                    "curve": b_curve,
                    "metrics": compute_performance_metrics(b_curve, cdi_annual),
                }
                continue
        out[key] = {
            "label": label,
            "return_type": rtype,
            "curve": [],
            "metrics": compute_performance_metrics([]),
            "status": INDISPONIVEL,
        }
    return out


# ==============================================================================
# ORQUESTRAÇÃO DO MOTOR DETERMINÍSTICO
# ==============================================================================
def list_strategies(cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    conf = cfg or market_data.load_strategies_config()
    items = []
    for sid, cls in STRATEGY_CATALOG.items():
        if sid in conf.get("strategies", {}):
            items.append(cls(conf).metadata())
    return items


def run_strategy(
    strategy_id: str,
    market_ctx: dict[str, Any] | None = None,
    persist: bool = True,
    actor: str = "motor_deterministico",
) -> dict[str, Any]:
    conf = market_data.load_strategies_config()
    if strategy_id not in STRATEGY_CATALOG:
        raise ValueError(f"Estratégia desconhecida: {strategy_id}")
    strat = STRATEGY_CATALOG[strategy_id](conf)
    result = strat.run(market_ctx=market_ctx)

    alerts = result.get("alerts") or []
    status = "ALERTA" if any(a.get("level") == "warning" for a in alerts) else "EM_DIA"

    if persist:
        existing = database.get_strategy_portfolio(strategy_id)
        current_w = existing.get("current_weights", []) if existing else []
        if not current_w and result.get("target_weights"):
            current_w = result["target_weights"]

        rebal = detect_rebalance_need(strategy_id, result["target_weights"], current_w, strat.params)
        if rebal["needs_rebalance"]:
            status = "REBALANCEAMENTO_PENDENTE" if status == "EM_DIA" else status

        database.upsert_strategy_portfolio(
            strategy_id=strategy_id,
            target_weights=result["target_weights"],
            current_weights=current_w,
            metrics=result.get("backtest", {}).get("metrics", {}),
            alerts=alerts,
            status=status,
        )
        database.log_strategy_decision(
            strategy_id=strategy_id,
            rule_ref=result.get("rule_used", ""),
            data_used={
                "status": status,
                "assets_count": len(result.get("target_weights", [])),
                "backtest_available": result.get("backtest", {}).get("available", False),
            },
            decision=f"Execução determinística concluída ({status}).",
            actor=actor,
        )

    result["status"] = status
    return result


def detect_rebalance_need(
    strategy_id: str,
    target_weights: list[dict[str, Any]],
    current_weights: list[dict[str, Any]],
    params: dict[str, Any],
) -> dict[str, Any]:
    drift_limit = float(params.get("drift_threshold_pp", 5.0))
    tgt_map = {w["symbol"]: float(w["target_weight_pct"]) for w in target_weights}
    cur_map = {w["symbol"]: float(w.get("current_weight_pct", w.get("target_weight_pct", 0.0))) for w in current_weights}
    all_syms = sorted(set(tgt_map.keys()) | set(cur_map.keys()))

    diffs = []
    max_drift = 0.0
    for s in all_syms:
        cw = cur_map.get(s, 0.0)
        tw = tgt_map.get(s, 0.0)
        d = round(tw - cw, 2)
        max_drift = max(max_drift, abs(d))
        if abs(d) > 0.01:
            diffs.append({"symbol": s, "current_pct": cw, "target_pct": tw, "delta_pp": d})

    needs = max_drift > drift_limit or set(tgt_map.keys()) != set(cur_map.keys())
    return {
        "strategy_id": strategy_id,
        "needs_rebalance": needs,
        "max_drift_pp": round(max_drift, 2),
        "threshold_pp": drift_limit,
        "diffs": diffs,
    }


def propose_rebalance(
    strategy_id: str,
    market_ctx: dict[str, Any] | None = None,
    actor: str = "agente_gerente",
) -> dict[str, Any]:
    """Gera uma proposta de rebalanceamento PENDENTE sem aplicá-la na carteira simulada."""
    res = run_strategy(strategy_id, market_ctx=market_ctx, persist=True, actor=actor)
    saved = database.get_strategy_portfolio(strategy_id) or {}
    current_w = saved.get("current_weights", [])
    target_w = res.get("target_weights", [])
    check = detect_rebalance_need(strategy_id, target_w, current_w, res["metadata"]["parametros"])

    if not target_w:
        return {"created": False, "reason": "Sem carteira-alvo gerada (dados indisponíveis).", "proposal": None}

    prop = database.create_strategy_proposal(
        strategy_id=strategy_id,
        proposal_type="REBALANCEAMENTO",
        rule_triggered=res.get("rule_used", "Regra de rebalanceamento da estratégia"),
        before_data=current_w,
        after_data=target_w,
        rationale=(
            f"Desvio máximo detectado: {check['max_drift_pp']} pp "
            f"(banda configurada: {check['threshold_pp']} pp)."
        ),
        data_snapshot={"diffs": check["diffs"]},
    )
    database.log_strategy_decision(
        strategy_id=strategy_id,
        rule_ref=res.get("rule_used", ""),
        data_used={"proposal_id": prop["id"], "max_drift_pp": check["max_drift_pp"]},
        decision=f"Proposta #{prop['id']} criada como PENDENTE aguardando aprovação de Admin.",
        actor=actor,
    )
    return {"created": True, "proposal": prop, "rebalance_check": check}


def approve_or_reject_proposal(
    proposal_id: int,
    action: str,
    admin_user: str,
    is_admin: bool = False,
) -> dict[str, Any]:
    """Aprova ou rejeita proposta. Apenas Admin autenticado pode invocar (validado na função)."""
    if not is_admin or not str(admin_user or "").strip():
        database.log_strategy_decision(
            strategy_id="governance",
            rule_ref="require_admin_for_approval",
            data_used={"proposal_id": proposal_id, "action": action, "actor": admin_user or "anon"},
            decision="Tentativa não autorizada de aprovar/rejeitar proposta bloqueada.",
            actor=str(admin_user or "anon"),
        )
        raise PermissionError("Aprovação ou rejeição de proposta exige autenticação de Admin.")

    action_up = action.upper().strip()
    if action_up not in ("APROVADA", "REJEITADA"):
        raise ValueError("Ação inválida. Use APROVADA ou REJEITADA.")

    prop = database.decide_strategy_proposal(proposal_id, action_up, decided_by=admin_user)
    if not prop:
        raise ValueError(f"Proposta #{proposal_id} não encontrada.")

    if action_up == "APROVADA":
        sid = prop["strategy_id"]
        saved = database.get_strategy_portfolio(sid) or {}
        new_weights = prop.get("after") or []
        database.upsert_strategy_portfolio(
            strategy_id=sid,
            target_weights=new_weights,
            current_weights=new_weights,
            metrics=saved.get("metrics", {}),
            alerts=saved.get("alerts", []),
            status="EM_DIA",
        )

    database.log_strategy_decision(
        strategy_id=prop["strategy_id"],
        rule_ref=prop["rule_triggered"],
        data_used={"proposal_id": proposal_id, "decided_by": admin_user},
        decision=f"Proposta #{proposal_id} {action_up} por {admin_user}.",
        actor=admin_user,
    )
    return prop
