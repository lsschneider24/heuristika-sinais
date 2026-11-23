import os
import tempfile
import unittest

import config

# Usa banco temporário para testes isolados
_tmp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
_tmp_db.close()
config.DB_PATH = _tmp_db.name

import app as flask_app  # noqa: E402
import auditor  # noqa: E402
import database  # noqa: E402
import signals_engine  # noqa: E402


class SinaisVIPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        database.seed_initial_data(force=True)
        cls.client = flask_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(config.DB_PATH)
        except OSError:
            pass

    def test_initial_stats(self):
        stats = database.get_performance_stats()
        self.assertEqual(stats["total_sinais"], 4)
        self.assertEqual(stats["total_acertos"], 2)
        self.assertEqual(stats["total_erros"], 1)
        self.assertEqual(stats["abertos"], 1)
        self.assertEqual(stats["taxa_acerto"], 66.7)

    def test_auditor_rules_compra_e_venda(self):
        sig_buy = {"direcao": "COMPRA", "sl": 95.0, "tp1": 105.0, "tp2": 110.0}
        self.assertEqual(auditor.evaluate_signal_outcome(sig_buy, 111.0), "ACERTO_TP2")
        self.assertEqual(auditor.evaluate_signal_outcome(sig_buy, 106.0), "ACERTO_TP1")
        self.assertEqual(auditor.evaluate_signal_outcome(sig_buy, 94.5), "ERRO_SL")
        self.assertIsNone(auditor.evaluate_signal_outcome(sig_buy, 101.0))

        sig_sell = {"direcao": "VENDA", "sl": 105.0, "tp1": 95.0, "tp2": 90.0}
        self.assertEqual(auditor.evaluate_signal_outcome(sig_sell, 89.0), "ACERTO_TP2")
        self.assertEqual(auditor.evaluate_signal_outcome(sig_sell, 94.0), "ACERTO_TP1")
        self.assertEqual(auditor.evaluate_signal_outcome(sig_sell, 105.5), "ERRO_SL")
        self.assertIsNone(auditor.evaluate_signal_outcome(sig_sell, 99.0))

    def test_indicators(self):
        prices = [100 + i * 0.5 for i in range(40)]
        ema9 = signals_engine.calc_ema(prices, 9)
        rsi = signals_engine.calc_rsi(prices, 14)
        self.assertTrue(len(ema9) > 0)
        self.assertGreater(rsi, 70)

    def test_public_and_vip_and_admin_routes(self):
        # Vitrine pública
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn(b"Heur", r_home.data)

        # /vip redireciona sem login
        r_vip_unauth = self.client.get("/vip")
        self.assertEqual(r_vip_unauth.status_code, 302)

        # Login VIP com código demo
        r_login = self.client.post("/login", data={"identificador": "VIP-DEMO-2026"}, follow_redirects=True)
        self.assertEqual(r_login.status_code, 200)
        self.assertIn(b"Painel VIP em Tempo Real", r_login.data)

        # Login Admin
        r_admin_login = self.client.post(
            "/admin/login",
            data={"password": config.ADMIN_PASSWORD},
            follow_redirects=True,
        )
        self.assertEqual(r_admin_login.status_code, 200)
        self.assertIn(b"Painel Administrativo", r_admin_login.data)

    def test_carteiras_e_academia_certificado(self):
        # Carteiras públicas mostram bloqueio para não-Anual
        r_cart = self.client.get("/carteiras")
        self.assertEqual(r_cart.status_code, 200)
        self.assertIn(b"01/12/2026", r_cart.data)

        # Academia + Cadastro + Prova complexa + Certificado
        r_acad = self.client.get("/academia")
        self.assertEqual(r_acad.status_code, 200)

        r_cad = self.client.post(
            "/academia/cadastro",
            data={"nome": "Lucas Teste", "email": "lucas@teste.com", "documento": "12345678900", "pin": "4321"},
            follow_redirects=True,
        )
        self.assertEqual(r_cad.status_code, 200)
        self.assertIn(b"LUCAS TESTE", r_cad.data)

        import academy_data
        answers = {q["id"]: q["correta"] for q in academy_data.PROVA_QUESTOES}
        r_exam = self.client.post("/academia/prova", data=answers, follow_redirects=True)
        self.assertEqual(r_exam.status_code, 200)
        self.assertIn(b"APROVADO NA CERTIFICA", r_exam.data)

    def test_institutional_terminal_views(self):
        client = flask_app.app.test_client()

        # 1. Home pública (histórico + vitrine protegida)
        r_home = client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn(b"homeHistSearch", r_home.data)
        self.assertIn(b"vip-lock-overlay", r_home.data)

        # 2. /carteiras Paywall (não autenticado não vaza tickers reais)
        r_cart_locked = client.get("/carteiras")
        self.assertEqual(r_cart_locked.status_code, 200)
        self.assertIn(b"MODO SIMULADOR DEMO", r_cart_locked.data)
        self.assertIn(b"wealthSvg", r_cart_locked.data)
        self.assertIn(b"donutSvg", r_cart_locked.data)
        self.assertNotIn(b"TESOURO SELIC", r_cart_locked.data)
        self.assertNotIn(b"HGLG11", r_cart_locked.data)

        # 3. /carteiras com assinante Anual (acesso liberado + query params)
        annual_sub = database.create_subscriber("Assinante Anual", "anual@teste.com", plano="Anual", dias=365)
        r_login = client.post("/login", data={"identificador": annual_sub["codigo_acesso"]}, follow_redirects=True)
        self.assertEqual(r_login.status_code, 200)
        self.assertIn(b"Calculadora de Lote", r_login.data)

        r_home_vip = client.get("/")
        self.assertEqual(r_home_vip.status_code, 200)
        self.assertIn(b"R:R 1:", r_home_vip.data)

        r_cart_open = client.get("/carteiras?horizonte=Curto%20(2%20anos)&perfil=Conservador")
        self.assertEqual(r_cart_open.status_code, 200)
        self.assertIn(b"ACESSO ANUAL LIBERADO", r_cart_open.data)
        self.assertIn(b"TESOURO SELIC", r_cart_open.data)
        self.assertIn(b"copyAllocationBtn", r_cart_open.data)

        # 4. /vip com calculadora e busca + EN language toggle
        r_vip = client.get("/vip")
        self.assertEqual(r_vip.status_code, 200)
        self.assertIn(b"riskCalcSection", r_vip.data)
        self.assertIn(b"vipSearchInput", r_vip.data)
        self.assertIn(b"R:R 1:", r_vip.data)
        r_en = client.get("/lang/en", follow_redirects=True)
        self.assertEqual(r_en.status_code, 200)

        # 5. /login e todas as abas de /admin
        self.assertEqual(client.get("/login").status_code, 302)  # já logado redireciona para /vip
        anon = flask_app.app.test_client()
        self.assertEqual(anon.get("/login").status_code, 200)
        anon.post("/admin/login", data={"password": config.ADMIN_PASSWORD})
        for tab in ("disparo", "auditoria", "assinantes", "carteiras"):
            r_tab = anon.get(f"/admin?tab={tab}")
            self.assertEqual(r_tab.status_code, 200)

        # 6. /academia e /certificado
        r_acad = anon.get("/academia")
        self.assertEqual(r_acad.status_code, 200)
        self.assertIn(b"acadProgressFill", r_acad.data)
        anon.post(
            "/academia/cadastro",
            data={"nome": "Certificado Teste", "email": "cert@teste.com", "documento": "", "pin": "9876"},
        )
        import academy_data
        answers = {q["id"]: q["correta"] for q in academy_data.PROVA_QUESTOES}
        r_pass = anon.post("/academia/prova", data=answers, follow_redirects=True)
        self.assertEqual(r_pass.status_code, 200)
        student = database.authenticate_student("cert@teste.com", "9876")
        certs = database.list_student_certificates(student["id"])
        self.assertTrue(len(certs) >= 1)
        r_cert = anon.get(f"/certificado/{certs[0]['codigo']}")
        self.assertEqual(r_cert.status_code, 200)
        self.assertIn(b"Certificado Teste", r_cert.data)

    def test_academia_learning_studio_payload(self):
        import json
        import re
        import academy_data

        self.assertEqual(len(academy_data.MODULOS_EDUCACIONAIS), 4)
        for mod in academy_data.MODULOS_EDUCACIONAIS:
            self.assertIn("duracao", mod)
            self.assertIn("nivel", mod)
            estudo = mod["estudo_completo"]
            for key in ("introducao", "formula_principal", "exemplo_resolvido", "erros_comuns", "checklist_pratico"):
                self.assertIn(key, estudo)
            self.assertIsInstance(estudo["erros_comuns"], list)
            self.assertIsInstance(estudo["checklist_pratico"], list)
            self.assertEqual(len(mod["slides"]), 5)
            for slide in mod["slides"]:
                for skey in ("titulo", "subtitulo", "bullets", "destaque", "visual_type"):
                    self.assertIn(skey, slide)
            video = mod["video_aula"]
            self.assertIn("titulo", video)
            self.assertGreaterEqual(video["duracao_segundos"], 180)
            self.assertGreaterEqual(len(video["capitulos"]), 4)
            expected_audio_url = f"/static/audio/academia_mod_{mod['numero']}.mp3"
            self.assertEqual(video.get("audio_url"), expected_audio_url)
            audio_path = os.path.join(config.BASE_DIR, "static", "audio", f"academia_mod_{mod['numero']}.mp3")
            self.assertTrue(os.path.isfile(audio_path), f"Arquivo de áudio ausente: {audio_path}")
            self.assertGreater(os.path.getsize(audio_path), 200_000)

            prev_start = -1.0
            for cap in video["capitulos"]:
                for ckey in ("tempo_inicio", "titulo", "roteiro", "visual_mode"):
                    self.assertIn(ckey, cap)
                self.assertGreater(float(cap["tempo_inicio"]), prev_start)
                prev_start = float(cap["tempo_inicio"])
                legendas = cap.get("legendas") or []
                self.assertGreater(len(legendas), 0)
                for leg in legendas:
                    for lkey in ("inicio", "fim", "texto"):
                        self.assertIn(lkey, leg)
                    self.assertGreaterEqual(float(leg["fim"]), float(leg["inicio"]))

        r_acad = self.client.get("/academia")
        self.assertEqual(r_acad.status_code, 200)
        html = r_acad.data.decode("utf-8")
        self.assertIn("learningStudio", html)
        self.assertIn("academyVideoCanvas", html)
        self.assertIn('id="academyAudioPlayer"', html)
        self.assertIn('id="videoVolumeSlider"', html)
        self.assertNotIn("speechSynthesis", html)
        self.assertIn("slideDiagramSvg", html)
        self.assertIn("studyContentHost", html)
        match = re.search(r'<script id="academyModulesJson" type="application/json">(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(match)
        parsed = json.loads(match.group(1))
        self.assertEqual(len(parsed), 4)
        self.assertEqual(len(parsed[0]["slides"]), 5)
        self.assertTrue(len(parsed[0]["video_aula"]["capitulos"]) >= 4)

        r_mp3 = self.client.get("/static/audio/academia_mod_01.mp3")
        self.assertEqual(r_mp3.status_code, 200)
        self.assertIn("audio/mpeg", r_mp3.headers.get("Content-Type", ""))
        r_mp3.close()

        r_mp3_range = self.client.get("/static/audio/academia_mod_01.mp3", headers={"Range": "bytes=0-1023"})
        self.assertEqual(r_mp3_range.status_code, 206)
        r_mp3_range.close()

    def test_admin_fixes_all_tabs(self):
        import re
        from datetime import datetime, timedelta
        from unittest.mock import patch

        # 0. Rotas admin novas e existentes exigem autenticação
        anon_client = flask_app.app.test_client()
        for method, path in (
            ("GET", "/admin/api/quote?categoria=Cripto&ativo=BTC/USD"),
            ("POST", "/admin/reopen-signal/1"),
            ("POST", "/admin/delete-signal/1"),
            ("POST", "/admin/subscriber/1/plan"),
            ("POST", "/admin/subscriber/1/delete"),
            ("POST", "/admin/portfolio/1/update"),
            ("POST", "/admin/logout"),
        ):
            resp = anon_client.get(path) if method == "GET" else anon_client.post(path)
            self.assertEqual(resp.status_code, 302, f"Esperado 302 em {method} {path}")
            self.assertIn("/admin/login", resp.headers.get("Location", ""))

        admin_client = flask_app.app.test_client()
        r_login = admin_client.post(
            "/admin/login",
            data={"password": config.ADMIN_PASSWORD},
            follow_redirects=True,
        )
        self.assertEqual(r_login.status_code, 200)
        m_csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', r_login.data.decode("utf-8"))
        self.assertIsNotNone(m_csrf)
        csrf_token = m_csrf.group(1)

        # CSRF obrigatório em POSTs autenticados no /admin
        before_count = len(database.list_signals(limit=200))
        r_no_csrf = admin_client.post(
            "/admin/publish",
            data={
                "categoria": "Cripto",
                "ativo": "BTC/USD",
                "direcao": "COMPRA",
                "entrada": "100",
                "sl": "95",
                "tp1": "105",
                "tp2": "110",
                "destino": "VIP",
            },
        )
        self.assertEqual(r_no_csrf.status_code, 403)
        self.assertEqual(len(database.list_signals(limit=200)), before_count)

        # 1. Tab inválida faz fallback seguro para Aba 1 (disparo)
        r_bad_tab = admin_client.get("/admin?tab=invalido")
        self.assertEqual(r_bad_tab.status_code, 200)
        self.assertIn(b"Novo Sinal (Site + Telegram)", r_bad_tab.data)

        # 2. Validação de níveis em /admin/publish (rejeita COMPRA e VENDA invertidos)
        with patch.object(config, "BOT_TOKEN", ""):
            r_inv_buy = admin_client.post(
                "/admin/publish",
                data={
                    "csrf_token": csrf_token,
                    "categoria": "Cripto",
                    "ativo": "BTC/USD",
                    "direcao": "COMPRA",
                    "entrada": "100",
                    "sl": "105",
                    "tp1": "110",
                    "tp2": "115",
                    "destino": "VIP",
                },
                follow_redirects=True,
            )
            self.assertEqual(r_inv_buy.status_code, 200)
            self.assertIn(b"Stop Loss &lt; Entrada &lt; TP1 &lt; TP2", r_inv_buy.data)
            self.assertEqual(len(database.list_signals(limit=200)), before_count)

            r_inv_sell = admin_client.post(
                "/admin/publish",
                data={
                    "csrf_token": csrf_token,
                    "categoria": "Cripto",
                    "ativo": "BTC/USD",
                    "direcao": "VENDA",
                    "entrada": "100",
                    "sl": "95",
                    "tp1": "90",
                    "tp2": "85",
                    "destino": "VIP",
                },
                follow_redirects=True,
            )
            self.assertEqual(r_inv_sell.status_code, 200)
            self.assertIn(b"TP2 &lt; TP1 &lt; Entrada &lt; Stop Loss", r_inv_sell.data)
            self.assertEqual(len(database.list_signals(limit=200)), before_count)

            # 3. Publicação válida com vírgula PT-BR + aviso explícito quando Telegram não está configurado
            r_pub = admin_client.post(
                "/admin/publish",
                data={
                    "csrf_token": csrf_token,
                    "categoria": "Cripto",
                    "ativo": "ETH/USD",
                    "direcao": "COMPRA",
                    "entrada": "100,50",
                    "sl": "95,00",
                    "tp1": "108,50",
                    "tp2": "115,00",
                    "destino": "VIP",
                    "observacao": "Teste automatizado",
                },
                follow_redirects=True,
            )
            self.assertEqual(r_pub.status_code, 200)
            self.assertIn(b"Aviso Telegram:", r_pub.data)

            all_sigs = database.list_signals(limit=200)
            self.assertEqual(len(all_sigs), before_count + 1)
            created_sig = all_sigs[0]
            self.assertAlmostEqual(created_sig["entrada"], 100.5)

            # 4. Endpoint de cotação /admin/api/quote (incluindo preços muito pequenos)
            with patch.object(signals_engine, "get_current_price", return_value=(91500.0, "Binance")):
                r_quote = admin_client.get("/admin/api/quote?categoria=Cripto&ativo=BTC/USD")
                self.assertEqual(r_quote.status_code, 200)
                qdata = r_quote.get_json()
                self.assertTrue(qdata["ok"])
                self.assertEqual(qdata["preco"], 91500.0)
                self.assertIn("COMPRA", qdata["sugestao"])
                self.assertIn("VENDA", qdata["sugestao"])

            for tiny_px in (0.01, 0.0001):
                with patch.object(signals_engine, "get_current_price", return_value=(tiny_px, "Binance")):
                    r_tiny = admin_client.get("/admin/api/quote?categoria=Forex&ativo=EUR/USD")
                    self.assertEqual(r_tiny.status_code, 200)
                    tdata = r_tiny.get_json()
                    c = tdata["sugestao"]["COMPRA"]
                    v = tdata["sugestao"]["VENDA"]
                    self.assertTrue(0 < c["sl"] < tdata["preco"] < c["tp1"] < c["tp2"])
                    self.assertTrue(0 < v["tp2"] < v["tp1"] < tdata["preco"] < v["sl"])

            # 5. Encerramento duplicado bloqueado, reabertura e exclusão na Aba 2
            sig_id = created_sig["id"]
            r_close1 = admin_client.post(
                f"/admin/close-signal/{sig_id}",
                data={"csrf_token": csrf_token, "outcome": "ACERTO_TP1"},
                follow_redirects=True,
            )
            self.assertEqual(r_close1.status_code, 200)
            self.assertEqual(database.get_signal_by_id(sig_id)["status"], "ACERTO_TP1")

            r_close_dup = admin_client.post(
                f"/admin/close-signal/{sig_id}",
                data={"csrf_token": csrf_token, "outcome": "ACERTO_TP1"},
                follow_redirects=True,
            )
            self.assertEqual(r_close_dup.status_code, 200)
            self.assertIn(b"encerrado como ACERTO_TP1", r_close_dup.data)

            r_reopen = admin_client.post(
                f"/admin/reopen-signal/{sig_id}",
                data={"csrf_token": csrf_token},
                follow_redirects=True,
            )
            self.assertEqual(r_reopen.status_code, 200)
            self.assertEqual(database.get_signal_by_id(sig_id)["status"], "ABERTO")

            r_del_sig = admin_client.post(
                f"/admin/delete-signal/{sig_id}",
                data={"csrf_token": csrf_token},
                follow_redirects=True,
            )
            self.assertEqual(r_del_sig.status_code, 200)
            self.assertIsNone(database.get_signal_by_id(sig_id))

        # Toggle de configuração com nome legível (não exibe chave interna)
        r_toggle = admin_client.post(
            "/admin/toggle-setting",
            data={"csrf_token": csrf_token, "chave": "auto_audit_enabled"},
            follow_redirects=True,
        )
        self.assertEqual(r_toggle.status_code, 200)
        self.assertIn(b"Auditoria Autom", r_toggle.data)
        self.assertNotIn(b"Configura\xc3\xa7\xc3\xa3o &#39;auto_audit_enabled&#39;", r_toggle.data)
        admin_client.post("/admin/toggle-setting", data={"csrf_token": csrf_token, "chave": "auto_audit_enabled"})

        # 6. Assinantes: +30d soma à validade (não reduz Anual!), expirado reativa/bloqueia, upgrade estende e sem XSS inline
        annual_sub = database.create_subscriber("Anual Soma", "anual_soma@teste.com", plano="Anual", dias=365)
        original_exp = annual_sub["expira_em"]
        expected_exp = (
            datetime.strptime(original_exp, "%Y-%m-%d").date() + timedelta(days=30)
        ).strftime("%Y-%m-%d")

        r_renew = admin_client.post(
            f"/admin/subscriber/{annual_sub['id']}/renew",
            data={"csrf_token": csrf_token, "dias": "30"},
            follow_redirects=True,
        )
        self.assertEqual(r_renew.status_code, 200)
        renewed_sub = database.get_subscriber_by_id(annual_sub["id"])
        self.assertEqual(renewed_sub["expira_em"], expected_exp)
        self.assertGreater(renewed_sub["expira_em"], original_exp)

        # Assinante com apóstrofo no nome e link com aspas simples (garante zero onclick/onsubmit inline)
        dangelo = database.create_subscriber("Joana D'Angelo", "joana@teste.com", plano="Mensal", dias=30)
        database.set_subscriber_invite_link(dangelo["id"], "https://t.me/+teste'invite")

        # Upgrade de plano ativo Mensal -> Anual estende expira_em para >= 365 dias
        r_up = admin_client.post(
            f"/admin/subscriber/{dangelo['id']}/plan",
            data={"csrf_token": csrf_token, "plano": "Anual"},
            follow_redirects=True,
        )
        self.assertEqual(r_up.status_code, 200)
        dangelo_up = database.get_subscriber_by_id(dangelo["id"])
        self.assertEqual(dangelo_up["plano"], "Anual")
        self.assertGreaterEqual(
            dangelo_up["expira_em"],
            (datetime.now().date() + timedelta(days=364)).strftime("%Y-%m-%d"),
        )

        # Assinante expirado (ativo=1 ou ativo=0, expira_em no passado)
        expired_sub = database.create_subscriber("Expirado Teste", "expirado@teste.com", plano="Anual", dias=365)
        conn = database.get_connection()
        conn.execute("UPDATE subscribers SET expira_em = '2020-01-01', ativo = 1 WHERE id = ?;", (expired_sub["id"],))
        conn.commit()
        conn.close()

        r_subs_tab = admin_client.get("/admin?tab=assinantes")
        self.assertEqual(r_subs_tab.status_code, 200)
        subs_html = r_subs_tab.data.decode("utf-8")
        self.assertIn("EXPIRADO", subs_html)
        self.assertNotIn("onclick=", subs_html)
        self.assertNotIn("onsubmit=", subs_html)
        self.assertIn("data-confirm=\"Excluir permanentemente o assinante Joana D&#39;Angelo?\"", subs_html)

        sub_client = flask_app.app.test_client()
        with sub_client.session_transaction() as sess:
            sess["vip_subscriber_id"] = expired_sub["id"]
        self.assertEqual(sub_client.get("/vip").status_code, 302)
        r_cart_exp = sub_client.get("/carteiras")
        self.assertEqual(r_cart_exp.status_code, 200)
        self.assertIn(b"MODO SIMULADOR DEMO", r_cart_exp.data)
        self.assertNotIn(b"ACESSO ANUAL LIBERADO", r_cart_exp.data)

        # Renovação de expirado reativa para hoje + 30 dias
        database.toggle_subscriber_status(expired_sub["id"])
        admin_client.post(
            f"/admin/subscriber/{expired_sub['id']}/renew",
            data={"csrf_token": csrf_token, "dias": "30"},
        )
        reac_sub = database.get_subscriber_by_id(expired_sub["id"])
        self.assertEqual(reac_sub["ativo"], 1)
        self.assertEqual(reac_sub["expira_em"], (datetime.now().date() + timedelta(days=30)).strftime("%Y-%m-%d"))

        # Upgrade de plano para Vitalício e limpeza dos assinantes de teste
        r_plan = admin_client.post(
            f"/admin/subscriber/{annual_sub['id']}/plan",
            data={"csrf_token": csrf_token, "plano": "Vitalício"},
            follow_redirects=True,
        )
        self.assertEqual(r_plan.status_code, 200)
        self.assertEqual(database.get_subscriber_by_id(annual_sub["id"])["plano"], "Vitalício")

        for sid in (annual_sub["id"], expired_sub["id"], dangelo["id"]):
            admin_client.post(f"/admin/subscriber/{sid}/delete", data={"csrf_token": csrf_token})
            self.assertIsNone(database.get_subscriber_by_id(sid))

        # 7. Carteiras Admin: peso decimal 12,5%, vigência editável/cronológica, alerta != 100%, update e remoção
        r_bad_vig = admin_client.post(
            "/admin/portfolio/add",
            data={
                "csrf_token": csrf_token,
                "horizonte": "Curto (2 anos)",
                "perfil": "Conservador",
                "ativo": "BAD11",
                "categoria": "Fundos",
                "peso_pct": "10",
                "vigencia": "2027-01-01",
                "tese": "Vigência inválida",
            },
            follow_redirects=True,
        )
        self.assertIn(b"DD/MM/AAAA", r_bad_vig.data)

        r_port_add = admin_client.post(
            "/admin/portfolio/add",
            data={
                "csrf_token": csrf_token,
                "horizonte": "Curto (2 anos)",
                "perfil": "Conservador",
                "ativo": "LFTB11",
                "categoria": "Fundos",
                "peso_pct": "12.5",
                "vigencia": "01/01/2027",
                "tese": "Teste decimal em carteira",
            },
            follow_redirects=True,
        )
        self.assertEqual(r_port_add.status_code, 200)
        self.assertIn(b"12,5%", r_port_add.data)
        self.assertIn(b"01/01/2027", r_port_add.data)
        self.assertIn(b"112,5%", r_port_add.data)
        self.assertIn(b"diferente de 100%", r_port_add.data)

        summary_curto = [
            s for s in database.get_portfolio_weight_summary()
            if s["horizonte"] == "Curto (2 anos)" and s["perfil"] == "Conservador"
        ][0]
        self.assertEqual(summary_curto["vigencia"], "01/01/2027")

        added_items = [
            it for it in database.list_portfolios(horizonte="Curto (2 anos)", perfil="Conservador")
            if it["ativo"] == "LFTB11"
        ]
        self.assertEqual(len(added_items), 1)
        added_id = added_items[0]["id"]

        r_port_upd = admin_client.post(
            f"/admin/portfolio/{added_id}/update",
            data={"csrf_token": csrf_token, "peso_pct": "10,0", "vigencia": "15/01/2027", "tese": "Tese editada"},
            follow_redirects=True,
        )
        self.assertEqual(r_port_upd.status_code, 200)
        self.assertIn(b"15/01/2027", r_port_upd.data)
        self.assertIn(b"Tese editada", r_port_upd.data)

        admin_client.post(f"/admin/portfolio/{added_id}/delete", data={"csrf_token": csrf_token})
        self.assertAlmostEqual(
            database.get_portfolio_combo_weight("Curto (2 anos)", "Conservador"),
            100.0,
        )

        # Logout via POST com CSRF
        r_logout = admin_client.post("/admin/logout", data={"csrf_token": csrf_token})
        self.assertEqual(r_logout.status_code, 302)
        self.assertEqual(admin_client.get("/admin").status_code, 302)

    def test_academia_adjustments_security_and_edge_cases(self):
        import academy_data

        # 1. Higiene ortográfica, remoção de fonética nas legendas, duração e visuais
        self.assertNotIn("Implácavel", repr(academy_data.MODULOS_EDUCACIONAIS))
        self.assertIn("Implacável", repr(academy_data.MODULOS_EDUCACIONAIS))

        phonetic_tokens = (
            "Á-Tê-Érre",
            "I-P-C-A mais",
            "I-P-C-A dois mil e quarenta e cinco",
            "I-V-V-B onze",
            "éfe estrela",
            "érre",
            "S&P quinhentos",
            "Nasdaq cem",
        )

        r_acad = self.client.get("/academia")
        self.assertEqual(r_acad.status_code, 200)
        acad_html = r_acad.data.decode("utf-8")
        self.assertNotIn("00:00 / 03:40", acad_html)
        self.assertIn("Ir para a Prova", acad_html)

        for mod in academy_data.MODULOS_EDUCACIONAIS:
            num = mod["numero"]
            r_mp3 = self.client.get(f"/static/audio/academia_mod_{num}.mp3")
            self.assertEqual(r_mp3.status_code, 200)
            self.assertIn("audio/mpeg", r_mp3.headers.get("Content-Type", ""))
            r_mp3.close()

            r_range = self.client.get(
                f"/static/audio/academia_mod_{num}.mp3",
                headers={"Range": "bytes=0-1023"},
            )
            self.assertEqual(r_range.status_code, 206)
            r_range.close()

            for slide in mod["slides"]:
                self.assertIn(f'"{slide["visual_type"]}"', acad_html)

            for cap in mod["video_aula"]["capitulos"]:
                self.assertIn(f'"{cap["visual_mode"]}"', acad_html)
                for leg in cap.get("legendas") or []:
                    txt = leg["texto"]
                    for tok in phonetic_tokens:
                        self.assertNotIn(tok, txt, f"Token fonético vazou na legenda: {txt}")
                    self.assertLessEqual(len(txt), 170, f"Legenda longa demais ({len(txt)}): {txt}")
                    self.assertGreaterEqual(float(leg["inicio"]), 0.0)
                    self.assertGreaterEqual(float(leg["fim"]), float(leg["inicio"]))

        # 2. Cadastro com validação e PIN com hash seguro
        c = flask_app.app.test_client()
        r_bad_name = c.post(
            "/academia/cadastro",
            data={"nome": "Ab", "email": "valido@teste.com", "documento": "", "pin": "1234"},
            follow_redirects=True,
        )
        self.assertIn("mín. 3 caracteres", r_bad_name.data.decode("utf-8"))

        r_bad_email = c.post(
            "/academia/cadastro",
            data={"nome": "Aluno Valido", "email": "invalido", "documento": "", "pin": "1234"},
            follow_redirects=True,
        )
        self.assertIn("e-mail válido", r_bad_email.data.decode("utf-8"))

        r_bad_pin = c.post(
            "/academia/cadastro",
            data={"nome": "Aluno Valido", "email": "valido@teste.com", "documento": "", "pin": "123"},
            follow_redirects=True,
        )
        self.assertIn("pelo menos 4 dígitos", r_bad_pin.data.decode("utf-8"))
        self.assertIsNone(database.authenticate_student("valido@teste.com", "1234"))

        r_ok_cad = c.post(
            "/academia/cadastro",
            data={
                "nome": "Aluno Seguranca",
                "email": "seguranca@teste.com",
                "documento": "123.456.789-01",
                "pin": "5588",
            },
            follow_redirects=False,
        )
        self.assertEqual(r_ok_cad.status_code, 302)
        self.assertTrue(r_ok_cad.headers.get("Location", "").endswith("#prova"))

        conn = database.get_connection()
        stored_row = conn.execute(
            "SELECT * FROM academy_students WHERE email = ?;",
            ("seguranca@teste.com",),
        ).fetchone()
        conn.close()
        self.assertIsNotNone(stored_row)
        self.assertNotEqual(stored_row["pin"], "5588")
        self.assertTrue(stored_row["pin"].startswith(("scrypt:", "pbkdf2:")))

        # E-mail duplicado não gera 500 e mantém aviso amigável
        c_dup = flask_app.app.test_client()
        r_dup = c_dup.post(
            "/academia/cadastro",
            data={"nome": "Outro Nome", "email": "seguranca@teste.com", "documento": "", "pin": "9999"},
            follow_redirects=True,
        )
        self.assertEqual(r_dup.status_code, 200)
        self.assertIn("Este e-mail já está cadastrado", r_dup.data.decode("utf-8"))

        # Login rejeita PIN errado e aceita PIN certo
        self.assertIsNone(database.authenticate_student("seguranca@teste.com", "0000"))
        r_wrong_login = c_dup.post(
            "/academia/login",
            data={"email": "seguranca@teste.com", "pin": "0000"},
            follow_redirects=True,
        )
        self.assertIn("E-mail ou PIN incorretos", r_wrong_login.data.decode("utf-8"))

        r_ok_login = c_dup.post(
            "/academia/login",
            data={"email": "seguranca@teste.com", "pin": "5588"},
            follow_redirects=False,
        )
        self.assertEqual(r_ok_login.status_code, 302)
        self.assertTrue(r_ok_login.headers.get("Location", "").endswith("#prova"))

        # Conta legada em texto puro é migrada automaticamente para hash ao autenticar
        conn = database.get_connection()
        conn.execute(
            "INSERT INTO academy_students (nome, email, documento, pin, criado_em) VALUES (?, ?, ?, ?, ?);",
            ("Aluno Legado", "legado@teste.com", "", "2468", database.now_str()),
        )
        conn.commit()
        conn.close()

        self.assertIsNone(database.authenticate_student("legado@teste.com", "0000"))
        legacy_auth = database.authenticate_student("legado@teste.com", "2468")
        self.assertIsNotNone(legacy_auth)
        self.assertTrue(legacy_auth["pin"].startswith(("scrypt:", "pbkdf2:")))

        # 3. Fluxos da prova, cookie compacto e sessão inválida
        anon_exam = flask_app.app.test_client()
        all_answers = {q["id"]: q["correta"] for q in academy_data.PROVA_QUESTOES}
        r_unauth_exam = anon_exam.post("/academia/prova", data=all_answers, follow_redirects=True)
        self.assertIn("Faça seu cadastro ou login na Academia", r_unauth_exam.data.decode("utf-8"))

        # Sessão com academy_student_id inexistente não emite certificado órfão
        ghost = flask_app.app.test_client()
        with ghost.session_transaction() as sess:
            sess["academy_student_id"] = 999999
        r_ghost_exam = ghost.post("/academia/prova", data=all_answers, follow_redirects=True)
        self.assertIn("Faça seu cadastro ou login na Academia", r_ghost_exam.data.decode("utf-8"))
        with ghost.session_transaction() as sess:
            self.assertNotIn("academy_student_id", sess)

        # Prova incompleta não corrige nem emite certificado
        partial_answers = {q["id"]: q["correta"] for q in academy_data.PROVA_QUESTOES[:5]}
        r_incomplete = c.post("/academia/prova", data=partial_answers, follow_redirects=True)
        self.assertIn("Responda todas as 10 questões", r_incomplete.data.decode("utf-8"))
        self.assertEqual(len(database.list_student_certificates(stored_row["id"])), 0)

        # Prova com 6/10 (60%) reprova sem emitir certificado e redireciona para #resultado-prova
        six_right = {}
        for idx, q in enumerate(academy_data.PROVA_QUESTOES):
            if idx < 6:
                six_right[q["id"]] = q["correta"]
            else:
                wrong_opt = next(opt_v for opt_v, _ in q["opcoes"] if opt_v != q["correta"])
                six_right[q["id"]] = wrong_opt

        r_fail_redir = c.post("/academia/prova", data=six_right, follow_redirects=False)
        self.assertEqual(r_fail_redir.status_code, 302)
        self.assertTrue(r_fail_redir.headers.get("Location", "").endswith("#resultado-prova"))
        r_fail_page = c.get("/academia")
        fail_html = r_fail_page.data.decode("utf-8")
        self.assertIn("NÃO APROVADO (MÍNIMO 70%)", fail_html)
        self.assertIn("Sua resposta:", fail_html)
        self.assertEqual(len(database.list_student_certificates(stored_row["id"])), 0)

        # Prova com 7/10 (70%) aprova, emite certificado e mantém Set-Cookie compacto (< 2000 bytes)
        seven_right = {}
        for idx, q in enumerate(academy_data.PROVA_QUESTOES):
            if idx < 7:
                seven_right[q["id"]] = q["correta"]
            else:
                wrong_opt = next(opt_v for opt_v, _ in q["opcoes"] if opt_v != q["correta"])
                seven_right[q["id"]] = wrong_opt

        r_pass_redir = c.post("/academia/prova", data=seven_right, follow_redirects=False)
        self.assertEqual(r_pass_redir.status_code, 302)
        self.assertTrue(r_pass_redir.headers.get("Location", "").endswith("#resultado-prova"))
        set_cookie_hdr = "; ".join(r_pass_redir.headers.getlist("Set-Cookie"))
        self.assertLess(len(set_cookie_hdr), 2000, f"Set-Cookie muito grande ({len(set_cookie_hdr)} bytes)")

        r_pass_page = c.get("/academia")
        pass_html = r_pass_page.data.decode("utf-8")
        self.assertIn("APROVADO NA CERTIFICA", pass_html)
        self.assertIn("70%", pass_html)

        certs = database.list_student_certificates(stored_row["id"])
        self.assertEqual(len(certs), 1)
        cert_code = certs[0]["codigo"]

        # 4. Privacidade no certificado público (CPF e e-mail mascarados) + código case-insensitive e inválido
        r_cert_cpf = self.client.get(f"/certificado/{cert_code.lower()}")
        self.assertEqual(r_cert_cpf.status_code, 200)
        cert_cpf_html = r_cert_cpf.data.decode("utf-8")
        self.assertIn("Aluno Seguranca", cert_cpf_html)
        self.assertIn("***.456.789-**", cert_cpf_html)
        self.assertNotIn("123.456.789-01", cert_cpf_html)
        self.assertNotIn("seguranca@teste.com", cert_cpf_html)

        # Certificado de aluno sem documento mascara o e-mail
        c_mail = flask_app.app.test_client()
        c_mail.post(
            "/academia/cadastro",
            data={"nome": "Aluno Email Mask", "email": "maskmail@teste.com", "documento": "", "pin": "1122"},
        )
        c_mail.post("/academia/prova", data=all_answers)
        mail_student = database.authenticate_student("maskmail@teste.com", "1122")
        mail_certs = database.list_student_certificates(mail_student["id"])
        r_cert_mail = self.client.get(f"/certificado/{mail_certs[0]['codigo']}")
        self.assertEqual(r_cert_mail.status_code, 200)
        cert_mail_html = r_cert_mail.data.decode("utf-8")
        self.assertIn("ma***@teste.com", cert_mail_html)
        self.assertNotIn("maskmail@teste.com", cert_mail_html)

        r_cert_missing = self.client.get("/certificado/INEXISTENTE-000", follow_redirects=False)
        self.assertEqual(r_cert_missing.status_code, 302)
        self.assertTrue(r_cert_missing.headers.get("Location", "").endswith("/academia"))

    def test_build_github_pages_static_bundle(self):
        from pathlib import Path
        import shutil
        import build_github_pages

        tmp_out = Path(tempfile.mkdtemp(prefix="hk_pages_test_"))
        try:
            res = build_github_pages.build_static_site(
                output_dir=tmp_out,
                backend_url="https://heuristika-web-production.up.railway.app",
            )
            self.assertGreaterEqual(res["files_count"], 11)
            self.assertTrue((tmp_out / ".nojekyll").is_file())
            self.assertTrue((tmp_out / "index.html").is_file())
            self.assertTrue((tmp_out / "carteiras" / "index.html").is_file())
            self.assertTrue((tmp_out / "academia" / "index.html").is_file())
            self.assertTrue((tmp_out / "academia.html").is_file())
            self.assertTrue((tmp_out / "static" / "style.css").is_file())
            for mod_num in ("01", "02", "03", "04"):
                self.assertTrue((tmp_out / "static" / "audio" / f"academia_mod_{mod_num}.mp3").is_file())

            acad_sub_html = (tmp_out / "academia" / "index.html").read_text(encoding="utf-8")
            self.assertIn("../static/style.css", acad_sub_html)
            self.assertIn("../static/audio/academia_mod_01.mp3", acad_sub_html)
            self.assertIn("hk_static_student_v1", acad_sub_html)
            self.assertIn('id="staticStudentArea"', acad_sub_html)
            self.assertIn('id="examForm"', acad_sub_html)

            acad_root_html = (tmp_out / "academia.html").read_text(encoding="utf-8")
            self.assertIn("./static/style.css", acad_root_html)
            self.assertIn("./static/audio/academia_mod_01.mp3", acad_root_html)
        finally:
            shutil.rmtree(tmp_out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
