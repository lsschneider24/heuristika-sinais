"""Testes offline (sem rede) do Radar Global de Oportunidades e Estratégias Globais (Etapa 2B)."""

import os
import tempfile
import unittest
from unittest.mock import patch

import config

_tmp_global_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
_tmp_global_db.close()
config.DB_PATH = _tmp_global_db.name
config.DATABASE_PATH = _tmp_global_db.name

import database  # noqa: E402
import global_radar  # noqa: E402
import market_data  # noqa: E402
import strategies_engine  # noqa: E402
from tests.fixtures_global import make_global_offline_ctx  # noqa: E402


class GlobalRadarTestCase(unittest.TestCase):
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

    def test_1_regime_units_tnx_irx_and_3_of_4_aggregation(self):
        cfg = market_data.load_strategies_config()["global_radar"]["regime_rules"]

        # Caso Risk-On (4 de 4 sinais Risk-On): ^TNX=4.30% e ^IRX=3.80% -> spread +0.50 pp (não multiplicado por 10)
        ctx_on = make_global_offline_ctx(vix=14.0, tnx_pct=4.30, irx_pct=3.80, dxy_trend="down", credit_trend="up")
        reg_on = global_radar.classify_market_regime(ctx_on["candles_by_symbol"], cfg)
        self.assertEqual(reg_on["regime"], "RISK-ON")
        self.assertEqual(reg_on["availability_label"], "4 de 4 sinais disponíveis")
        yc = next(s for s in reg_on["signals"] if s["id"] == "yield_curve")
        self.assertAlmostEqual(yc["value"], 0.50, places=2)
        self.assertEqual(yc["y10_pct"], 4.30)
        self.assertEqual(yc["y3m_pct"], 3.80)

        # Caso Risk-Off (curva invertida ^TNX=4.10% e ^IRX=4.60% -> -0.50 pp, VIX=30, DXY up, HYG/IEF down)
        ctx_off = make_global_offline_ctx(vix=30.0, tnx_pct=4.10, irx_pct=4.60, dxy_trend="up", credit_trend="down")
        reg_off = global_radar.classify_market_regime(ctx_off["candles_by_symbol"], cfg)
        self.assertEqual(reg_off["regime"], "RISK-OFF")
        yc_off = next(s for s in reg_off["signals"] if s["id"] == "yield_curve")
        self.assertAlmostEqual(yc_off["value"], -0.50, places=2)

        # Caso sem dados -> 'indisponível' e 0 de 4 sinais disponíveis
        reg_empty = global_radar.classify_market_regime({}, cfg)
        self.assertEqual(reg_empty["regime"], "indisponível")
        self.assertEqual(reg_empty["availability_label"], "0 de 4 sinais disponíveis")

    def test_2_radar_scan_usd_brl_decomposition_and_candidate_governance(self):
        ctx = make_global_offline_ctx()
        radar = global_radar.scan_global_opportunities(market_ctx=ctx)
        self.assertEqual(radar["label"], "CANDIDATO A ESTUDO")
        self.assertIn("sem poder preditivo comprovado", radar["score_disclaimer"])
        self.assertGreaterEqual(len(radar["candidates"]), 15)

        ivv = next(c for c in radar["candidates"] if c["symbol"] == "IVV")
        self.assertEqual(ivv["label"], "CANDIDATO A ESTUDO")
        self.assertEqual(ivv["br_equivalent"], "IVVB11.SA")
        self.assertIsInstance(ivv["return_usd_12m_pct"], float)
        self.assertIsInstance(ivv["fx_effect_12m_pct"], float)
        self.assertIsInstance(ivv["return_brl_12m_pct"], float)
        self.assertIn("momentum_12_1", ivv["score_breakdown"])

        # Valuation não verificado deve aparecer como 'indisponível'
        self.assertEqual(ivv["valuation"]["status"], "indisponível")

        # Sem USDBRL=X -> retorno BRL fica 'indisponível' (nunca estimado)
        ctx_no_fx = make_global_offline_ctx()
        ctx_no_fx["candles_by_symbol"]["USDBRL=X"] = {"status": "indisponível", "candles": "indisponível"}
        radar_no_fx = global_radar.scan_global_opportunities(market_ctx=ctx_no_fx)
        ivv_no_fx = next(c for c in radar_no_fx["candidates"] if c["symbol"] == "IVV")
        self.assertIsInstance(ivv_no_fx["return_usd_12m_pct"], float)
        self.assertEqual(ivv_no_fx["return_brl_12m_pct"], "indisponível")

        # Matriz de correlação e explicação detalhada
        self.assertIn("IVV", radar["correlation_matrix"])
        exp = global_radar.explain_candidate("IVV", market_ctx=ctx)
        self.assertTrue(exp["found"])
        self.assertEqual(exp["label"], "CANDIDATO A ESTUDO")
        self.assertIsInstance(exp["a_favor"], list)
        self.assertIsInstance(exp["contra"], list)

    def test_3_dual_momentum_risk_parity_cap_and_radar_top_n(self):
        ctx = make_global_offline_ctx()

        # Dual Momentum em BRL (compara retornos convertidos para BRL contra CDI)
        res_dm = strategies_engine.run_strategy("dual_momentum_global", market_ctx=ctx, persist=True)
        self.assertTrue(res_dm["backtest"]["available"])
        self.assertEqual(res_dm["base_currency"], "BRL")
        self.assertEqual(res_dm["risk_free_symbol"], "SELIC_CDI")
        self.assertEqual(res_dm["backtest"]["curve"][0]["value"], 100.0)

        # Paridade de risco simplificada: teto de 35% impede SHY de dominar
        res_rp = strategies_engine.run_strategy("risk_parity_simplified", market_ctx=ctx, persist=True)
        self.assertTrue(res_rp["backtest"]["available"])
        self.assertIn("Paridade de risco simplificada", res_rp["metadata"]["nome"])
        for w in res_rp["target_weights"]:
            self.assertLessEqual(w["target_weight_pct"], 35.01, f"{w['symbol']} excedeu teto de 35%: {w['target_weight_pct']}")
        self.assertAlmostEqual(sum(w["target_weight_pct"] for w in res_rp["target_weights"]), 100.0, delta=0.3)

        # Radar Top-N: backtest histórico t+1 com custos
        res_topn = strategies_engine.run_strategy("radar_top_n", market_ctx=ctx, persist=True)
        self.assertTrue(res_topn["backtest"]["available"])
        self.assertEqual(len(res_topn["target_weights"]), 5)
        self.assertIn("sem poder preditivo comprovado", res_topn["score_disclaimer"])

        # Concentração por região/classe/moeda
        conc = global_radar.check_portfolio_concentration(res_rp["target_weights"], {})
        self.assertIsInstance(conc, list)

        # Sem rede -> modo estrito retorna 'indisponível'
        with patch.object(market_data.requests, "get", side_effect=RuntimeError("Offline")):
            res_off = strategies_engine.run_strategy("risk_parity_simplified", market_ctx={}, persist=False)
            self.assertFalse(res_off["backtest"]["available"])


if __name__ == "__main__":
    unittest.main()
