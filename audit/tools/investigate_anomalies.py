"""Investigação de anomalias (Etapa 2C/2D - Item C)."""

from __future__ import annotations

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
VENV_SITE = BASE_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE.is_dir():
    sys.path.insert(0, str(VENV_SITE))

import market_data  # noqa: E402
import strategies_engine  # noqa: E402


def main() -> int:
    # 1. Dual Momentum month-by-month trace
    cfg = market_data.load_strategies_config()["strategies"]["dual_momentum_global"]["parametros"]
    cdi_data = market_data.fetch_bcb_cdi_series()
    fx_res = market_data.get_strict_daily_candles("USDBRL=X", yahoo_symbol="USDBRL=X", limit=420, allow_fallback=False)
    fx_map = {c["date"]: float(c["close"]) for c in fx_res["candles"]}
    series_map = {}
    for item in cfg["candidates"]:
        sym = item["symbol"]
        c_res = market_data.get_strict_daily_candles(sym, yahoo_symbol=item["yahoo_symbol"], limit=420, allow_fallback=False)
        series_map[sym] = strategies_engine._build_base_currency_series(c_res["candles"], item["currency"], "BRL", fx_map)
    aligned = strategies_engine.align_price_series(series_map, max_gap_days=1)
    dates = aligned["dates"]
    cdi_map = {str(r["date"]): float(r["rate_pct"]) / 100.0 for r in cdi_data["daily_rates"]}
    last_cdi = float(cdi_data["last_daily_rate_pct"]) / 100.0
    cdi_idx = [1.0]
    for dt in dates[1:]:
        cdi_idx.append(cdi_idx[-1] * (1.0 + cdi_map.get(dt, last_cdi)))

    lookback = 252
    step = 21
    print("=== DUAL MOMENTUM TRACE (2y window, limit=420) ===")
    print(f"Total aligned dates: {len(dates)} ({dates[0]} .. {dates[-1]}), backtest starts at idx={lookback} ({dates[lookback]})")
    for idx in range(lookback, len(dates), step):
        dt = dates[idx]
        moms = {"CDI": round((cdi_idx[idx] / cdi_idx[idx - lookback] - 1.0) * 100.0, 2)}
        for sym, cl in aligned["aligned"].items():
            moms[sym] = round((float(cl[idx]["close"]) / float(cl[idx - lookback]["close"]) - 1.0) * 100.0, 2)
        best = max(moms, key=lambda k: moms[k])
        nxt_idx = min(len(dates) - 1, idx + step)
        if best == "CDI":
            m_ret = round((cdi_idx[nxt_idx] / cdi_idx[idx] - 1.0) * 100.0, 2)
        else:
            cl = aligned["aligned"][best]
            m_ret = round((float(cl[nxt_idx]["close"]) / float(cl[idx]["close"]) - 1.0) * 100.0, 2)
        print(f"{dt} -> {dates[nxt_idx]} | chosen={best:<10} | moms={moms} | period_ret={m_ret}%")

    # 2. Indexação vs weighted benchmarks
    res_idx = strategies_engine.run_strategy("indexacao_bogle", persist=False)
    bt_idx = res_idx["backtest"]
    bms = bt_idx["benchmarks"]
    r_cdi = bms["CDI"]["metrics"]["total_return_pct"]
    r_bova = bms["BOVA11"]["metrics"]["total_return_pct"]
    r_ivvb = bms["IVVB11"]["metrics"]["total_return_pct"]
    weighted = round(0.4 * r_cdi + 0.3 * r_bova + 0.3 * r_ivvb, 2)
    print("\n=== INDEXACAO BOGLE ===")
    print(f"Portfolio={bt_idx['metrics']['total_return_pct']}% vs Weighted(40/30/30)={weighted}% (CDI={r_cdi}%, BOVA11={r_bova}%, IVVB11={r_ivvb}%), rebal_events={bt_idx['rebalance_events']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
