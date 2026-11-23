import logging
import threading
import time
import config
import database
import signals_engine
import telegram_sender

logger = logging.getLogger(__name__)
_worker_started = False
_worker_lock = threading.Lock()


def compute_pct_change(direcao: str, entrada: float, preco_saida: float) -> float:
    if not entrada:
        return 0.0
    if direcao == "COMPRA":
        return round(((preco_saida - entrada) / entrada) * 100, 2)
    return round(((entrada - preco_saida) / entrada) * 100, 2)


def evaluate_signal_outcome(signal: dict, preco_atual: float):
    """Retorna novo status ('ACERTO_TP2', 'ACERTO_TP1', 'ERRO_SL') ou None se permanecer ABERTO."""
    direcao = signal["direcao"].upper()
    tp1 = float(signal["tp1"])
    tp2 = float(signal["tp2"])
    sl = float(signal["sl"])

    if direcao == "COMPRA":
        if preco_atual >= tp2:
            return "ACERTO_TP2"
        if preco_atual >= tp1:
            return "ACERTO_TP1"
        if preco_atual <= sl:
            return "ERRO_SL"
    elif direcao == "VENDA":
        if preco_atual <= tp2:
            return "ACERTO_TP2"
        if preco_atual <= tp1:
            return "ACERTO_TP1"
        if preco_atual >= sl:
            return "ERRO_SL"
    return None


def audit_open_signals() -> dict:
    """Consulta o preço atual de todos os sinais ABERTOS, audita e notifica no Telegram."""
    open_signals = database.list_signals(status_list=["ABERTO"], limit=200)
    checked = 0
    closed_list = []

    conn = database.get_connection()
    for sig in open_signals:
        checked += 1
        try:
            preco_atual, _fonte = signals_engine.get_current_price(sig["categoria"], sig["ativo"])
        except Exception as exc:
            logger.warning("Falha ao consultar preço para auditoria de %s: %s", sig["ativo"], exc)
            continue

        novo_status = evaluate_signal_outcome(sig, preco_atual)
        pct = compute_pct_change(sig["direcao"], float(sig["entrada"]), preco_atual)

        if novo_status:
            encerrado_em = database.now_str()
            conn.execute(
                """
                UPDATE signals
                SET preco_atual = ?, status = ?, resultado_pct = ?, encerrado_em = ?
                WHERE id = ?;
                """,
                (preco_atual, novo_status, pct, encerrado_em, sig["id"]),
            )
            conn.commit()
            updated_sig = database.get_signal_by_id(sig["id"])
            telegram_sender.publish_audit_result_to_telegram(updated_sig)
            closed_list.append(updated_sig)
        else:
            conn.execute(
                "UPDATE signals SET preco_atual = ?, resultado_pct = ? WHERE id = ?;",
                (preco_atual, pct, sig["id"]),
            )
            conn.commit()

    conn.close()
    database.set_setting("last_audit_at", database.now_str())
    return {
        "checked": checked,
        "closed_count": len(closed_list),
        "closed_signals": closed_list,
    }


def manual_close_signal(signal_id: int, outcome: str) -> dict:
    """Permite encerrar ou corrigir manualmente qualquer sinal pelo /admin."""
    sig = database.get_signal_by_id(signal_id)
    if not sig:
        return {"ok": False, "error": "Sinal não encontrado"}

    outcome = outcome.upper().strip()
    if outcome not in ("ACERTO_TP1", "ACERTO_TP2", "ERRO_SL"):
        return {"ok": False, "error": "Status inválido"}

    if sig["status"] == outcome:
        return {"ok": False, "error": f"Sinal #{signal_id} já está encerrado como {outcome}."}

    if outcome == "ACERTO_TP2":
        preco_ref = float(sig["tp2"])
    elif outcome == "ACERTO_TP1":
        preco_ref = float(sig["tp1"])
    else:
        preco_ref = float(sig["sl"])

    pct = compute_pct_change(sig["direcao"], float(sig["entrada"]), preco_ref)
    encerrado_em = database.now_str()

    conn = database.get_connection()
    conn.execute(
        """
        UPDATE signals
        SET preco_atual = ?, status = ?, resultado_pct = ?, encerrado_em = ?
        WHERE id = ?;
        """,
        (preco_ref, outcome, pct, encerrado_em, signal_id),
    )
    conn.commit()
    conn.close()

    updated = database.get_signal_by_id(signal_id)
    tg_res = telegram_sender.publish_audit_result_to_telegram(updated)
    return {"ok": True, "signal": updated, "telegram": tg_res}


def reopen_signal(signal_id: int) -> dict:
    """Reabre um sinal encerrado manualmente ou pela auditoria para status ABERTO."""
    sig = database.get_signal_by_id(signal_id)
    if not sig:
        return {"ok": False, "error": "Sinal não encontrado."}
    if sig["status"] == "ABERTO":
        return {"ok": False, "error": f"Sinal #{signal_id} já está ABERTO."}
    database.reopen_signal(signal_id)
    return {"ok": True, "signal": database.get_signal_by_id(signal_id)}


def _background_loop():
    last_scan = 0.0
    last_audit = 0.0
    while True:
        try:
            now = time.time()
            settings = database.get_all_settings()

            if settings.get("auto_audit_enabled") == "1" and (now - last_audit) >= config.AUDIT_INTERVAL_SECONDS:
                audit_open_signals()
                last_audit = now

            if settings.get("auto_scan_enabled") == "1" and (now - last_scan) >= config.SCAN_INTERVAL_SECONDS:
                signals_engine.scan_and_generate_signals()
                last_scan = now
        except Exception as exc:
            logger.warning("Erro no loop de background: %s", exc)
        time.sleep(5)


def start_background_worker():
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        t = threading.Thread(target=_background_loop, daemon=True, name="SignalsAuditorWorker")
        t.start()
        _worker_started = True
