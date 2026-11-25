"""Testes específicos obrigatórios de governança, look-ahead, custos e modo estrito (Parte 3)."""

import copy
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import config

_tmp_audit_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
_tmp_audit_db.close()
config.DB_PATH = _tmp_audit_db.name
config.DATABASE_PATH = _tmp_audit_db.name

import database  # noqa: E402
import market_data  # noqa: E402
import signals_engine  # noqa: E402
import strategies_engine  # noqa: E402
from tests.fixtures_strategies import (  # noqa: E402
    make_offline_market_ctx,
    make_verified_b3_fundamentals,
)


class AuditSpecificsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        database.seed_initial_data(force=True)

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(config.DB_PATH)
        except OSError:
            pass

    def test_a_no_lookahead_future_prices_do_not_change_past_decisions(self):
        ctx_base = make_offline_market_ctx(with_gap=False)
        ctx_future_shock = copy.deepcopy(ctx_base)
        # Altera drasticamente os últimos 20 pregões futuros em todos os ativos
        for sym, payload in ctx_future_shock["candles_by_symbol"].items():
            candles = payload["candles"]
            for i in range(len(candles) - 20, len(candles)):
                candles[i]["close"] *= 0.45
                candles[i]["high"] *= 0.45
                candles[i]["low"] *= 0.45

        res_base = strategies_engine.run_strategy("trend_following_turtles", market_ctx=ctx_base, persist=False)
        res_shock = strategies_engine.run_strategy("trend_following_turtles", market_ctx=ctx_future_shock, persist=False)

        curve_base = res_base["backtest"]["curve"]
        curve_shock = res_shock["backtest"]["curve"]
        cutoff = len(curve_base) - 21
        self.assertEqual(curve_base[:cutoff], curve_shock[:cutoff])

    def test_b_execution_t_plus_1_with_brokerage_and_slippage(self):
        ctx = make_offline_market_ctx(with_gap=False)
        # Força um rebalanceamento imediato com custos altos vs custo zero
        cfg_zero = market_data.load_strategies_config()
        cfg_zero["backtest"]["brokerage_bps"] = 0.0
        cfg_zero["backtest"]["slippage_bps"] = 0.0
        cfg_high = market_data.load_strategies_config()
        cfg_high["backtest"]["brokerage_bps"] = 100.0
        cfg_high["backtest"]["slippage_bps"] = 100.0
        # Força desvio para acionar rebalanceamentos
        cfg_zero["strategies"]["indexacao_bogle"]["parametros"]["drift_threshold_pp"] = 0.2
        cfg_high["strategies"]["indexacao_bogle"]["parametros"]["drift_threshold_pp"] = 0.2

        bt_zero = strategies_engine.IndexacaoBogleStrategy(cfg_zero).run(ctx)["backtest"]
        bt_high = strategies_engine.IndexacaoBogleStrategy(cfg_high).run(ctx)["backtest"]

        self.assertGreater(bt_zero["rebalance_events"], 0)
        self.assertGreater(bt_zero["curve"][-1]["value"], bt_high["curve"][-1]["value"])

    def test_c_audit_log_blocks_update_and_delete(self):
        lid = database.log_strategy_decision(
            "indexacao_bogle",
            "Regra teste c",
            {"check": "append-only"},
            "Inserção permitida",
            actor="audit_test",
        )
        conn = database.get_connection()
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE strategy_audit_log SET decision = 'alterado' WHERE id = ?;", (lid,))
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("DELETE FROM strategy_audit_log WHERE id = ?;", (lid,))
        finally:
            conn.close()

    def test_d_strict_mode_missing_data_returns_indisponivel(self):
        with patch.object(market_data.requests, "get", side_effect=RuntimeError("Offline")):
            res = market_data.get_strict_daily_candles("BOVA11", yahoo_symbol="BOVA11.SA", allow_fallback=False)
            self.assertEqual(res["status"], "indisponível")
            self.assertEqual(res["last_price"], "indisponível")
            self.assertEqual(res["candles"], "indisponível")

            cdi = market_data.fetch_bcb_cdi_series(allow_cache=False)
            self.assertEqual(cdi["status"], "indisponível")
            self.assertEqual(cdi["annual_rate_pct"], "indisponível")

    def test_e_simulated_fallback_disabled_by_default_and_unused_by_strategies(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_SIMULATION_FALLBACK", None)
            default_flag = os.getenv("ENABLE_SIMULATION_FALLBACK", "false").lower() == "true"
            self.assertFalse(default_flag)
        self.assertFalse(config.ENABLE_SIMULATION_FALLBACK)

        with patch.object(signals_engine, "_generate_simulated_candles", side_effect=AssertionError("Proibido usar simulado")):
            with patch.object(market_data.requests, "get", side_effect=RuntimeError("Offline")):
                res = strategies_engine.run_strategy("indexacao_bogle", market_ctx={}, persist=False)
                self.assertFalse(res["backtest"]["available"])

    def test_f_approve_or_reject_proposal_requires_admin_inside_function(self):
        ctx = make_offline_market_ctx()
        prop_res = strategies_engine.propose_rebalance("indexacao_bogle", market_ctx=ctx, actor="test_f")
        pid = prop_res["proposal"]["id"]

        with self.assertRaises(PermissionError):
            strategies_engine.approve_or_reject_proposal(pid, "APROVADA", "usuario_comum", is_admin=False)
        with self.assertRaises(PermissionError):
            strategies_engine.approve_or_reject_proposal(pid, "APROVADA", "", is_admin=True)

        still_pending = database.get_strategy_proposal_by_id(pid)
        self.assertEqual(still_pending["status"], "PENDENTE")

        approved = strategies_engine.approve_or_reject_proposal(pid, "APROVADA", "admin", is_admin=True)
        self.assertEqual(approved["status"], "APROVADA")

    def test_g_dividendos_incomplete_allocates_remaining_to_cdi_and_excludes_unverified(self):
        # 4 ativos verificados (< 10) + 2 ativos não verificados (não podem entrar!)
        fund = make_verified_b3_fundamentals(6)
        fund["stocks"][4]["verified"] = False
        fund["stocks"][5]["verified"] = False
        fund["stocks_by_symbol"]["DIV05"]["verified"] = False
        fund["stocks_by_symbol"]["DIV06"]["verified"] = False

        # Marca campos de DIV05/DIV06 como se load_b3_fundamentals filtrasse, ou mantém verified=False
        # Aqui simulamos a saída de load_b3_fundamentals com verified=False excluído
        for sym in ("DIV05", "DIV06"):
            fund["stocks_by_symbol"][sym]["values"]["dy_12m_pct"] = "indisponível"

        res = strategies_engine.run_strategy("dividendos_barsi", market_ctx={"fundamentals": fund}, persist=False)
        self.assertIn("carteira incompleta: 4 de 10 ativos", res["portfolio_completeness"])
        symbols = [w["symbol"] for w in res["target_weights"]]
        self.assertNotIn("DIV05", symbols)
        self.assertNotIn("DIV06", symbols)
        self.assertIn("SELIC_CDI", symbols)
        cdi_w = next(w["target_weight_pct"] for w in res["target_weights"] if w["symbol"] == "SELIC_CDI")
        self.assertEqual(cdi_w, 60.0)
        self.assertAlmostEqual(sum(w["target_weight_pct"] for w in res["target_weights"]), 100.0, delta=0.1)

    def test_h_indexacao_cdi_leg_uses_sgs_series_and_documents_limitations(self):
        ctx = make_offline_market_ctx()
        res = strategies_engine.run_strategy("indexacao_bogle", market_ctx=ctx, persist=False)
        bt = res["backtest"]
        self.assertTrue(bt["available"])
        self.assertIn("CDI", bt["benchmarks"])
        warnings_txt = " ".join(bt.get("warnings") or []).lower()
        self.assertIn("impostos", warnings_txt)
        self.assertIn("iof", warnings_txt)
        self.assertGreater(bt["benchmarks"]["CDI"]["curve"][-1]["value"], 100.0)


if __name__ == "__main__":
    unittest.main()
