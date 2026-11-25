"""Envio automático de sinais via Telegram Bot API (custo zero, usa %LOCALAPPDATA%\\Heuristika\\.env)."""
from __future__ import annotations

import json
import urllib.request
from typing import Any

import config


def format_signal_message(signal: dict[str, Any]) -> str:
    ativo = signal.get("ativo", "-")
    lado = str(signal.get("direcao") or signal.get("lado") or "COMPRA").upper()
    entrada = signal.get("entrada", "-")
    sl = signal.get("stop_loss", "-")
    tp1 = signal.get("alvo_1") or signal.get("tp1") or "-"
    tp2 = signal.get("alvo_2") or signal.get("tp2") or "-"
    cat = signal.get("categoria", "")
    return (
        f"📡 *Sinal Heurístika* ({cat})\n"
        f"*{ativo}* — {lado}\n"
        f"Entrada: `{entrada}` | Stop: `{sl}`\n"
        f"TP1: `{tp1}` | TP2: `{tp2}`\n"
        f"_Estudo educativo; não é recomendação._"
    )


def send_telegram_message(text: str, chat_id: str | None = None) -> dict[str, Any]:
    token = config.BOT_TOKEN
    target = (chat_id or config.VIP_CHAT_ID or config.ADMIN_CHAT_ID).strip()
    if not token or not target:
        return {"ok": False, "skipped": True, "reason": "BOT_TOKEN ou VIP_CHAT_ID não configurado no .env"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": target, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": bool(data.get("ok")), "result": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
