"""
Backtest real desde 01/11/2026 usando candles horários públicos (Binance + Yahoo Finance)
e as regras reais do motor (EMA 9/21 + RSI 14 + ATR 14) para popular o histórico auditado.
"""
from datetime import datetime, timezone
import requests
import config
import database
import signals_engine

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Heuristika/1.0"}
START_DT = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def fetch_binance_since_nov1(binance_symbol: str):
    start_ms = int(START_DT.timestamp() * 1000)
    url = "https://api.binance.com/api/v3/klines"
    resp = requests.get(
        url,
        params={"symbol": binance_symbol, "interval": "1h", "startTime": start_ms, "limit": 1000},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    candles = []
    for r in resp.json():
        candles.append({
            "ts": datetime.fromtimestamp(r[0] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
        })
    return candles


def fetch_yahoo_since_nov1(yahoo_symbol: str):
    period1 = int(START_DT.timestamp())
    period2 = int(datetime.now(timezone.utc).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    resp = requests.get(
        url,
        params={"period1": period1, "period2": period2, "interval": "1h"},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    res = resp.json()["chart"]["result"][0]
    timestamps = res.get("timestamp", [])
    quote = res["indicators"]["quote"][0]
    candles = []
    for ts, o, h, l, c in zip(
        timestamps,
        quote.get("open", []),
        quote.get("high", []),
        quote.get("low", []),
        quote.get("close", []),
    ):
        if None not in (o, h, l, c):
            candles.append({
                "ts": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            })
    return candles


def backtest_asset(categoria: str, asset: dict, max_signals: int = 3):
    symbol = asset["symbol"]
    decimals = asset.get("decimals", 2)
    candles = []
    fonte = ""

    if asset.get("binance"):
        try:
            candles = fetch_binance_since_nov1(asset["binance"])
            fonte = "Binance"
        except Exception:
            candles = []

    if not candles and asset.get("yahoo"):
        try:
            candles = fetch_yahoo_since_nov1(asset["yahoo"])
            fonte = "Yahoo"
        except Exception:
            candles = []

    if len(candles) < 30:
        return []

    results = []
    i = 25
    while i < len(candles) - 2 and len(results) < max_signals:
        window = candles[: i + 1]
        closes = [c["close"] for c in window]
        highs = [c["high"] for c in window]
        lows = [c["low"] for c in window]

        ema_fast = signals_engine.calc_ema(closes, config.EMA_FAST)
        ema_slow = signals_engine.calc_ema(closes, config.EMA_SLOW)
        rsi = signals_engine.calc_rsi(closes, config.RSI_PERIOD)
        atr = signals_engine.calc_atr(highs, lows, closes, config.ATR_PERIOD)

        fast_curr, fast_prev = ema_fast[-1], ema_fast[-2]
        slow_curr, slow_prev = ema_slow[-1], ema_slow[-2]
        preco = closes[-1]

        direcao = None
        if fast_prev <= slow_prev and fast_curr > slow_curr and rsi < config.RSI_OVERBOUGHT:
            direcao = "COMPRA"
        elif fast_prev >= slow_prev and fast_curr < slow_curr and rsi > config.RSI_OVERSOLD:
            direcao = "VENDA"

        if not direcao:
            i += 1
            continue

        atr_safe = max(atr, preco * 0.004)
        if direcao == "COMPRA":
            sl = round(preco - 1.5 * atr_safe, decimals)
            tp1 = round(preco + 1.8 * atr_safe, decimals)
            tp2 = round(preco + 3.2 * atr_safe, decimals)
        else:
            sl = round(preco + 1.5 * atr_safe, decimals)
            tp1 = round(preco - 1.8 * atr_safe, decimals)
            tp2 = round(preco - 3.2 * atr_safe, decimals)

        # Caminha candle a candle para verificar se bateu SL, TP1 ou TP2
        status = "ABERTO"
        exit_price = candles[-1]["close"]
        encerrado_em = None
        hit_tp1 = False
        end_idx = len(candles) - 1

        for j in range(i + 1, len(candles)):
            bar = candles[j]
            if direcao == "COMPRA":
                if bar["low"] <= sl:
                    status = "ACERTO_TP1" if hit_tp1 else "ERRO_SL"
                    exit_price = tp1 if hit_tp1 else sl
                    encerrado_em = bar["ts"]
                    end_idx = j
                    break
                if bar["high"] >= tp2:
                    status = "ACERTO_TP2"
                    exit_price = tp2
                    encerrado_em = bar["ts"]
                    end_idx = j
                    break
                if bar["high"] >= tp1:
                    hit_tp1 = True
            else:
                if bar["high"] >= sl:
                    status = "ACERTO_TP1" if hit_tp1 else "ERRO_SL"
                    exit_price = tp1 if hit_tp1 else sl
                    encerrado_em = bar["ts"]
                    end_idx = j
                    break
                if bar["low"] <= tp2:
                    status = "ACERTO_TP2"
                    exit_price = tp2
                    encerrado_em = bar["ts"]
                    end_idx = j
                    break
                if bar["low"] <= tp1:
                    hit_tp1 = True

        if status == "ABERTO" and hit_tp1:
            status = "ACERTO_TP1"
            exit_price = tp1
            encerrado_em = candles[-1]["ts"]

        pct = (
            ((exit_price - preco) / preco) * 100
            if direcao == "COMPRA"
            else ((preco - exit_price) / preco) * 100
        )

        results.append({
            "categoria": categoria,
            "ativo": symbol,
            "direcao": direcao,
            "entrada": round(preco, decimals),
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "preco_atual": round(exit_price, decimals),
            "destino": "AMBOS" if (len(results) == 0 and categoria in ("Cripto", "Forex")) else "VIP",
            "status": status,
            "resultado_pct": round(pct, 2),
            "origem": "ROBO",
            "observacao": f"Backtest 01/11–20/11 | EMA9/21 + RSI {rsi} | Fonte: {fonte}",
            "criado_em": candles[i]["ts"],
            "encerrado_em": encerrado_em,
        })
        i = end_idx + 12  # espaçamento mínimo entre sinais no mesmo ativo

    return results


def main():
    database.init_db()
    all_signals = []
    for cat, ativos in config.CATALOGO_ATIVOS.items():
        for asset in ativos[:2]:
            sigs = backtest_asset(cat, asset, max_signals=2)
            all_signals.extend(sigs)

    all_signals.sort(key=lambda s: s["criado_em"])

    conn = database.get_connection()
    conn.execute("DELETE FROM signals;")
    for s in all_signals:
        conn.execute(
            """
            INSERT INTO signals (
                categoria, ativo, direcao, entrada, sl, tp1, tp2, preco_atual,
                destino, status, resultado_pct, origem, observacao, criado_em, encerrado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                s["categoria"], s["ativo"], s["direcao"], s["entrada"], s["sl"], s["tp1"], s["tp2"],
                s["preco_atual"], s["destino"], s["status"], s["resultado_pct"], s["origem"],
                s["observacao"], s["criado_em"], s["encerrado_em"],
            ),
        )
    conn.commit()
    conn.close()

    stats = database.get_performance_stats()
    print("=== BACKTEST REAL DESDE 01/11/2026 ===")
    print(f"Total de sinais: {stats['total_sinais']}")
    print(f"Acertos (TP1/TP2): {stats['total_acertos']} (TP1={stats['total_tp1']}, TP2={stats['total_tp2']})")
    print(f"Erros (SL): {stats['total_erros']}")
    print(f"Em Aberto: {stats['abertos']}")
    print(f"Taxa de Acerto: {stats['taxa_acerto']}%")
    print(f"Retorno Acumulado: {stats['retorno_acumulado']}%")


if __name__ == "__main__":
    main()
