from datetime import datetime
import hmac
import logging
import math
import os
import re
import secrets
import sqlite3
from functools import wraps
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

import academy_data
import auditor
import config
import database
import signals_engine
import telegram_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("SESSION_COOKIE_SECURE", "").lower() == "true":
    app.config["SESSION_COOKIE_SECURE"] = True

# Inicializa banco e popula dados iniciais se vazio
database.init_db()
database.seed_initial_data()


TRANSLATIONS = {
    "pt": {
        "site_title": "Heurístika — Sinais & Assimetria de Mercado",
        "util_desk": "MESA DE SINAIS",
        "util_audit": "AUDITORIA AUTOMÁTICA",
        "util_tg": "TELEGRAM VIP",
        "util_mon": "Monitoramento 24/7",
        "util_admin": "Painel Admin",
        "brand_sub1": "Assimetria &",
        "brand_sub2": "Market Edge",
        "nav_markets": "Mercados",
        "nav_signals": "Sinais",
        "nav_portfolios": "Carteiras",
        "nav_academy": "Academia",
        "nav_audit": "Auditoria",
        "nav_plans": "Planos",
        "nav_login": "Entrar",
        "nav_vip_cta": "Acesso VIP",
        "nav_vip_panel": "Terminal VIP",
        "nav_logout": "Sair",
        "hero_pill": "HEURÍSTICA FINANCEIRA • AUDITORIA AO VIVO",
        "hero_h1_top": "Decisões de Mercado",
        "hero_h1_sub": "com Assimetria Quantitativa.",
        "hero_desc": "Sinais em <strong>Forex, Cripto, Índices, Futuros, Ações e Fundos</strong> com entrada, alvos e stop auditados em tempo real.",
        "hero_cta_vip": "Desbloquear VIP",
        "hero_cta_sub": "Já sou Assinante",
        "hero_cta_panel": "Terminal VIP",
        "term_title": "AUDITORIA LIVE",
        "term_closed": "ENCERRADOS",
        "term_winrate": "Taxa de Acerto",
        "term_wl": "Acertos / Stops",
        "term_open": "Em Aberto",
        "m_winrate": "TAXA DE ACERTO",
        "m_targets": "ALVOS (TP1/TP2)",
        "m_cats": "MERCADOS",
        "m_audit": "AUDITORIA",
        "m_edit": "EDIÇÃO MANUAL",
        "src_kicker": "FONTES DE DADOS & AUDITORIA",
        "src_title": "Cotações e resultados validados em fontes públicas",
        "src_badge": "100% AUDITADO",
        "src_1_desc": "Preços e candles 1h em tempo real para BTC, ETH, SOL e BNB.",
        "src_2_desc": "Cotações para Ações, Fundos, Índices e Futuros.",
        "src_3_desc": "Feed institucional para EUR/USD, GBP/USD e USD/JPY.",
        "src_4_desc": "Registro imutável de entrada, TP1, TP2 e Stop Loss.",
        "view_signals": "Ver Sinais",
        "open_title": "Mesa de Operações — Em Aberto",
        "open_sub_free": "sinais vitrine gratuitos",
        "open_sub_vip": "sinais exclusivos VIP",
        "no_open": "Nenhum sinal em aberto nesta categoria no momento. O auditor continua monitorando o mercado.",
        "see_history": "Ver Histórico Auditado",
        "showcase": "VITRINE",
        "buy": "COMPRA",
        "sell": "VENDA",
        "entry": "Entrada",
        "sl": "Stop Loss",
        "tp1": "Alvo 1 (TP1)",
        "tp2": "Alvo 2 (TP2)",
        "current": "Atual",
        "vip_asset": "ATIVO VIP",
        "vip_signal": "SINAL VIP",
        "vip_monitoring": "Operação ativa em monitoramento",
        "open_in_vip": "Abrir no Terminal VIP →",
        "hist_title": "Livro Razão — Histórico Auditado",
        "hist_sub": "Todos os acertos e stops registrados automaticamente",
        "th_cat": "Categoria",
        "th_asset": "Ativo",
        "th_dir": "Direção",
        "th_entry": "Entrada",
        "th_close": "Fechamento",
        "th_status": "Status Auditado",
        "th_var": "Variação",
        "th_closed_at": "Encerrado em",
        "no_hist": "Nenhum sinal encerrado nesta categoria ainda.",
        "plans_title": "Acesso ao Terminal VIP & Telegram",
        "plans_sub": "Pagamento exclusivo via transferência Pix • Sem cobrança automática no cartão",
        "support_btn": "Falar com Atendimento",
        "pay_pix": "Pagar via Pix",
        "pix_badge": "PAGAMENTO EXCLUSIVO PIX",
        "pix_modal_title": "Assinar Plano",
        "pix_value_lbl": "Valor da transferência:",
        "pix_recv_lbl": "Favorecido:",
        "pix_mode_lbl": "Modalidade:",
        "pix_copy": "Copiar Chave",
        "pix_copied": "Copiado!",
        "pix_hint": "Após realizar o Pix, envie o comprovante para receber seu código de acesso VIP e o link único do Telegram.",
        "pix_send_btn": "Enviar Comprovante e Liberar Acesso",
        "disclaimer_title": "Aviso Legal de Risco:",
        "disclaimer_body": "As informações, análises e sinais publicados neste terminal têm caráter estritamente educacional e informativo, não constituindo recomendação personalizada de investimento. Operações em renda variável, criptoativos, forex, derivativos e futuros envolvem risco significativo de perda financeira. Resultados passados não garantem retornos futuros.",
        "footer_text": "Heurístika • Heurística Financeira & Auditoria Quantitativa",
    },
    "en": {
        "site_title": "Heurístika — Market Signals & Quantitative Asymmetry",
        "util_desk": "SIGNALS DESK",
        "util_audit": "AUTO AUDIT",
        "util_tg": "VIP TELEGRAM",
        "util_mon": "24/7 Monitoring",
        "util_admin": "Admin Panel",
        "brand_sub1": "Asymmetry &",
        "brand_sub2": "Market Edge",
        "nav_markets": "Markets",
        "nav_signals": "Signals",
        "nav_portfolios": "Portfolios",
        "nav_academy": "Academy",
        "nav_audit": "Audit",
        "nav_plans": "Plans",
        "nav_login": "Sign In",
        "nav_vip_cta": "VIP Access",
        "nav_vip_panel": "VIP Terminal",
        "nav_logout": "Sign Out",
        "hero_pill": "FINANCIAL HEURISTICS • LIVE AUDIT",
        "hero_h1_top": "Market Decisions",
        "hero_h1_sub": "with Quantitative Asymmetry.",
        "hero_desc": "Signals across <strong>Forex, Crypto, Indices, Futures, Stocks and Funds</strong> with live-audited entry, targets and stop.",
        "hero_cta_vip": "Unlock VIP",
        "hero_cta_sub": "Sign In",
        "hero_cta_panel": "VIP Terminal",
        "term_title": "LIVE AUDIT",
        "term_closed": "CLOSED",
        "term_winrate": "Win Rate",
        "term_wl": "Wins / Stops",
        "term_open": "Open",
        "m_winrate": "WIN RATE",
        "m_targets": "TARGETS (TP1/TP2)",
        "m_cats": "MARKETS",
        "m_audit": "AUTO AUDIT",
        "m_edit": "MANUAL EDITS",
        "src_kicker": "DATA SOURCES & AUDIT",
        "src_title": "Quotes and outcomes verified on public market feeds",
        "src_badge": "100% AUDITED",
        "src_1_desc": "Real-time spot prices & 1h candles for BTC, ETH, SOL and BNB.",
        "src_2_desc": "Live quotes for Stocks, Funds, Global Indices and Futures.",
        "src_3_desc": "Institutional FX feed for EUR/USD, GBP/USD and USD/JPY.",
        "src_4_desc": "Immutable entry, TP1, TP2 and Stop Loss ledger.",
        "view_signals": "View Signals",
        "open_title": "Trading Desk — Open Signals",
        "open_sub_free": "free showcase signals",
        "open_sub_vip": "exclusive VIP signals",
        "no_open": "No open signals in this category right now. The auditor continues monitoring the market.",
        "see_history": "View Audited History",
        "showcase": "SHOWCASE",
        "buy": "BUY",
        "sell": "SELL",
        "entry": "Entry",
        "sl": "Stop Loss",
        "tp1": "Target 1 (TP1)",
        "tp2": "Target 2 (TP2)",
        "current": "Current",
        "vip_asset": "VIP ASSET",
        "vip_signal": "VIP SIGNAL",
        "vip_monitoring": "Active trade under live monitoring",
        "open_in_vip": "Open in VIP Terminal →",
        "hist_title": "Verified Ledger — Audited History",
        "hist_sub": "All wins and stops recorded automatically",
        "th_cat": "Category",
        "th_asset": "Asset",
        "th_dir": "Side",
        "th_entry": "Entry",
        "th_close": "Close",
        "th_status": "Audited Status",
        "th_var": "Return",
        "th_closed_at": "Closed at",
        "no_hist": "No closed signals in this category yet.",
        "plans_title": "VIP Terminal & Telegram Access",
        "plans_sub": "Exclusive Pix transfer payment • No automatic card billing",
        "support_btn": "Contact Support",
        "pay_pix": "Pay via Pix",
        "pix_badge": "PIX EXCLUSIVE PAYMENT",
        "pix_modal_title": "Subscribe to",
        "pix_value_lbl": "Transfer amount:",
        "pix_recv_lbl": "Beneficiary:",
        "pix_mode_lbl": "Method:",
        "pix_copy": "Copy Key",
        "pix_copied": "Copied!",
        "pix_hint": "After completing the Pix transfer, send the receipt to receive your VIP access code and single-use Telegram link.",
        "pix_send_btn": "Send Receipt & Unlock Access",
        "disclaimer_title": "Risk Disclaimer:",
        "disclaimer_body": "Information, analysis and signals published on this terminal are strictly educational and informational and do not constitute personalized investment advice. Trading equities, cryptoassets, forex, derivatives and futures involves substantial risk of financial loss. Past performance does not guarantee future results.",
        "footer_text": "Heurístika • Financial Heuristics & Quantitative Audit",
    },
}


def get_lang() -> str:
    lang = session.get("lang", "pt")
    return lang if lang in ("pt", "en") else "pt"


@app.context_processor
def inject_i18n():
    lang = get_lang()
    return {"lang": lang, "t": TRANSLATIONS[lang]}


@app.route("/lang/<lang>")
def set_language(lang):
    if lang in ("pt", "en"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


@app.template_filter("fmt_price")
def fmt_price_filter(value, categoria="", ativo=""):
    if value is None:
        return "-"
    item = config.find_asset_config(categoria, ativo)
    dec = item["decimals"] if item else (4 if categoria == "Forex" else 2)
    try:
        formatted = f"{float(value):,.{dec}f}"
        if get_lang() == "pt":
            formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (TypeError, ValueError):
        return str(value)


@app.template_filter("fmt_pct")
def fmt_pct_filter(value, decimals=2, signed=False, strip_zero=False):
    if value is None:
        return "-"
    try:
        num = float(value)
        prefix = "+" if (signed and num >= 0) else ""
        if strip_zero and abs(num - round(num)) < 1e-9:
            formatted = f"{prefix}{int(round(num))}%"
        else:
            formatted = f"{prefix}{num:.{decimals}f}%"
        if get_lang() == "pt":
            formatted = formatted.replace(".", ",")
        return formatted
    except (TypeError, ValueError):
        return str(value)


@app.template_filter("fmt_dt")
def fmt_dt_filter(value):
    if not value:
        return "-"
    if get_lang() == "pt":
        try:
            dt = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass
    return str(value)


@app.template_filter("fmt_date")
def fmt_date_filter(value):
    if not value:
        return "-"
    raw = str(value).strip()[:10]
    if get_lang() == "pt":
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return str(value)


@app.template_filter("fmt_duration")
def fmt_duration_filter(value):
    try:
        total_sec = max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return "00:00"
    mm, ss = divmod(total_sec, 60)
    return f"{mm:02d}:{ss:02d}"


def _parse_number(raw) -> float:
    """Converte string numérica PT-BR ou EN para float finito."""
    s = str(raw if raw is not None else "").strip().replace(" ", "")
    if not s:
        raise ValueError("Campo numérico obrigatório.")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    val = float(s)
    if not math.isfinite(val):
        raise ValueError("Valor numérico inválido.")
    return val


def _validate_signal_levels(direcao: str, entrada: float, sl: float, tp1: float, tp2: float):
    """Valida coerência operacional entre Entrada, Stop Loss, TP1 e TP2."""
    if min(entrada, sl, tp1, tp2) <= 0:
        return "Todos os preços (Entrada, SL, TP1 e TP2) devem ser maiores que zero."
    if direcao == "COMPRA":
        if not (sl < entrada < tp1 < tp2):
            return "Para COMPRA, os níveis devem respeitar: Stop Loss < Entrada < TP1 < TP2."
    elif direcao == "VENDA":
        if not (tp2 < tp1 < entrada < sl):
            return "Para VENDA, os níveis devem respeitar: TP2 < TP1 < Entrada < Stop Loss."
    else:
        return "Direção inválida. Use COMPRA ou VENDA."
    return None


def _summarize_telegram_delivery(destino: str, tg_res: dict):
    """Retorna (canais_enviados, motivos_falha) de acordo com o destino do sinal."""
    destino = (destino or "VIP").upper()
    targets = []
    if destino in ("VIP", "AMBOS"):
        targets.append(("vip", "Telegram VIP"))
    if destino in ("FREE", "AMBOS"):
        targets.append(("free", "Telegram Gratuito"))

    sent = []
    failed = []
    for key, label in targets:
        res = (tg_res or {}).get(key)
        if res and res.get("ok"):
            sent.append(label)
        else:
            reason = (
                (res or {}).get("reason")
                or (res or {}).get("description")
                or (res or {}).get("error")
                or "BOT_TOKEN ou CHAT_ID não configurado"
            )
            short_tag = "VIP" if key == "vip" else "Gratuito"
            failed.append(f"{short_tag} ({reason})")
    return sent, failed


def vip_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        sub_id = session.get("vip_subscriber_id")
        if not sub_id:
            return redirect(url_for("login"))
        sub = database.get_subscriber_by_id(sub_id)
        if not database.is_subscriber_valid(sub):
            session.pop("vip_subscriber_id", None)
            flash("Sua assinatura está inativa ou expirada.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def _get_admin_csrf_token() -> str:
    token = session.get("_admin_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_admin_csrf_token"] = token
    return token


def _validate_vigencia(vigencia: str) -> str:
    val = (vigencia or "").strip()
    try:
        datetime.strptime(val, "%d/%m/%Y")
    except ValueError as exc:
        raise ValueError("Vigência inválida. Use o formato DD/MM/AAAA.") from exc
    return val


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        if request.method == "POST":
            expected = str(session.get("_admin_csrf_token") or "")
            provided = str(request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or "")
            if not expected or not hmac.compare_digest(provided, expected):
                flash("Token de segurança expirado ou inválido. Recarregue a página e tente novamente.", "error")
                return redirect(url_for("admin_panel")), 403
        return view(*args, **kwargs)

    return wrapped


# ==============================================================================
# ROTAS PÚBLICAS & VITRINE
# ==============================================================================
@app.route("/")
def index():
    categoria = request.args.get("categoria", "Todos")
    if categoria not in ["Todos"] + config.CATEGORIAS:
        categoria = "Todos"

    stats = database.get_performance_stats(categoria)
    all_open = database.list_signals(categoria=categoria, status_list=["ABERTO"], limit=50)
    free_open = [s for s in all_open if s["destino"] in ("FREE", "AMBOS")]
    vip_open = [s for s in all_open if s["destino"] == "VIP"]

    closed_history = database.list_signals(
        categoria=categoria,
        status_list=["ACERTO_TP1", "ACERTO_TP2", "ERRO_SL"],
        limit=30,
    )

    # Curva de equity real calculada em ordem cronológica a partir dos sinais encerrados
    chronological = list(reversed(closed_history))
    equity_points = [0.0]
    acc = 0.0
    for item in chronological:
        acc = round(acc + float(item.get("resultado_pct") or 0.0), 2)
        equity_points.append(acc)

    ticker_assets = []
    for cat_name, items in config.CATALOGO_ATIVOS.items():
        for it in items[:2]:
            ticker_assets.append({"categoria": cat_name, "symbol": it["symbol"], "price": it["fallback_price"], "decimals": it["decimals"]})

    is_vip = bool(session.get("vip_subscriber_id"))
    return render_template(
        "index.html",
        categorias=["Todos"] + config.CATEGORIAS,
        categoria_ativa=categoria,
        stats=stats,
        free_open=free_open,
        vip_open=vip_open,
        closed_history=closed_history,
        equity_points=equity_points,
        ticker_assets=ticker_assets,
        planos=config.PLANOS,
        checkout_url=config.CHECKOUT_URL,
        suporte_url=config.SUPORTE_URL,
        pix_key=config.PIX_KEY,
        pix_receiver=config.PIX_RECEIVER,
        pix_institution=config.PIX_INSTITUTION,
        is_vip=is_vip,
    )


# ==============================================================================
# ÁREA DO ASSINANTE VIP
# ==============================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("vip_subscriber_id"):
        return redirect(url_for("vip_area"))

    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        sub = database.authenticate_subscriber(identificador)
        if sub:
            session["vip_subscriber_id"] = sub["id"]
            flash(f"Bem-vindo(a), {sub['nome']}!", "success")
            return redirect(url_for("vip_area"))
        flash("E-mail/contato ou código de acesso inválido, inativo ou expirado.", "error")

    return render_template(
        "login.html",
        checkout_url=config.CHECKOUT_URL,
        suporte_url=config.SUPORTE_URL,
    )


@app.route("/logout")
def logout():
    session.pop("vip_subscriber_id", None)
    flash("Você saiu da Área VIP.", "info")
    return redirect(url_for("index"))


@app.route("/vip")
@vip_required
def vip_area():
    sub = database.get_subscriber_by_id(session["vip_subscriber_id"])
    categoria = request.args.get("categoria", "Todos")
    if categoria not in ["Todos"] + config.CATEGORIAS:
        categoria = "Todos"

    stats = database.get_performance_stats(categoria)
    open_signals = database.list_signals(categoria=categoria, status_list=["ABERTO"], limit=100)
    closed_history = database.list_signals(
        categoria=categoria,
        status_list=["ACERTO_TP1", "ACERTO_TP2", "ERRO_SL"],
        limit=100,
    )
    telegram_link = sub.get("telegram_invite_link") or config.TELEGRAM_VIP_CHANNEL_URL

    return render_template(
        "vip.html",
        subscriber=sub,
        categorias=["Todos"] + config.CATEGORIAS,
        categoria_ativa=categoria,
        stats=stats,
        open_signals=open_signals,
        closed_history=closed_history,
        telegram_link=telegram_link,
        suporte_url=config.SUPORTE_URL,
    )


# ==============================================================================
# PAINEL ADMINISTRATIVO
# ==============================================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        _get_admin_csrf_token()
        return redirect(url_for("admin_panel"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(str(password), str(config.ADMIN_PASSWORD)):
            session["is_admin"] = True
            session["_admin_csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin_panel"))
        flash("Senha administrativa incorreta.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.pop("is_admin", None)
    session.pop("_admin_csrf_token", None)
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_panel():
    tab = request.args.get("tab", "disparo")
    if tab not in ("disparo", "auditoria", "assinantes", "carteiras"):
        tab = "disparo"

    stats = database.get_performance_stats()
    stats_by_cat = database.get_stats_by_category()
    signals = database.list_signals(limit=200)
    subscribers = database.list_subscribers()
    settings = database.get_all_settings()
    portfolios = database.list_portfolios()
    portfolio_summary = database.get_portfolio_weight_summary()
    portfolio_invalid_count = sum(1 for r in portfolio_summary if not r["ok"])

    return render_template(
        "admin.html",
        active_tab=tab,
        csrf_token=_get_admin_csrf_token(),
        categorias=config.CATEGORIAS,
        catalogo=config.CATALOGO_ATIVOS,
        stats=stats,
        stats_by_cat=stats_by_cat,
        signals=signals,
        subscribers=subscribers,
        settings=settings,
        portfolios=portfolios,
        today_iso=datetime.now().strftime("%Y-%m-%d"),
        telegram_vip_ok=bool(config.BOT_TOKEN and config.VIP_CHAT_ID),
        telegram_free_ok=bool(config.BOT_TOKEN and config.FREE_CHAT_ID),
        portfolio_summary=portfolio_summary,
        portfolio_invalid_count=portfolio_invalid_count,
        horizontes=["Curto (2 anos)", "Médio (5 anos)", "Longo (10+ anos)"],
        perfis=["Conservador", "Moderado", "Agressivo"],
        planos_disponiveis=["Mensal", "Trimestral", "Anual", "Vitalício"],
    )


@app.route("/admin/api/quote")
@admin_required
def admin_api_quote():
    categoria = request.args.get("categoria", "").strip()
    ativo = request.args.get("ativo", "").strip()
    if not ativo:
        return jsonify({"ok": False, "error": "Informe o ativo."}), 400

    item = config.find_asset_config(categoria, ativo)
    dec = item["decimals"] if item else (4 if categoria == "Forex" else 2)
    try:
        preco_raw, fonte = signals_engine.get_current_price(categoria, ativo)
        preco_val = float(preco_raw)
        if preco_val <= 0:
            raise ValueError("Cotação inválida recebida da fonte de dados.")
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    while dec < 8 and (preco_val * 0.012) < (10 ** (-dec)):
        dec += 1

    preco = round(preco_val, dec)
    if preco <= 0:
        preco = preco_val
    step = 10 ** (-dec)

    sl_c = round(preco * 0.988, dec)
    if sl_c >= preco:
        sl_c = round(max(step, preco - step), dec)
    tp1_c = round(preco * 1.018, dec)
    if tp1_c <= preco:
        tp1_c = round(preco + step, dec)
    tp2_c = round(preco * 1.032, dec)
    if tp2_c <= tp1_c:
        tp2_c = round(tp1_c + step, dec)

    sl_v = round(preco * 1.012, dec)
    if sl_v <= preco:
        sl_v = round(preco + step, dec)
    tp1_v = round(preco * 0.982, dec)
    if tp1_v >= preco:
        tp1_v = round(max(step * 2, preco - step), dec)
    tp2_v = round(preco * 0.968, dec)
    if tp2_v >= tp1_v:
        tp2_v = round(max(step, tp1_v - step), dec)

    return jsonify(
        {
            "ok": True,
            "preco": preco,
            "fonte": fonte,
            "decimals": dec,
            "sugestao": {
                "COMPRA": {"sl": sl_c, "tp1": tp1_c, "tp2": tp2_c},
                "VENDA": {"sl": sl_v, "tp1": tp1_v, "tp2": tp2_v},
            },
        }
    )


@app.route("/admin/portfolio/add", methods=["POST"])
@admin_required
def admin_portfolio_add():
    try:
        horizonte = request.form.get("horizonte", "").strip()
        perfil = request.form.get("perfil", "").strip()
        ativo = request.form.get("ativo", "").strip().upper()
        categoria = request.form.get("categoria", "").strip()
        tese = request.form.get("tese", "").strip()
        vigencia = _validate_vigencia(request.form.get("vigencia") or "01/12/2026")

        if horizonte not in ("Curto (2 anos)", "Médio (5 anos)", "Longo (10+ anos)"):
            raise ValueError("Horizonte inválido.")
        if perfil not in ("Conservador", "Moderado", "Agressivo"):
            raise ValueError("Perfil inválido.")
        if categoria not in config.CATEGORIAS:
            raise ValueError("Categoria inválida.")
        if not ativo or not tese:
            raise ValueError("Preencha o ativo e a tese da alocação.")

        peso_pct = _parse_number(request.form.get("peso_pct"))
        if peso_pct <= 0 or peso_pct > 100:
            raise ValueError("O peso (%) deve estar entre 0,01% e 100%.")

        database.add_portfolio_item(
            horizonte=horizonte,
            perfil=perfil,
            ativo=ativo,
            categoria=categoria,
            peso_pct=peso_pct,
            tese=tese,
            vigencia=vigencia,
        )
        total = database.get_portfolio_combo_weight(horizonte, perfil)
        if abs(total - 100.0) >= 0.01:
            flash(
                f"Ativo {ativo} adicionado em {horizonte} / {perfil}. Atenção: soma atual dos pesos está em {total:g}% (recomendado: 100%).",
                "warning",
            )
        else:
            flash(f"Ativo {ativo} adicionado! Carteira {horizonte} / {perfil} fechou em 100%.", "success")
    except Exception as exc:
        flash(f"Erro ao adicionar ativo na carteira: {exc}", "error")
    return redirect(url_for("admin_panel", tab="carteiras"))


@app.route("/admin/portfolio/<int:item_id>/update", methods=["POST"])
@admin_required
def admin_portfolio_update(item_id):
    try:
        peso_pct = _parse_number(request.form.get("peso_pct"))
        if peso_pct <= 0 or peso_pct > 100:
            raise ValueError("O peso (%) deve estar entre 0,01% e 100%.")
        tese = request.form.get("tese", "").strip()
        raw_vig = request.form.get("vigencia", "").strip()
        vigencia = _validate_vigencia(raw_vig) if raw_vig else ""
        if not tese:
            raise ValueError("A tese não pode ficar vazia.")

        updated = database.update_portfolio_item(item_id, peso_pct, tese, vigencia)
        if not updated:
            flash("Item da carteira não encontrado.", "error")
        else:
            total = database.get_portfolio_combo_weight(updated["horizonte"], updated["perfil"])
            if abs(total - 100.0) >= 0.01:
                flash(
                    f"Item {updated['ativo']} atualizado. Atenção: soma de {updated['horizonte']} / {updated['perfil']} está em {total:g}% (recomendado: 100%).",
                    "warning",
                )
            else:
                flash(
                    f"Item {updated['ativo']} atualizado! Carteira {updated['horizonte']} / {updated['perfil']} fechou em 100%.",
                    "success",
                )
    except Exception as exc:
        flash(f"Erro ao atualizar item da carteira: {exc}", "error")
    return redirect(url_for("admin_panel", tab="carteiras"))


@app.route("/admin/portfolio/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_portfolio_delete(item_id):
    database.delete_portfolio_item(item_id)
    flash("Ativo removido da carteira.", "info")
    return redirect(url_for("admin_panel", tab="carteiras"))


def _classify_portfolio_asset(ativo: str, categoria: str) -> str:
    """Agrupa ativos de carteira em classes institucionais para leitura visual."""
    upper = (ativo or "").upper()
    if any(tok in upper for tok in ("TESOURO", "SELIC", "IPCA", "CDI", "CAIXA", "LCI", "LCA", "CDB")):
        return "Renda Fixa"
    if any(tok in upper for tok in ("HGLG", "MXRF", "XPML", "KNRI", "VISC", "BTLG", "XPLG")) or (
        categoria == "Fundos" and upper.endswith("11") and "IVVB" not in upper and "BOVA" not in upper and "SMAL" not in upper
    ):
        return "FIIs"
    if categoria == "Cripto" or any(tok in upper for tok in ("BTC", "ETH", "SOL", "BNB")):
        return "Cripto"
    if categoria == "Índices" or any(tok in upper for tok in ("IVVB11", "BOVA11", "SPX500", "NDX100")):
        return "ETF / Global"
    if categoria in ("Futuros", "Forex"):
        return "Hedge / Macro"
    if categoria == "Ações":
        return "Ações"
    return categoria or "Fundos"


# ==============================================================================
# CARTEIRAS GERENCIADAS (EXCLUSIVO PLANO ANUAL — VIGÊNCIA 01/12/2026)
# ==============================================================================
@app.route("/carteiras")
def carteiras():
    sub_id = session.get("vip_subscriber_id")
    sub = database.get_subscriber_by_id(sub_id) if sub_id else None
    has_annual_access = bool(database.is_subscriber_valid(sub) and sub["plano"] in ("Anual", "Vitalício"))

    horizonte = request.args.get("horizonte", "Todos")
    perfil = request.args.get("perfil", "Todos")
    horizontes = ["Todos", "Curto (2 anos)", "Médio (5 anos)", "Longo (10+ anos)"]
    perfis = ["Todos", "Conservador", "Moderado", "Agressivo"]

    if horizonte not in horizontes:
        horizonte = "Todos"
    if perfil not in perfis:
        perfil = "Todos"

    items = database.list_portfolios(horizonte=horizonte, perfil=perfil)
    grouped = {}
    for it in items:
        key = (it["horizonte"], it["perfil"], it["vigencia"])
        grouped.setdefault(key, []).append(it)

    all_items = database.list_portfolios(horizonte="Todos", perfil="Todos")
    portfolios_catalog = {}
    for it in all_items:
        combo_key = f"{it['horizonte']}||{it['perfil']}"
        bucket = portfolios_catalog.setdefault(
            combo_key,
            {
                "horizonte": it["horizonte"],
                "perfil": it["perfil"],
                "vigencia": it["vigencia"],
                "ativos": [],
                "classes": {},
            },
        )
        asset_class = _classify_portfolio_asset(it["ativo"], it["categoria"])
        weight = float(it["peso_pct"])
        bucket["classes"][asset_class] = round(bucket["classes"].get(asset_class, 0.0) + weight, 2)
        idx_num = len(bucket["ativos"]) + 1
        bucket["ativos"].append(
            {
                "ativo": it["ativo"] if has_annual_access else f"Ativo Exclusivo #{idx_num}",
                "categoria": it["categoria"],
                "classe": asset_class,
                "peso_pct": weight if has_annual_access else None,
                "tese": it["tese"] if has_annual_access else "Ticker, peso exato e tese quantitativa liberados no Plano Anual / Vitalício.",
                "vigencia": it["vigencia"],
            }
        )

    focus_horizonte = horizonte if horizonte != "Todos" else "Médio (5 anos)"
    focus_perfil = perfil if perfil != "Todos" else "Moderado"

    return render_template(
        "carteiras.html",
        subscriber=sub,
        has_annual_access=has_annual_access,
        horizontes=horizontes,
        perfis=perfis,
        horizonte_ativo=horizonte,
        perfil_ativo=perfil,
        focus_horizonte=focus_horizonte,
        focus_perfil=focus_perfil,
        grouped_portfolios=grouped,
        portfolios_catalog=portfolios_catalog,
        pix_key=config.PIX_KEY,
        pix_receiver=config.PIX_RECEIVER,
        pix_institution=config.PIX_INSTITUTION,
        suporte_url=config.SUPORTE_URL,
    )


# ==============================================================================
# ACADEMIA EDUCACIONAL, CADASTRO, PROVA COMPLEXA & CERTIFICADO
# ==============================================================================
def _mask_certificate_id(documento: str, email: str) -> str:
    doc = (documento or "").strip()
    if doc:
        digits = re.sub(r"\D", "", doc)
        if len(digits) == 11:
            return f"***.{digits[3:6]}.{digits[6:9]}-**"
        if len(doc) > 4:
            return f"{doc[:2]}***{doc[-2:]}"
        return "***"

    mail = (email or "").strip()
    if "@" in mail:
        local, domain = mail.split("@", 1)
        prefix = local[:2] if len(local) >= 2 else local[:1]
        return f"{prefix}***@{domain}"
    return "Verificado"


def _build_exam_result_view(raw_result: dict | None) -> dict | None:
    if not raw_result:
        return None
    if "revisao" in raw_result:
        return raw_result

    respostas = raw_result.get("respostas") or {}
    revisao = []
    for q in academy_data.PROVA_QUESTOES:
        qid = q["id"]
        resp_user = str(respostas.get(qid, "")).strip().lower()
        options_map = {opt_val: opt_lbl for opt_val, opt_lbl in q["opcoes"]}
        revisao.append({
            "enunciado": q["enunciado"],
            "acertou": resp_user == q["correta"],
            "explicacao": q["explicacao"],
            "resposta_usuario": resp_user.upper() if resp_user else "Em branco",
            "resposta_usuario_texto": options_map.get(resp_user, ""),
            "correta": q["correta"].upper(),
        })

    return {
        "aprovado": bool(raw_result.get("aprovado")),
        "nota_pct": raw_result.get("nota_pct", 0.0),
        "acertos": raw_result.get("acertos", 0),
        "total": raw_result.get("total", len(academy_data.PROVA_QUESTOES)),
        "cert_code": raw_result.get("cert_code"),
        "revisao": revisao,
    }


@app.route("/academia")
def academia():
    student_id = session.get("academy_student_id")
    student = database.get_student_by_id(student_id) if student_id else None
    if student_id and not student:
        session.pop("academy_student_id", None)
    certs = database.list_student_certificates(student["id"]) if student else []
    exam_result = _build_exam_result_view(session.pop("last_exam_result", None))
    return render_template(
        "academia.html",
        student=student,
        certificates=certs,
        modulos=academy_data.MODULOS_EDUCACIONAIS,
        questoes=academy_data.PROVA_QUESTOES,
        exam_result=exam_result,
    )


@app.route("/academia/cadastro", methods=["POST"])
def academia_cadastro():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    documento = request.form.get("documento", "").strip()
    pin = request.form.get("pin", "").strip()

    if len(nome) < 3 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(pin) < 4:
        flash("Preencha nome completo (mín. 3 caracteres), e-mail válido e um PIN/senha de pelo menos 4 dígitos.", "error")
        return redirect(url_for("academia") + "#cadastro")

    try:
        student = database.register_student(nome, email, documento, pin)
        session["academy_student_id"] = student["id"]
        flash(f"Cadastro concluído, {student['nome']}! Você já está habilitado para a Prova de Certificação.", "success")
        return redirect(url_for("academia") + "#prova")
    except sqlite3.IntegrityError:
        flash("Este e-mail já está cadastrado. Use o login ao lado com seu PIN.", "warning")
    except Exception:
        app.logger.exception("Erro inesperado ao cadastrar aluno na Academia.")
        flash("Não foi possível concluir o cadastro agora. Tente novamente em instantes.", "error")
    return redirect(url_for("academia") + "#cadastro")


@app.route("/academia/login", methods=["POST"])
def academia_login():
    email = request.form.get("email", "").strip()
    pin = request.form.get("pin", "").strip()
    student = database.authenticate_student(email, pin)
    if student:
        session["academy_student_id"] = student["id"]
        flash(f"Bem-vindo(a) de volta à Academia, {student['nome']}!", "success")
        return redirect(url_for("academia") + "#prova")
    flash("E-mail ou PIN incorretos.", "error")
    return redirect(url_for("academia") + "#cadastro")


@app.route("/academia/logout")
def academia_logout():
    session.pop("academy_student_id", None)
    return redirect(url_for("academia"))


@app.route("/academia/prova", methods=["POST"])
def academia_prova():
    student_id = session.get("academy_student_id")
    student = database.get_student_by_id(student_id) if student_id else None
    if not student:
        session.pop("academy_student_id", None)
        flash("Faça seu cadastro ou login na Academia antes de enviar a prova.", "error")
        return redirect(url_for("academia") + "#cadastro")

    questoes = academy_data.PROVA_QUESTOES
    respostas = {}
    missing = []
    acertos = 0
    for idx, q in enumerate(questoes, start=1):
        valid_vals = {opt_val for opt_val, _ in q["opcoes"]}
        resp_user = request.form.get(q["id"], "").strip().lower()
        if resp_user not in valid_vals:
            missing.append(idx)
            continue
        respostas[q["id"]] = resp_user
        if resp_user == q["correta"]:
            acertos += 1

    if missing:
        flash(
            f"Responda todas as {len(questoes)} questões antes de finalizar a prova (faltam {len(missing)}).",
            "warning",
        )
        return redirect(url_for("academia") + "#prova")

    total = len(questoes)
    nota_pct = round((acertos / total) * 100, 1)
    aprovado = nota_pct >= 70.0
    cert_code = None

    if aprovado:
        cert = database.issue_certificate(student["id"], nota_pct, acertos, total)
        cert_code = cert["codigo"]
        flash(f"Parabéns! Você foi APROVADO com {nota_pct:.0f}% ({acertos}/{total}). Certificado {cert_code} emitido!", "success")
    else:
        flash(f"Nota obtida: {nota_pct:.0f}% ({acertos}/{total}). É necessário atingir 70% (7/10) para emitir o certificado.", "warning")

    session["last_exam_result"] = {
        "aprovado": aprovado,
        "nota_pct": nota_pct,
        "acertos": acertos,
        "total": total,
        "cert_code": cert_code,
        "respostas": respostas,
    }
    return redirect(url_for("academia") + "#resultado-prova")


@app.route("/certificado/<codigo>")
def certificado(codigo):
    cert = database.get_certificate_by_code(codigo)
    if not cert:
        flash("Certificado não encontrado ou código inválido.", "error")
        return redirect(url_for("academia"))
    identificacao_mascarada = _mask_certificate_id(
        cert.get("student_documento") or "",
        cert.get("student_email") or "",
    )
    return render_template("certificado.html", cert=cert, identificacao_mascarada=identificacao_mascarada)


@app.route("/admin/publish", methods=["POST"])
@admin_required
def admin_publish():
    try:
        categoria = request.form.get("categoria", "").strip()
        if categoria not in config.CATEGORIAS:
            raise ValueError("Categoria inválida.")

        ativo = (request.form.get("ativo_custom") or request.form.get("ativo") or "").strip().upper()
        if not ativo:
            raise ValueError("Selecione ou informe um ativo válido.")

        direcao = request.form.get("direcao", "").strip().upper()
        destino = request.form.get("destino", "VIP").strip().upper()
        if destino not in ("VIP", "FREE", "AMBOS"):
            raise ValueError("Destino de publicação inválido.")

        entrada = _parse_number(request.form.get("entrada"))
        sl = _parse_number(request.form.get("sl"))
        tp1 = _parse_number(request.form.get("tp1"))
        tp2 = _parse_number(request.form.get("tp2"))

        err = _validate_signal_levels(direcao, entrada, sl, tp1, tp2)
        if err:
            flash(err, "error")
            return redirect(url_for("admin_panel", tab="disparo"))

        observacao = request.form.get("observacao", "")

        signal_id = database.insert_signal(
            {
                "categoria": categoria,
                "ativo": ativo,
                "direcao": direcao,
                "entrada": entrada,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "preco_atual": entrada,
                "destino": destino,
                "origem": "MANUAL",
                "observacao": observacao,
            }
        )
        sig = database.get_signal_by_id(signal_id)
        tg_res = telegram_sender.publish_signal_to_telegram(sig)
        sent_labels, failed_reasons = _summarize_telegram_delivery(destino, tg_res)

        if failed_reasons:
            flash(
                f"Sinal #{signal_id} ({sig['ativo']}) publicado no Site. Aviso Telegram: {'; '.join(failed_reasons)}.",
                "warning",
            )
        else:
            flash(
                f"Sinal #{signal_id} ({sig['ativo']}) publicado no Site e enviado para {', '.join(sent_labels)}!",
                "success",
            )
    except Exception as exc:
        flash(f"Erro ao publicar sinal: {exc}", "error")

    return redirect(url_for("admin_panel", tab="disparo"))


@app.route("/admin/audit-now", methods=["POST"])
@admin_required
def admin_audit_now():
    res = auditor.audit_open_signals()
    flash(
        f"Auditoria concluída: {res['checked']} sinais verificados, {res['closed_count']} encerrados.",
        "success",
    )
    return redirect(url_for("admin_panel", tab="auditoria"))


@app.route("/admin/scan-now", methods=["POST"])
@admin_required
def admin_scan_now():
    res = signals_engine.scan_and_generate_signals(max_new_per_run=3)
    flash(
        f"Varredura concluída: {res['checked']} ativos analisados, {res['created_count']} novos sinais publicados ({res['skipped_duplicate']} ignorados por anti-duplicidade).",
        "success",
    )
    return redirect(url_for("admin_panel", tab="auditoria"))


@app.route("/admin/toggle-setting", methods=["POST"])
@admin_required
def admin_toggle_setting():
    chave = request.form.get("chave")
    labels = {
        "auto_audit_enabled": ("Auditoria Automática", "ATIVA", "PAUSADA"),
        "auto_scan_enabled": ("Robô de Varredura", "ATIVO", "PAUSADO"),
    }
    if chave in labels:
        atual = database.get_setting(chave, "0")
        novo = "0" if atual == "1" else "1"
        database.set_setting(chave, novo)
        label, state_on, state_off = labels[chave]
        verbo = "atualizada" if chave == "auto_audit_enabled" else "atualizado"
        flash(f"{label} {verbo} para {state_on if novo == '1' else state_off}.", "info")
    return redirect(url_for("admin_panel", tab="auditoria"))


@app.route("/admin/close-signal/<int:signal_id>", methods=["POST"])
@admin_required
def admin_close_signal(signal_id):
    outcome = request.form.get("outcome", "")
    outcome_labels = {
        "ACERTO_TP1": "Acerto TP1",
        "ACERTO_TP2": "Acerto TP2",
        "ERRO_SL": "Stop Loss",
    }
    res = auditor.manual_close_signal(signal_id, outcome)
    if res.get("ok"):
        sig = res["signal"]
        label = outcome_labels.get(sig["status"], sig["status"])
        _, failed_reasons = _summarize_telegram_delivery(sig.get("destino", "VIP"), res.get("telegram") or {})
        if failed_reasons:
            flash(
                f"Sinal #{signal_id} encerrado como {label}. Aviso Telegram: {'; '.join(failed_reasons)}.",
                "warning",
            )
        else:
            flash(f"Sinal #{signal_id} encerrado como {label} e notificado no Telegram.", "success")
    else:
        flash(res.get("error", "Erro ao atualizar sinal."), "error")
    return redirect(url_for("admin_panel", tab="auditoria"))


@app.route("/admin/reopen-signal/<int:signal_id>", methods=["POST"])
@admin_required
def admin_reopen_signal(signal_id):
    res = auditor.reopen_signal(signal_id)
    if res.get("ok"):
        flash(f"Sinal #{signal_id} reaberto para ABERTO.", "info")
    else:
        flash(res.get("error", "Erro ao reabrir sinal."), "error")
    return redirect(url_for("admin_panel", tab="auditoria"))


@app.route("/admin/delete-signal/<int:signal_id>", methods=["POST"])
@admin_required
def admin_delete_signal(signal_id):
    if database.delete_signal(signal_id):
        flash(f"Sinal #{signal_id} removido.", "info")
    else:
        flash("Sinal não encontrado.", "error")
    return redirect(url_for("admin_panel", tab="auditoria"))


@app.route("/admin/subscriber/create", methods=["POST"])
@admin_required
def admin_create_subscriber():
    nome = request.form.get("nome", "").strip()
    contato = request.form.get("contato", "").strip()
    plano = request.form.get("plano", "Mensal")
    dias = {"Mensal": 30, "Trimestral": 90, "Anual": 365, "Vitalício": 36500}.get(plano, 30)

    if not nome or not contato:
        flash("Preencha nome e contato/e-mail do assinante.", "error")
        return redirect(url_for("admin_panel", tab="assinantes"))

    try:
        sub = database.create_subscriber(nome, contato, plano, dias)
        flash(f"Assinante {sub['nome']} criado! Código de acesso: {sub['codigo_acesso']}", "success")
    except Exception as exc:
        flash(f"Erro ao cadastrar assinante (contato já existe?): {exc}", "error")

    return redirect(url_for("admin_panel", tab="assinantes"))


@app.route("/admin/subscriber/<int:sub_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_subscriber(sub_id):
    if database.toggle_subscriber_status(sub_id):
        flash("Status do assinante atualizado.", "info")
    else:
        flash("Assinante não encontrado.", "error")
    return redirect(url_for("admin_panel", tab="assinantes"))


@app.route("/admin/subscriber/<int:sub_id>/renew", methods=["POST"])
@admin_required
def admin_renew_subscriber(sub_id):
    try:
        dias = int(request.form.get("dias", "30"))
    except (TypeError, ValueError):
        dias = 30
    if dias not in (30, 90, 365):
        dias = 30
    nova_data = database.renew_subscriber(sub_id, dias=dias)
    if nova_data:
        try:
            nova_fmt = datetime.strptime(nova_data[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            nova_fmt = nova_data
        flash(f"Assinatura renovada por +{dias} dias (nova validade: {nova_fmt}).", "success")
    else:
        flash("Assinante não encontrado.", "error")
    return redirect(url_for("admin_panel", tab="assinantes"))


@app.route("/admin/subscriber/<int:sub_id>/plan", methods=["POST"])
@admin_required
def admin_update_subscriber_plan(sub_id):
    plano = request.form.get("plano", "").strip()
    if plano not in ("Mensal", "Trimestral", "Anual", "Vitalício"):
        flash("Plano inválido.", "error")
        return redirect(url_for("admin_panel", tab="assinantes"))
    updated = database.update_subscriber_plan(sub_id, plano)
    if updated:
        flash(f"Plano de {updated['nome']} atualizado para {plano}.", "success")
    else:
        flash("Assinante não encontrado.", "error")
    return redirect(url_for("admin_panel", tab="assinantes"))


@app.route("/admin/subscriber/<int:sub_id>/delete", methods=["POST"])
@admin_required
def admin_delete_subscriber(sub_id):
    if database.delete_subscriber(sub_id):
        flash("Assinante removido.", "info")
    else:
        flash("Assinante não encontrado.", "error")
    return redirect(url_for("admin_panel", tab="assinantes"))


@app.route("/admin/subscriber/<int:sub_id>/invite", methods=["POST"])
@admin_required
def admin_generate_invite(sub_id):
    sub = database.get_subscriber_by_id(sub_id)
    if not sub:
        flash("Assinante não encontrado.", "error")
        return redirect(url_for("admin_panel", tab="assinantes"))

    res = telegram_sender.create_vip_invite_link(sub["nome"])
    if res.get("ok"):
        database.set_subscriber_invite_link(sub_id, res["invite_link"])
        flash(f"Link único gerado para {sub['nome']}: {res['invite_link']}", "success")
    else:
        flash(res.get("error", "Não foi possível gerar o convite."), "error")
    return redirect(url_for("admin_panel", tab="assinantes"))


@app.route("/api/stats")
def api_stats():
    categoria = request.args.get("categoria", "Todos")
    return jsonify(database.get_performance_stats(categoria))


@app.route("/api/cron/audit")
def api_cron_audit():
    """Endpoint opcional para cron externo (ex: PythonAnywhere Free + cron-job.org)."""
    token = request.headers.get("X-Cron-Secret") or request.args.get("token", "")
    expected = os.getenv("CRON_SECRET", config.ADMIN_PASSWORD)
    if not hmac.compare_digest(str(token), str(expected)):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    audit_res = auditor.audit_open_signals()
    scan_res = None
    if database.get_setting("auto_scan_enabled", "0") == "1":
        scan_res = signals_engine.scan_and_generate_signals()
    return jsonify({"ok": True, "audit": audit_res, "scan": scan_res})


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "5050"))
    auditor.start_background_worker()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
elif __name__ != "__main__":
    import os
    if os.getenv("RUN_WORKER_ON_IMPORT", "0") == "1":
        auditor.start_background_worker()
