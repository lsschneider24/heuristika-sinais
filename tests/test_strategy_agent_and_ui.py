"""Testes offline (sem rede) para strategy_agent.py, rotas de /carteiras, botão único Admin e GitHub Pages estático."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app as flask_app  # noqa: E402
import build_github_pages  # noqa: E402
import config  # noqa: E402
import database  # noqa: E402
import strategy_agent  # noqa: E402
from tests.fixtures_global import make_global_offline_ctx  # noqa: E402
from tests.fixtures_strategies import make_offline_market_ctx, make_verified_b3_fundamentals  # noqa: E402


class StrategyAgentAndUITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="hk_agent_ui_"))
        self.old_db = config.DATABASE_PATH
        config.DATABASE_PATH = str(self.tmp_dir / "test_agent.db")
        database.init_db()
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()

    def tearDown(self) -> None:
        config.DATABASE_PATH = self.old_db
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_agent_12_tools_deterministic_and_refuses_personalized_advice(self) -> None:
        agent = strategy_agent.StrategyAgent()
        self.assertEqual(len(agent.TOOL_NAMES), 12)
        self.assertFalse(agent.llm.enabled)

        ctx = make_offline_market_ctx(with_gap=False)
        ctx["fundamentals"] = make_verified_b3_fundamentals(12)
        gctx = make_global_offline_ctx()

        self.assertGreaterEqual(len(agent.list_strategies()), 9)
        run_res = agent.run_strategy("indexacao_bogle", market_ctx=ctx, persist=True)
        self.assertTrue(run_res["backtest"]["available"])
        port = agent.get_portfolio("indexacao_bogle")
        self.assertIsNotNone(port)
        prop = agent.propose_rebalance("indexacao_bogle", market_ctx=ctx, actor="agent_test")
        self.assertTrue(prop["created"])
        met = agent.get_metrics("indexacao_bogle", market_ctx=ctx)
        self.assertIn("total_return_pct", met["metrics"])
        comp = agent.compare_strategies(["indexacao_bogle", "trend_following_turtles"], market_ctx=ctx)
        self.assertEqual(len(comp), 2)
        logs = agent.get_log(limit=10)
        self.assertGreater(len(logs), 0)

        rad = agent.scan_global_opportunities(market_ctx=gctx)
        self.assertEqual(rad["candidates"][0]["label"], "CANDIDATO A ESTUDO")
        reg = agent.get_market_regime(market_ctx=gctx)
        self.assertIn(reg["regime"], ("RISK-ON", "RISK-OFF", "NEUTRO"))
        corr = agent.get_correlation(market_ctx=gctx)
        self.assertIn("correlation_matrix", corr)
        exp = agent.explain_candidate("IVV", market_ctx=gctx)
        self.assertEqual(exp["label"], "CANDIDATO A ESTUDO")

        rep = agent.generate_report("semanal", market_ctx=gctx)
        self.assertIn("Relatório Semanal", rep["markdown"])

        # Recusa recomendação personalizada
        refusal = agent.chat("O que devo comprar hoje para o meu perfil?", market_ctx=gctx)
        self.assertTrue(refusal["refused"])
        self.assertEqual(refusal["mode"], "deterministic")
        self.assertIn("Não posso fazer recomendação personalizada", refusal["reply"])

    def test_ui_routes_admin_gate_and_single_button(self) -> None:
        r_cart = self.client.get("/carteiras")
        self.assertEqual(r_cart.status_code, 200)
        self.assertIn(b"Gerente de Estrat", r_cart.data)

        # Sem Admin: botão único e aprovação retornam 403
        r_unauth = self.client.post("/api/admin/atualizar-laboratorio")
        self.assertEqual(r_unauth.status_code, 403)
        r_dec_unauth = self.client.post("/api/admin/strategies/proposals/1/decide", json={"decision": "APROVADA"})
        self.assertEqual(r_dec_unauth.status_code, 403)

        # Chat determinístico via API
        r_chat = self.client.post("/api/strategies/agent/chat", json={"message": "O que devo comprar?"})
        self.assertEqual(r_chat.status_code, 200)
        self.assertTrue(r_chat.get_json()["refused"])

        # Com Admin: botão único executa sequência com mocks offline e aplica limite de frequência (429)
        import app as app_module
        app_module._LAB_UPDATE_LAST_TS = 0.0
        with self.client.session_transaction() as sess:
            sess["is_admin"] = True
        ctx = make_offline_market_ctx(with_gap=False)
        with patch("data_collector.collect_b3_fundamentals", return_value={"stocks": [{"symbol": "TEST"}], "reference_date": "2026-11-25"}), \
             patch("market_data.fetch_bcb_cdi_series", return_value={"status": "ok", "annual_rate_pct": 14.0}), \
             patch("strategies_engine.run_strategy", return_value={"target_weights": [{"symbol": "CDI", "target_weight_pct": 100.0}]}), \
             patch("global_radar.scan_global_opportunities", return_value={"regime": {"regime": "NEUTRO", "availability_label": "4 de 4 sinais"}}), \
             patch("strategy_agent.StrategyAgent.generate_report", return_value={"generated_at": "2026-11-25", "markdown": "# OK"}):
            r_btn = self.client.post("/api/admin/atualizar-laboratorio")
            self.assertEqual(r_btn.status_code, 200)
            payload = r_btn.get_json()
            self.assertTrue(payload["ok"])
            self.assertGreaterEqual(len(payload["summary"]["passed"]), 4)

            r_rate = self.client.post("/api/admin/atualizar-laboratorio")
            self.assertEqual(r_rate.status_code, 429)

    def test_risk_parity_caps_and_brl_conversion_regression(self) -> None:
        import strategies_engine
        ctx = make_offline_market_ctx(with_gap=False)
        res = strategies_engine.run_strategy("risk_parity_simplified", market_ctx=ctx, persist=False)
        self.assertTrue(res["backtest"]["available"])
        cls_totals: dict[str, float] = {}
        for tw in res["target_weights"]:
            self.assertLessEqual(tw["target_weight_pct"], 35.01)
            cl = tw["asset_class"]
            cls_totals[cl] = cls_totals.get(cl, 0.0) + tw["target_weight_pct"]
        for cl, tot in cls_totals.items():
            self.assertLessEqual(tot, 50.01, f"Classe {cl} excedeu 50%: {tot}%")

    def test_static_github_pages_disables_chat_and_admin(self) -> None:
        out_dir = self.tmp_dir / "site_dist"
        build_github_pages.build_static_site(output_dir=out_dir)
        cart_html = (out_dir / "carteiras" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const IS_STATIC = true;", cart_html)
        admin_html = (out_dir / "admin" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("btnAtualizarLab", admin_html)
        self.assertNotIn("/api/admin/atualizar-laboratorio", admin_html)

    def test_telegram_notifier_skips_without_token_and_formats_signal(self) -> None:
        import telegram_notifier
        msg = telegram_notifier.format_signal_message({
            "ativo": "BTC/USD",
            "direcao": "COMPRA",
            "categoria": "CRIPTO",
            "entrada": 90000,
            "stop_loss": 88000,
            "alvo_1": 93000,
            "alvo_2": 96000,
        })
        self.assertIn("BTC/USD", msg)
        self.assertIn("COMPRA", msg)
        res = telegram_notifier.send_telegram_message(msg, chat_id="")
        self.assertIn("ok", res)


if __name__ == "__main__":
    unittest.main()
