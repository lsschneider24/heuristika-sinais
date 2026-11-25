"""Testes de regressão da Etapa 3 Parte 1: calendários distintos nas 5 estratégias e regra geral de payout."""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import calendar_fill
import strategies_engine
from tests.fixtures_strategies import make_offline_market_ctx


class CalendarAndQualityRegressionTestCase(unittest.TestCase):
    def _ctx_with_holiday_gaps(self) -> dict:
        ctx = make_offline_market_ctx(with_gap=False)
        # Simula feriados distintos: remove datas diferentes em B3 (BOVA11.SA/PETR4.SA), EUA (IVV/TLT) e mantém BTC-USD
        for sym, drop_idxs in [
            ("BOVA11.SA", {210, 260}),
            ("IVVB11.SA", {215, 265}),
            ("IVV", {215, 265}),
            ("TLT", {215, 265}),
            ("PETR4.SA", {210, 260}),
        ]:
            if sym in ctx["candles_by_symbol"] and ctx["candles_by_symbol"][sym].get("status") == "ok":
                cs = ctx["candles_by_symbol"][sym]["candles"]
                ctx["candles_by_symbol"][sym]["candles"] = [c for idx, c in enumerate(cs) if idx not in drop_idxs]
        return ctx

    def test_all_5_strategies_preserve_assets_across_calendar_holidays(self) -> None:
        ctx = self._ctx_with_holiday_gaps()
        for sid in (
            "indexacao_bogle",
            "trend_following_turtles",
            "dual_momentum_global",
            "risk_parity_simplified",
            "radar_top_n",
        ):
            with self.subTest(strategy_id=sid):
                res = strategies_engine.run_strategy(sid, market_ctx=ctx, persist=False)
                bt = res["backtest"]
                self.assertTrue(bt["available"], f"{sid} falhou com lacunas de feriado")
                self.assertGreater(len(res["target_weights"]), 0)

    def test_calendar_fill_flags_and_never_drops_within_max_fill(self) -> None:
        base = datetime(2025, 1, 1)
        dates = [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10)]
        px = {
            "B3": {d: 100.0 + i for i, d in enumerate(dates) if i != 4},   # 1 dia de feriado
            "EUA": {d: 200.0 + i for i, d in enumerate(dates) if i != 5},  # 1 dia de feriado diferente
            "CRIPTO": {d: 300.0 + i for i, d in enumerate(dates)},         # todos os dias
        }
        filled, log = calendar_fill.ffill_price_maps(px, dates, max_fill=5)
        self.assertEqual(log["B3"], 1)
        self.assertEqual(log["EUA"], 1)
        self.assertEqual(log["CRIPTO"], 0)
        self.assertEqual(filled["B3"][dates[4]], px["B3"][dates[3]])
        self.assertEqual(filled["EUA"][dates[5]], px["EUA"][dates[4]])

    def test_local_cache_integrity_and_stale_flag(self) -> None:
        import local_cache
        key = "test_cache_key_unit"
        p = local_cache.save_cache_entry("unit_test", key, {"x": 42})
        hit = local_cache.load_cache_entry("unit_test", key, max_age_hours=24.0)
        self.assertTrue(hit["hit"])
        self.assertFalse(hit["stale"])
        self.assertEqual(hit["payload"]["x"], 42)
        stale_hit = local_cache.load_cache_entry("unit_test", key, max_age_hours=-1.0)
        self.assertTrue(stale_hit["hit"])
        self.assertTrue(stale_hit["stale"])
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
