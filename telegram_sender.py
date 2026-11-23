import html
import logging
import requests
import config
import database

logger = logging.getLogger(__name__)


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"


def _format_price(val: float, decimals: int = 2) -> str:
    return f"{val:.{decimals}f}"


def _get_decimals(categoria: str, ativo: str) -> int:
    item = config.find_asset_config(categoria, ativo)
    if item:
        return item.get("decimals", 2)
    return 4 if categoria == "Forex" else 2


def format_signal_html(signal: dict, is_free_preview: bool = False) -> str:
    cat_tag = html.escape(signal["categoria"].upper())
    ativo = html.escape(signal["ativo"])
    direcao = html.escape(signal["direcao"])
    emoji_dir = "🟢 COMPRA" if direcao == "COMPRA" else "🔴 VENDA"
    dec = _get_decimals(signal["categoria"], signal["ativo"])

    entrada = _format_price(float(signal["entrada"]), dec)
    sl = _format_price(float(signal["sl"]), dec)
    tp1 = _format_price(float(signal["tp1"]), dec)
    tp2 = _format_price(float(signal["tp2"]), dec)

    risco = abs(float(signal["entrada"]) - float(signal["sl"]))
    retorno = abs(float(signal["tp2"]) - float(signal["entrada"]))
    rr = round(retorno / risco, 2) if risco > 0 else 0.0

    obs = html.escape(signal.get("observacao") or "")
    header = f"<b>[{cat_tag}] {ativo} — {emoji_dir}</b>"
    if is_free_preview:
        header = f"🎁 <b>SINAL VITRINE</b>\n{header}"

    linhas = [
        header,
        "",
        f"📍 <b>Entrada:</b> <code>{entrada}</code>",
        f"🛡 <b>Stop Loss:</b> <code>{sl}</code>",
        f"🎯 <b>Alvo 1 (TP1):</b> <code>{tp1}</code>",
        f"🚀 <b>Alvo 2 (TP2):</b> <code>{tp2}</code>",
        f"⚖️ <b>Risco/Retorno:</b> <code>1:{rr}</code>",
    ]

    if obs:
        linhas.extend(["", f"📝 <i>{obs}</i>"])

    linhas.extend(["", f"🆔 Sinal #{signal['id']} • Auditoria Automática Ativa"])
    return "\n".join(linhas)


def _build_inline_keyboard(destino: str) -> dict:
    buttons = []
    if destino in ("FREE", "AMBOS"):
        buttons.append(
            [
                {"text": "🔓 Desbloquear Acesso VIP", "url": config.CHECKOUT_URL},
                {"text": "📊 Ver Painel", "url": f"{config.SITE_URL}/"},
            ]
        )
    else:
        buttons.append(
            [
                {"text": "💎 Abrir Painel VIP", "url": f"{config.SITE_URL}/vip"},
                {"text": "📈 Transparência", "url": f"{config.SITE_URL}/"},
            ]
        )
    return {"inline_keyboard": buttons}


def send_telegram_message(chat_id: str, text: str, reply_markup: dict = None, reply_to_message_id: int = None) -> dict:
    if not config.BOT_TOKEN or not chat_id:
        return {"ok": False, "skipped": True, "reason": "BOT_TOKEN ou CHAT_ID não configurado"}

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        resp = requests.post(_api_url("sendMessage"), json=payload, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            logger.warning("Erro Telegram sendMessage: %s", data)
        return data
    except Exception as exc:
        logger.warning("Exceção ao enviar para Telegram: %s", exc)
        return {"ok": False, "error": str(exc)}


def publish_signal_to_telegram(signal: dict) -> dict:
    destino = (signal.get("destino") or "VIP").upper()
    results = {"vip": None, "free": None}
    vip_msg_id = None
    free_msg_id = None

    if destino in ("VIP", "AMBOS"):
        text_vip = format_signal_html(signal, is_free_preview=False)
        res = send_telegram_message(config.VIP_CHAT_ID, text_vip, _build_inline_keyboard("VIP"))
        results["vip"] = res
        if res.get("ok"):
            vip_msg_id = res["result"]["message_id"]

    if destino in ("FREE", "AMBOS"):
        text_free = format_signal_html(signal, is_free_preview=True)
        res = send_telegram_message(config.FREE_CHAT_ID, text_free, _build_inline_keyboard("FREE"))
        results["free"] = res
        if res.get("ok"):
            free_msg_id = res["result"]["message_id"]

    if vip_msg_id or free_msg_id:
        database.update_signal_telegram_ids(signal["id"], vip_msg_id=vip_msg_id, free_msg_id=free_msg_id)

    return results


def publish_audit_result_to_telegram(signal: dict) -> dict:
    status = signal["status"]
    cat_tag = html.escape(signal["categoria"].upper())
    ativo = html.escape(signal["ativo"])
    dec = _get_decimals(signal["categoria"], signal["ativo"])
    preco_atual = _format_price(float(signal.get("preco_atual") or signal["entrada"]), dec)
    pct = float(signal.get("resultado_pct") or 0.0)
    sinal_pct = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"

    if status in ("ACERTO_TP1", "ACERTO_TP2"):
        alvo = "TP2 (ALVO MÁXIMO)" if status == "ACERTO_TP2" else "TP1"
        titulo = f"✅ <b>ALVO ATINGIDO — {alvo}</b>"
    else:
        titulo = "❌ <b>STOP LOSS ACIONADO</b>"

    text = "\n".join(
        [
            titulo,
            f"📌 <b>[{cat_tag}] {ativo}</b> ({signal['direcao']})",
            f"💵 <b>Preço de Encerramento:</b> <code>{preco_atual}</code>",
            f"📊 <b>Resultado Auditado:</b> <code>{sinal_pct}</code>",
            f"🆔 Sinal #{signal['id']}",
        ]
    )

    destino = (signal.get("destino") or "VIP").upper()
    results = {}

    if destino in ("VIP", "AMBOS") and config.VIP_CHAT_ID:
        results["vip"] = send_telegram_message(
            config.VIP_CHAT_ID,
            text,
            reply_markup=_build_inline_keyboard("VIP"),
            reply_to_message_id=signal.get("telegram_vip_msg_id"),
        )

    if destino in ("FREE", "AMBOS") and config.FREE_CHAT_ID:
        results["free"] = send_telegram_message(
            config.FREE_CHAT_ID,
            text,
            reply_markup=_build_inline_keyboard("FREE"),
            reply_to_message_id=signal.get("telegram_free_msg_id"),
        )

    return results


def create_vip_invite_link(member_name: str = "") -> dict:
    """Gera link de convite de uso único (member_limit=1) para o canal VIP."""
    if not config.BOT_TOKEN or not config.VIP_CHAT_ID:
        return {
            "ok": False,
            "error": "Configure BOT_TOKEN e VIP_CHAT_ID no arquivo .env para gerar convites reais.",
        }

    payload = {
        "chat_id": config.VIP_CHAT_ID,
        "member_limit": 1,
        "name": f"VIP {member_name[:20]}" if member_name else "Acesso VIP Único",
    }
    try:
        resp = requests.post(_api_url("createChatInviteLink"), json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return {"ok": True, "invite_link": data["result"]["invite_link"]}
        return {"ok": False, "error": data.get("description", "Falha na API do Telegram")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
