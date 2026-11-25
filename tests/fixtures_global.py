"""Fixtures sintéticas offline para o Radar Global de Oportunidades e estratégias globais."""

from __future__ import annotations

from typing import Any

from tests.fixtures_strategies import (
    make_business_dates,
    make_synthetic_candles,
    make_synthetic_cdi,
)


def make_global_offline_ctx(
    vix: float = 15.5,
    tnx_pct: float = 4.30,
    irx_pct: float = 3.80,
    dxy_trend: str = "down",
    credit_trend: str = "up",
) -> dict[str, Any]:
    dates = make_business_dates(300, start_date="2025-09-01")
    candles_by_symbol: dict[str, Any] = {}

    specs = {
        "IVV": (480.0, 0.0010, 0.004),
        "QQQ": (420.0, 0.0013, 0.006),
        "VGK": (65.0, 0.0004, 0.004),
        "EWJ": (68.0, 0.0005, 0.004),
        "EEM": (42.0, 0.0002, 0.005),
        "MCHI": (46.0, -0.0002, 0.007),
        "INDA": (51.0, 0.0007, 0.005),
        "BOVA11.SA": (118.0, 0.0005, 0.006),
        "EWZ": (28.0, 0.0003, 0.007),
        "TLT": (92.0, 0.0001, 0.004),
        "SHY": (82.0, 0.00018, 0.0005),  # baixa volatilidade para testar teto 35% na Paridade de Risco
        "HYG": (78.0, 0.0004 if credit_trend == "up" else -0.0003, 0.002),
        "IEF": (94.0, 0.0001, 0.002),
        "GLD": (220.0, 0.0008, 0.004),
        "DBC": (23.0, 0.0002, 0.005),
        "VNQ": (86.0, 0.0003, 0.005),
        "BTC-USD": (72000.0, 0.0014, 0.015),
        "ETH-USD": (2800.0, 0.0009, 0.016),
        "ACWI": (110.0, 0.0007, 0.0035),
        "USDBRL=X": (5.10, 0.0002, 0.003),
        "IVVB11.SA": (330.0, 0.0011, 0.004),
        "^BVSP": (126000.0, 0.0004, 0.005),
    }

    for sym, (s0, drift, amp) in specs.items():
        candles_by_symbol[sym] = {
            "status": "ok",
            "source": "Fixture Global (1d)",
            "price_adjusted": True,
            "candles": make_synthetic_candles(dates, s0, drift, amp),
        }

    # Séries macro de regime
    vix_series = [{"date": d, "open": vix, "high": vix + 0.5, "low": vix - 0.5, "close": vix} for d in dates]
    tnx_series = [{"date": d, "open": tnx_pct, "high": tnx_pct + 0.02, "low": tnx_pct - 0.02, "close": tnx_pct} for d in dates]
    irx_series = [{"date": d, "open": irx_pct, "high": irx_pct + 0.02, "low": irx_pct - 0.02, "close": irx_pct} for d in dates]
    dxy_drift = -0.0005 if dxy_trend == "down" else 0.0006
    dxy_series = make_synthetic_candles(dates, 105.0, dxy_drift, 0.001)

    candles_by_symbol["^VIX"] = {"status": "ok", "source": "Fixture", "candles": vix_series}
    candles_by_symbol["^TNX"] = {"status": "ok", "source": "Fixture", "candles": tnx_series}
    candles_by_symbol["^IRX"] = {"status": "ok", "source": "Fixture", "candles": irx_series}
    candles_by_symbol["DX-Y.NYB"] = {"status": "ok", "source": "Fixture", "candles": dxy_series}

    return {
        "reference_today": "2026-11-23",
        "cdi_data": make_synthetic_cdi(dates, daily_rate_pct=0.048),
        "candles_by_symbol": candles_by_symbol,
    }
