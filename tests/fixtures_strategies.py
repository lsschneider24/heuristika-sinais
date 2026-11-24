"""Fixtures sintéticas determinísticas e sem rede para testes das estratégias."""

from __future__ import annotations

from datetime import date, timedelta
import math
from typing import Any


def make_business_dates(count: int = 280, start_date: str = "2025-10-01", gap_at_idx: int | None = None) -> list[str]:
    d = date.fromisoformat(start_date)
    out: list[str] = []
    while len(out) < count:
        if d.weekday() < 5:
            if gap_at_idx is not None and len(out) == gap_at_idx:
                d += timedelta(days=10)
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def make_synthetic_candles(
    dates: list[str],
    start_price: float = 100.0,
    daily_drift: float = 0.0008,
    osc_amp: float = 0.004,
) -> list[dict[str, Any]]:
    px = float(start_price)
    candles: list[dict[str, Any]] = []
    for idx, dt in enumerate(dates):
        ret = daily_drift + osc_amp * math.sin(idx * 0.25)
        px = max(1.0, px * (1.0 + ret))
        candles.append({
            "date": dt,
            "open": round(px * 0.998, 4),
            "high": round(px * 1.006, 4),
            "low": round(px * 0.994, 4),
            "close": round(px, 4),
        })
    return candles


def make_synthetic_cdi(dates: list[str], daily_rate_pct: float = 0.05) -> dict[str, Any]:
    annual_pct = round(((1.0 + daily_rate_pct / 100.0) ** 252 - 1.0) * 100.0, 2)
    return {
        "status": "ok",
        "source": "BCB_SGS_FIXTURE",
        "series_daily_id": 12,
        "series_annual_id": 4389,
        "last_date": dates[-1],
        "last_daily_rate_pct": daily_rate_pct,
        "annual_rate_pct": annual_pct,
        "daily_rates": [{"date": d, "rate_pct": daily_rate_pct} for d in dates],
        "from_cache": False,
    }


def make_offline_market_ctx(with_gap: bool = False) -> dict[str, Any]:
    dates_long = make_business_dates(280, start_date="2025-10-01", gap_at_idx=120 if with_gap else None)
    dates_short = dates_long[20:]  # Simula ativo com início posterior (limiting_asset)

    candles_by_symbol = {
        "BOVA11": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 115.0, 0.0007, 0.005),
        },
        "BOVA11.SA": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 115.0, 0.0007, 0.005),
        },
        "IVVB11": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 320.0, 0.0009, 0.004),
        },
        "IVVB11.SA": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 320.0, 0.0009, 0.004),
        },
        "^BVSP": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": False,
            "candles": make_synthetic_candles(dates_long, 125000.0, 0.0005, 0.005),
        },
        "PETR4": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_short, 34.0, 0.0011, 0.006),
        },
        "VALE3": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 58.0, 0.0004, 0.006),
        },
        "ITUB4": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 32.0, 0.0008, 0.004),
        },
        "WEGE3": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 45.0, -0.0003, 0.005),
        },
        "GC=F": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 2500.0, 0.0006, 0.003),
        },
        "BTC-USD": {
            "status": "ok",
            "source": "Fixture (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates_long, 80000.0, 0.0012, 0.012),
        },
    }

    return {
        "reference_today": "2026-11-23",
        "cdi_data": make_synthetic_cdi(dates_long),
        "candles_by_symbol": candles_by_symbol,
    }


def make_verified_b3_fundamentals(count: int = 12) -> dict[str, Any]:
    """Snapshot sintético verificado para testes unitários de seleção e tetos de Dividendos."""
    sectors = ["Bancos", "Energia Elétrica", "Seguros", "Saneamento", "Telecom", "Mineração & Siderurgia"]
    stocks = []
    by_sym = {}
    for i in range(count):
        sym = f"DIV{i+1:02d}"
        sec = sectors[i % len(sectors)]
        entry = {
            "symbol": sym,
            "yahoo_symbol": f"{sym}.SA",
            "name": f"Empresa Dividendos {i+1}",
            "sector": sec,
            "liquid_b3": True,
            "verified": True,
            "origin_type": "fixture_test",
            "fields": {},
            "values": {
                "dy_12m_pct": round(11.0 - i * 0.25, 2),
                "payout_pct": 55.0,
                "years_paying": 10,
                "net_debt_ebitda": 1.2,
                "roe_pct": 18.0,
            },
            "missing_fields": [],
            "has_missing_data": False,
            "reference_date": "2026-11-15",
            "is_stale": False,
            "freshness_label": "em_dia",
        }
        stocks.append(entry)
        by_sym[sym] = entry
    return {
        "status": "ok",
        "reference_date": "2026-11-15",
        "age_days": 8,
        "max_age_days": 90,
        "is_stale": False,
        "freshness_label": "em_dia",
        "universe_count": len(stocks),
        "stocks": stocks,
        "stocks_by_symbol": by_sym,
    }


def make_synthetic_b3_snapshot_json(reference_date: str = "2026-11-15", count: int = 32) -> dict[str, Any]:
    """Snapshot JSON sintético para testar load_b3_fundamentals sem depender do arquivo de produção."""
    stocks: list[dict[str, Any]] = []
    for i in range(count):
        if i == 0:
            sym = "SYN_UNVER"
            stocks.append({
                "symbol": sym,
                "yahoo_symbol": f"{sym}.SA",
                "name": "Sintética Não Verificada",
                "sector": "Bancos",
                "liquid_b3": True,
                "evento_corporativo": False,
                "verified": False,
                "fields": {
                    "dy_12m_pct": {"value": 8.0, "source": "Fixture sintética", "date": reference_date, "verified": False},
                    "payout_pct": {"value": 45.0, "source": "Fixture sintética", "date": reference_date, "verified": False},
                    "years_paying": {"value": 10, "source": "Fixture sintética", "date": reference_date, "verified": False},
                    "net_debt_ebitda": {"value": 0.0, "source": "Instituição Financeira", "date": reference_date, "verified": False},
                },
            })
        elif i == 1:
            sym = "SYN_MISS"
            stocks.append({
                "symbol": sym,
                "yahoo_symbol": f"{sym}.SA",
                "name": "Sintética Campo Ausente",
                "sector": "Holding & Energia",
                "liquid_b3": True,
                "evento_corporativo": False,
                "verified": False,
                "fields": {
                    "dy_12m_pct": {"value": 5.1, "source": "Fixture sintética", "date": reference_date, "verified": False},
                    "payout_pct": {"value": None, "source": "Dado ausente", "date": reference_date, "verified": False},
                    "years_paying": {"value": 8, "source": "Fixture sintética", "date": reference_date, "verified": False},
                    "net_debt_ebitda": {"value": None, "source": "Dado ausente", "date": reference_date, "verified": False},
                },
            })
        else:
            sym = f"SYN{i:02d}"
            stocks.append({
                "symbol": sym,
                "yahoo_symbol": f"{sym}.SA",
                "name": f"Sintética {i}",
                "sector": "Energia Elétrica",
                "liquid_b3": True,
                "evento_corporativo": False,
                "verified": True,
                "fields": {
                    "dy_12m_pct": {"value": 7.5, "source": "Fixture sintética", "date": reference_date, "verified": True},
                    "payout_pct": {"value": 55.0, "source": "Fixture sintética", "date": reference_date, "verified": True},
                    "years_paying": {"value": 10, "source": "Fixture sintética", "date": reference_date, "verified": True},
                    "net_debt_ebitda": {"value": 1.8, "source": "Fixture sintética", "date": reference_date, "verified": True},
                },
            })
    return {
        "schema_version": "1.1.0",
        "reference_date": reference_date,
        "max_age_days": 90,
        "stocks": stocks,
    }
