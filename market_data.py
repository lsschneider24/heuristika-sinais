"""Camada de dados estrita (Custo Zero) para o Gerente de Estratégias de Investimento:
- Carrega e valida strategies_config.json (versionado)
- Carrega data/b3_fundamentals.json com validação de campo ausente ('indisponível') e
  alerta de snapshot antigo (> 90 dias -> 'dados desatualizados')
- Consulta CDI real via API pública gratuita SGS do Banco Central do Brasil:
  * Série 12: Taxa de juros - CDI (% ao dia)
  * Série 4389: Taxa de juros - CDI anualizada base 252 (% a.a.)
- Consulta histórico diário (1d) via Yahoo Finance / Stooq em modo estrito
  (allow_fallback=False por padrão: NUNCA estima ou inventa preços; retorna 'indisponível').
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
import io
import json
import logging
from pathlib import Path
from typing import Any
import requests

import signals_engine

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STRATEGIES_CONFIG_PATH = BASE_DIR / "strategies_config.json"
FUNDAMENTALS_PATH = DATA_DIR / "b3_fundamentals.json"
CDI_CACHE_PATH = DATA_DIR / "cdi_sgs_cache.json"

INDISPONIVEL = "indisponível"
DADOS_DESATUALIZADOS = "dados desatualizados"

# Séries oficiais gratuitas do SGS - Banco Central do Brasil
BCB_SGS_CDI_DAILY_SERIES = 12     # Taxa de juros - CDI (% ao dia)
BCB_SGS_CDI_ANNUAL_SERIES = 4389  # Taxa de juros - CDI anualizada base 252 (% a.a.)

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeuristikaLab/1.0",
    "Accept": "application/json, text/plain, */*",
}


def load_strategies_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Lê o arquivo versionado strategies_config.json."""
    path = Path(config_path) if config_path else STRATEGIES_CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_strategies_config(data: dict[str, Any], config_path: Path | str | None = None) -> None:
    """Salva atualização aprovada no arquivo versionado strategies_config.json."""
    path = Path(config_path) if config_path else STRATEGIES_CONFIG_PATH
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_b3_fundamentals(
    snapshot_path: Path | str | None = None,
    max_age_days: int | None = None,
    reference_today: date | str | None = None,
) -> dict[str, Any]:
    """Carrega o snapshot fundamentalista da B3 com verificação de campos ausentes e defasagem (>90 dias)."""
    path = Path(snapshot_path) if snapshot_path else FUNDAMENTALS_PATH
    if not path.is_file():
        return {
            "status": INDISPONIVEL,
            "reference_date": INDISPONIVEL,
            "age_days": INDISPONIVEL,
            "max_age_days": max_age_days or 90,
            "is_stale": False,
            "freshness_label": INDISPONIVEL,
            "stocks": [],
            "stocks_by_symbol": {},
        }

    raw = json.loads(path.read_text(encoding="utf-8"))
    ref_date_str = str(raw.get("reference_date") or "").strip()
    configured_max_age = int(max_age_days if max_age_days is not None else raw.get("max_age_days", 90))

    if isinstance(reference_today, str):
        today_dt = datetime.strptime(reference_today[:10], "%Y-%m-%d").date()
    elif isinstance(reference_today, date):
        today_dt = reference_today
    else:
        today_dt = datetime.now().date()

    age_days: int | str = INDISPONIVEL
    is_stale = False
    freshness_label = "em_dia"

    if ref_date_str:
        try:
            ref_dt = datetime.strptime(ref_date_str[:10], "%Y-%m-%d").date()
            age_days = max(0, (today_dt - ref_dt).days)
            if age_days > configured_max_age:
                is_stale = True
                freshness_label = DADOS_DESATUALIZADOS
        except ValueError:
            age_days = INDISPONIVEL
            freshness_label = INDISPONIVEL
    else:
        ref_date_str = INDISPONIVEL
        freshness_label = INDISPONIVEL

    required_fields = ("dy_12m_pct", "payout_pct", "years_paying", "net_debt_ebitda")
    default_sources = raw.get("default_field_sources") or {}
    normalized_stocks: list[dict[str, Any]] = []
    by_symbol: dict[str, dict[str, Any]] = {}

    for item in raw.get("stocks", []):
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        raw_fields = item.get("fields") or {}
        norm_fields: dict[str, dict[str, Any]] = {}
        flat_values: dict[str, Any] = {}
        missing_fields: list[str] = []

        stock_verified = bool(item.get("verified", True))
        for fkey in required_fields:
            fobj = raw_fields.get(fkey)
            if isinstance(fobj, dict):
                val = fobj.get("value")
                src = fobj.get("source") or default_sources.get(fkey, INDISPONIVEL)
                fdate = fobj.get("date") or ref_date_str
                fverified = bool(fobj.get("verified", stock_verified))
            else:
                val = fobj
                src = default_sources.get(fkey, INDISPONIVEL)
                fdate = ref_date_str
                fverified = stock_verified

            if (not fverified) or val is None or val == "" or val == INDISPONIVEL:
                norm_val: Any = INDISPONIVEL
                missing_fields.append(fkey)
            else:
                try:
                    norm_val = float(val) if fkey != "years_paying" else int(val)
                except (TypeError, ValueError):
                    norm_val = INDISPONIVEL
                    missing_fields.append(fkey)

            norm_fields[fkey] = {
                "value": norm_val,
                "source": src,
                "date": fdate,
                "verified": fverified,
            }
            flat_values[fkey] = norm_val

        sector = item.get("sector") or INDISPONIVEL
        if sector == INDISPONIVEL:
            missing_fields.append("sector")

        stock_entry = {
            "symbol": symbol,
            "yahoo_symbol": item.get("yahoo_symbol") or f"{symbol}.SA",
            "name": item.get("name") or symbol,
            "sector": sector,
            "liquid_b3": bool(item.get("liquid_b3", True)),
            "evento_corporativo": bool(item.get("evento_corporativo", False)),
            "corporate_event_reason": item.get("corporate_event_reason"),
            "verified": stock_verified and len(missing_fields) == 0,
            "origin_type": item.get("origin_type") or raw.get("origin_type") or "manual_cvm_ri_snapshot",
            "fields": norm_fields,
            "values": flat_values,
            "missing_fields": missing_fields,
            "has_missing_data": len(missing_fields) > 0,
            "reference_date": ref_date_str,
            "is_stale": is_stale,
            "freshness_label": freshness_label,
        }
        normalized_stocks.append(stock_entry)
        by_symbol[symbol] = stock_entry

    return {
        "status": DADOS_DESATUALIZADOS if is_stale else "ok",
        "reference_date": ref_date_str,
        "age_days": age_days,
        "max_age_days": configured_max_age,
        "is_stale": is_stale,
        "freshness_label": freshness_label,
        "universe_count": len(normalized_stocks),
        "stocks": normalized_stocks,
        "stocks_by_symbol": by_symbol,
    }


def fetch_bcb_cdi_series(
    start_date: str | None = None,
    end_date: str | None = None,
    allow_cache: bool = True,
    cache_path: Path | str | None = None,
    timeout: int = 7,
) -> dict[str, Any]:
    """Consulta a série real do CDI no SGS do Banco Central do Brasil (gratuito):
    - Série 12: CDI diário (% a.d.)
    - Série 4389: CDI anualizado base 252 (% a.a.)
    Em caso de falha de rede sem cache válido, retorna 'indisponível' (nunca taxa fixa inventada).
    """
    cpath = Path(cache_path) if cache_path else CDI_CACHE_PATH
    today = datetime.now().date()
    dt_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else today
    dt_start = (
        datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date
        else (dt_end - timedelta(days=370))
    )

    d_ini_bcb = dt_start.strftime("%d/%m/%Y")
    d_fim_bcb = dt_end.strftime("%d/%m/%Y")

    url_s12 = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{BCB_SGS_CDI_DAILY_SERIES}/dados"
        f"?formato=json&dataInicial={d_ini_bcb}&dataFinal={d_fim_bcb}"
    )
    url_s4389 = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{BCB_SGS_CDI_ANNUAL_SERIES}/dados/ultimos/5"
        f"?formato=json"
    )

    try:
        resp12 = requests.get(url_s12, headers=_HTTP_HEADERS, timeout=timeout)
        resp12.raise_for_status()
        rows12 = resp12.json()
        if not isinstance(rows12, list) or len(rows12) == 0:
            raise ValueError("Série 12 do BCB retornou lista vazia.")

        daily_rates: list[dict[str, Any]] = []
        for r in rows12:
            raw_dt = str(r.get("data") or "").strip()
            raw_val = str(r.get("valor") or "").strip().replace(",", ".")
            if not raw_dt or not raw_val:
                continue
            iso_dt = datetime.strptime(raw_dt, "%d/%m/%Y").strftime("%Y-%m-%d")
            daily_rates.append({"date": iso_dt, "rate_pct": float(raw_val)})

        if not daily_rates:
            raise ValueError("Nenhum ponto diário válido na Série 12 do BCB.")

        annual_rate_pct: float | None = None
        try:
            resp4389 = requests.get(url_s4389, headers=_HTTP_HEADERS, timeout=timeout)
            resp4389.raise_for_status()
            rows4389 = resp4389.json()
            if isinstance(rows4389, list) and rows4389:
                last_val = str(rows4389[-1].get("valor") or "").strip().replace(",", ".")
                if last_val:
                    annual_rate_pct = round(float(last_val), 2)
        except Exception:
            annual_rate_pct = None

        if annual_rate_pct is None:
            last_daily = daily_rates[-1]["rate_pct"] / 100.0
            annual_rate_pct = round(((1.0 + last_daily) ** 252 - 1.0) * 100.0, 2)

        payload = {
            "status": "ok",
            "source": f"BCB_SGS (Série {BCB_SGS_CDI_DAILY_SERIES} diária / Série {BCB_SGS_CDI_ANNUAL_SERIES} anual)",
            "series_daily_id": BCB_SGS_CDI_DAILY_SERIES,
            "series_annual_id": BCB_SGS_CDI_ANNUAL_SERIES,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "last_date": daily_rates[-1]["date"],
            "last_daily_rate_pct": daily_rates[-1]["rate_pct"],
            "annual_rate_pct": annual_rate_pct,
            "daily_rates": daily_rates,
            "from_cache": False,
        }
        if allow_cache:
            try:
                cpath.parent.mkdir(parents=True, exist_ok=True)
                cpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                logger.debug("Não foi possível salvar cache do CDI: %s", exc)
        return payload
    except Exception as exc:
        logger.debug("Falha ao consultar SGS/BCB ao vivo: %s", exc)
        if allow_cache and cpath.is_file():
            try:
                cached = json.loads(cpath.read_text(encoding="utf-8"))
                if cached.get("daily_rates") and isinstance(cached.get("annual_rate_pct"), (int, float)):
                    cached["from_cache"] = True
                    cached["status"] = "cache"
                    return cached
            except Exception:
                pass

        return {
            "status": INDISPONIVEL,
            "source": INDISPONIVEL,
            "series_daily_id": BCB_SGS_CDI_DAILY_SERIES,
            "series_annual_id": BCB_SGS_CDI_ANNUAL_SERIES,
            "fetched_at": None,
            "last_date": INDISPONIVEL,
            "last_daily_rate_pct": INDISPONIVEL,
            "annual_rate_pct": INDISPONIVEL,
            "daily_rates": INDISPONIVEL,
            "from_cache": False,
        }


def _fetch_yahoo_daily_candles(yahoo_symbol: str, range_str: str = "2y", timeout: int = 7) -> tuple[list[dict[str, Any]], bool]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    resp = requests.get(
        url,
        params={"range": range_str, "interval": "1d"},
        headers=_HTTP_HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    adj_list = ((indicators.get("adjclose") or [{}])[0]).get("adjclose") or []
    has_adj = len(adj_list) == len(closes) and any(a is not None for a in adj_list)

    candles: list[dict[str, Any]] = []
    for idx, (ts, o, h, l, c) in enumerate(zip(timestamps, opens, highs, lows, closes)):
        if None in (h, l, c) or float(c) <= 0:
            continue
        c_f = float(c)
        o_f = float(o if o is not None else c_f)
        h_f = float(h)
        l_f = float(l)
        if has_adj and adj_list[idx] is not None:
            adj_f = float(adj_list[idx])
            factor = adj_f / c_f if c_f > 0 else 1.0
            o_f, h_f, l_f, c_f = o_f * factor, h_f * factor, l_f * factor, adj_f
        dt_str = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
        candles.append({
            "date": dt_str,
            "open": round(o_f, 6),
            "high": round(h_f, 6),
            "low": round(l_f, 6),
            "close": round(c_f, 6),
        })
    if len(candles) < 2:
        raise ValueError(f"Série diária insuficiente no Yahoo Finance para {yahoo_symbol}")
    return candles, has_adj


def _fetch_stooq_daily_candles(stooq_symbol: str, timeout: int = 7) -> list[dict[str, Any]]:
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    resp = requests.get(url, headers=_HTTP_HEADERS, timeout=timeout)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    candles: list[dict[str, Any]] = []
    for row in reader:
        dt_str = (row.get("Date") or "").strip()
        c_val = row.get("Close")
        h_val = row.get("High")
        l_val = row.get("Low")
        o_val = row.get("Open")
        if not dt_str or not c_val or c_val == "N/D":
            continue
        c_f = float(c_val)
        candles.append({
            "date": dt_str,
            "open": float(o_val) if (o_val and o_val != "N/D") else c_f,
            "high": float(h_val) if (h_val and h_val != "N/D") else c_f,
            "low": float(l_val) if (l_val and l_val != "N/D") else c_f,
            "close": c_f,
        })
    candles.sort(key=lambda x: x["date"])
    if len(candles) < 2:
        raise ValueError(f"Série diária insuficiente na Stooq para {stooq_symbol}")
    return candles


def get_strict_daily_candles(
    symbol: str,
    yahoo_symbol: str | None = None,
    stooq_symbol: str | None = None,
    limit: int = 300,
    allow_fallback: bool = False,
) -> dict[str, Any]:
    """Busca candles diários reais para estratégias e benchmarks.
    REGRA DE GOVERNANÇA: com allow_fallback=False (padrão obrigatório nas estratégias),
    NUNCA consome _generate_simulated_candles nem fallback_price; retorna 'indisponível'.
    """
    y_sym = yahoo_symbol
    if not y_sym and symbol:
        if symbol.endswith((".SA", "=F", "-USD")) or symbol.startswith("^"):
            y_sym = symbol
        else:
            y_sym = f"{symbol}.SA"

    if y_sym:
        try:
            candles, price_adjusted = _fetch_yahoo_daily_candles(y_sym)
            sliced = candles[-limit:] if limit else candles
            return {
                "status": "ok",
                "symbol": symbol,
                "source": "Yahoo Finance (1d)",
                "price_adjusted": price_adjusted,
                "is_simulated": False,
                "last_price": round(sliced[-1]["close"], 4),
                "last_date": sliced[-1]["date"],
                "candles": sliced,
            }
        except Exception as exc:
            logger.debug("Yahoo 1d falhou para %s (%s): %s", symbol, y_sym, exc)

    if stooq_symbol:
        try:
            candles = _fetch_stooq_daily_candles(stooq_symbol)
            sliced = candles[-limit:] if limit else candles
            return {
                "status": "ok",
                "symbol": symbol,
                "source": "Stooq (1d)",
                "price_adjusted": False,
                "is_simulated": False,
                "last_price": round(sliced[-1]["close"], 4),
                "last_date": sliced[-1]["date"],
                "candles": sliced,
            }
        except Exception as exc:
            logger.debug("Stooq 1d falhou para %s (%s): %s", symbol, stooq_symbol, exc)

    if not allow_fallback:
        return {
            "status": INDISPONIVEL,
            "symbol": symbol,
            "source": INDISPONIVEL,
            "price_adjusted": False,
            "is_simulated": False,
            "last_price": INDISPONIVEL,
            "last_date": INDISPONIVEL,
            "candles": INDISPONIVEL,
        }

    # Caso explícito fora das estratégias quando allow_fallback=True
    h, l, c = signals_engine._generate_simulated_candles(100.0, count=min(limit, 60))
    today = datetime.now().date()
    sim_candles = [
        {
            "date": (today - timedelta(days=len(c) - 1 - idx)).strftime("%Y-%m-%d"),
            "open": round(c[idx], 4),
            "high": round(h[idx], 4),
            "low": round(l[idx], 4),
            "close": round(c[idx], 4),
        }
        for idx in range(len(c))
    ]
    return {
        "status": "SIMULADO",
        "symbol": symbol,
        "source": "SIMULADO (Contingência Local)",
        "is_simulated": True,
        "last_price": sim_candles[-1]["close"],
        "last_date": sim_candles[-1]["date"],
        "candles": sim_candles,
    }
