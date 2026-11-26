import csv
import io
import logging
import random
import requests
import config
import database
import telegram_sender

logger = logging.getLogger(__name__)

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SinaisVIP/1.0"
}


def _fetch_binance_candles(binance_symbol: str, limit: int = 60):
    url = "https://api.binance.com/api/v3/klines"
    resp = requests.get(
        url,
        params={"symbol": binance_symbol, "interval": "1h", "limit": limit},
        headers=_HTTP_HEADERS,
        timeout=6,
    )
    resp.raise_for_status()
    rows = resp.json()
    highs = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    closes = [float(r[4]) for r in rows]
    return highs, lows, closes


def _fetch_yahoo_candles(yahoo_symbol: str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    resp = requests.get(
        url,
        params={"range": "5d", "interval": "1h"},
        headers=_HTTP_HEADERS,
        timeout=6,
    )
    resp.raise_for_status()
    data = resp.json()
    result = data["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    highs, lows, closes = [], [], []
    for h, l, c in zip(quote.get("high", []), quote.get("low", []), quote.get("close", [])):
        if h is not None and l is not None and c is not None:
            highs.append(float(h))
            lows.append(float(l))
            closes.append(float(c))
    if len(closes) < 25:
        raise ValueError("Dados insuficientes do Yahoo Finance")
    return highs[-60:], lows[-60:], closes[-60:]


def _fetch_stooq_price(stooq_symbol: str):
    url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
    resp = requests.get(url, headers=_HTTP_HEADERS, timeout=6)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        close_val = row.get("Close")
        if close_val and close_val != "N/D":
            return float(close_val)
    raise ValueError("Preço indisponível na Stooq")


def _generate_simulated_candles(base_price: float, count: int = 60):
    """Contingência local para garantir continuidade em ambiente offline."""
    closes = [base_price]
    highs = [base_price * 1.003]
    lows = [base_price * 0.997]
    for _ in range(count - 1):
        drift = random.uniform(-0.008, 0.008)
        c = max(0.0001, closes[-1] * (1 + drift))
        h = c * (1 + random.uniform(0.001, 0.005))
        l = c * (1 - random.uniform(0.001, 0.005))
        closes.append(c)
        highs.append(h)
        lows.append(l)
    return highs, lows, closes


def get_candles(categoria: str, ativo: str, allow_fallback: bool | None = None):
    """Retorna (highs, lows, closes, fonte) para o ativo.
    Quando allow_fallback=False (modo estrito para estratégias), nunca gera candles simulados
    e retorna ('indisponível', 'indisponível', 'indisponível', 'indisponível') se falhar.
    """
    item = config.find_asset_config(categoria, ativo) or {}
    fallback = float(item.get("fallback_price", 100.0))

    if item.get("binance"):
        try:
            h, l, c = _fetch_binance_candles(item["binance"])
            return h, l, c, "Binance"
        except Exception as exc:
            logger.debug("Binance falhou para %s: %s", ativo, exc)

    if item.get("yahoo"):
        try:
            h, l, c = _fetch_yahoo_candles(item["yahoo"])
            return h, l, c, "Yahoo"
        except Exception as exc:
            logger.debug("Yahoo falhou para %s: %s", ativo, exc)

    if allow_fallback is False:
        return "indisponível", "indisponível", "indisponível", "indisponível"

    use_sim = config.ENABLE_SIMULATION_FALLBACK if allow_fallback is None else bool(allow_fallback)
    if use_sim:
        h, l, c = _generate_simulated_candles(fallback)
        return h, l, c, "SIMULADO (Contingência Local)"

    raise RuntimeError(f"Sem fonte de dados disponível para {ativo}")


def get_current_price(categoria: str, ativo: str, allow_fallback: bool | None = None) -> tuple:
    """Retorna (preco_atual, fonte).
    Quando allow_fallback=False (modo estrito), retorna ('indisponível', 'indisponível') se falhar.
    """
    item = config.find_asset_config(categoria, ativo) or {}
    fallback = float(item.get("fallback_price", 100.0))

    if item.get("binance"):
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": item["binance"]},
                headers=_HTTP_HEADERS,
                timeout=5,
            )
            resp.raise_for_status()
            return float(resp.json()["price"]), "Binance"
        except Exception:
            pass

    if item.get("yahoo"):
        try:
            _, _, closes = _fetch_yahoo_candles(item["yahoo"])
            return closes[-1], "Yahoo"
        except Exception:
            pass

    if item.get("stooq"):
        try:
            return _fetch_stooq_price(item["stooq"]), "Stooq"
        except Exception:
            pass

    if allow_fallback is False:
        return "indisponível", "indisponível"

    use_sim = config.ENABLE_SIMULATION_FALLBACK if allow_fallback is None else bool(allow_fallback)
    if use_sim:
        jitter = random.uniform(-0.004, 0.004)
        return round(fallback * (1 + jitter), item.get("decimals", 2)), "SIMULADO (Contingência Local)"

    return fallback, "SIMULADO (Fallback Estático)"


def calc_ema(values: list, period: int) -> list:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(values[:period]) / period]
    for price in values[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def calc_rsi(closes: list, period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas[-period:]]
    losses = [abs(min(d, 0.0)) for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def calc_atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    if len(closes) <= period:
        return abs(closes[-1] * 0.01)
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


def score_asset_setup(
    direcao: str,
    closes: list,
    ema_fast: list,
    ema_slow: list,
    rsi: float,
    atr: float,
    rr_tp2: float,
) -> int:
    """Analista Quantitativo Avançado: pontua o setup de 0 a 100 combinando
    momentum multi-candle, inclinação de médias, zona de RSI, regime de ATR% e assimetria R:R.
    """
    preco = closes[-1] if closes else 1.0
    score = 0.0

    # 1. Tendência & Momentum Multi-Candle (até 35 pts)
    spread_pct = abs(ema_fast[-1] - ema_slow[-1]) / max(preco, 1e-6) * 100.0
    slope_ok = (ema_fast[-1] > ema_fast[-2]) if direcao == "COMPRA" else (ema_fast[-1] < ema_fast[-2])
    mom_5 = ((closes[-1] - closes[-6]) / max(closes[-6], 1e-6) * 100.0) if len(closes) >= 6 else 0.0
    mom_aligned = (mom_5 > 0) if direcao == "COMPRA" else (mom_5 < 0)
    score += min(15.0, spread_pct * 25.0)
    if slope_ok:
        score += 10.0
    if mom_aligned:
        score += 10.0

    # 2. Zona Saudável de RSI (até 25 pts)
    if direcao == "COMPRA":
        if 50.0 <= rsi <= 64.0:
            score += 25.0
        elif 45.0 <= rsi < 69.0:
            score += 16.0
        else:
            score += 8.0
    else:
        if 36.0 <= rsi <= 50.0:
            score += 25.0
        elif 31.0 < rsi <= 55.0:
            score += 16.0
        else:
            score += 8.0

    # 3. Regime de Volatilidade ATR% (até 20 pts — evita ativos travados ou em exaustão)
    atr_pct = (atr / max(preco, 1e-6)) * 100.0
    if 0.25 <= atr_pct <= 2.5:
        score += 20.0
    elif 0.10 <= atr_pct <= 4.5:
        score += 12.0
    else:
        score += 5.0

    # 4. Assimetria Risco/Retorno até TP2 (até 20 pts)
    if rr_tp2 >= 2.0:
        score += 20.0
    elif rr_tp2 >= 1.5:
        score += 12.0
    else:
        score += 4.0

    return max(0, min(100, int(round(score))))


def analyze_asset(categoria: str, asset: dict):
    """Analisa um ativo com EMA9/EMA21 + RSI + ATR + Score do Analista Avançado."""
    symbol = asset["symbol"]
    decimals = asset.get("decimals", 2)

    highs, lows, closes, fonte = get_candles(categoria, symbol)
    if len(closes) < config.EMA_SLOW + 2:
        return None

    ema_fast = calc_ema(closes, config.EMA_FAST)
    ema_slow = calc_ema(closes, config.EMA_SLOW)

    # Alinha pelo final das séries
    fast_curr, fast_prev = ema_fast[-1], ema_fast[-2]
    slow_curr, slow_prev = ema_slow[-1], ema_slow[-2]
    rsi = calc_rsi(closes, config.RSI_PERIOD)
    atr = calc_atr(highs, lows, closes, config.ATR_PERIOD)
    preco = closes[-1]

    direcao = None
    motivo = ""

    # Cruzamento de alta ou tendência de alta com RSI saudável
    if (fast_prev <= slow_prev and fast_curr > slow_curr) or (fast_curr > slow_curr and 45 <= rsi <= config.RSI_OVERBOUGHT):
        if rsi < config.RSI_OVERBOUGHT:
            direcao = "COMPRA"
            motivo = f"EMA{config.EMA_FAST}>{config.EMA_SLOW} | RSI {rsi} | Fonte: {fonte}"
    elif (fast_prev >= slow_prev and fast_curr < slow_curr) or (fast_curr < slow_curr and config.RSI_OVERSOLD <= rsi <= 55):
        if rsi > config.RSI_OVERSOLD:
            direcao = "VENDA"
            motivo = f"EMA{config.EMA_FAST}<{config.EMA_SLOW} | RSI {rsi} | Fonte: {fonte}"

    if not direcao:
        return None

    atr_safe = max(atr, preco * 0.004)
    if direcao == "COMPRA":
        sl = preco - (1.5 * atr_safe)
        tp1 = preco + (1.8 * atr_safe)
        tp2 = preco + (3.2 * atr_safe)
    else:
        sl = preco + (1.5 * atr_safe)
        tp1 = preco - (1.8 * atr_safe)
        tp2 = preco - (3.2 * atr_safe)

    risk_dist = abs(preco - sl)
    rr_tp2 = abs(tp2 - preco) / risk_dist if risk_dist > 0 else 0.0
    score = score_asset_setup(direcao, closes, ema_fast, ema_slow, rsi, atr_safe, rr_tp2)
    motivo = f"Score Analista: {score}/100 | {motivo}"

    return {
        "categoria": categoria,
        "ativo": symbol,
        "direcao": direcao,
        "entrada": round(preco, decimals),
        "sl": round(sl, decimals),
        "tp1": round(tp1, decimals),
        "tp2": round(tp2, decimals),
        "preco_atual": round(preco, decimals),
        "destino": "VIP",
        "origem": "ROBO",
        "observacao": motivo,
        "score": score,
    }


def scan_and_generate_signals(max_new_per_run: int = 2) -> dict:
    """Varre o catálogo com o Analista Avançado (ranqueamento por score + anti-correlação)
    e publica os melhores sinais respeitando anti-duplicidade.
    """
    created = []
    skipped_dup = 0
    checked = 0
    candidates = []

    for categoria, ativos in config.CATALOGO_ATIVOS.items():
        for asset in ativos:
            checked += 1
            symbol = asset["symbol"]
            if database.has_recent_open_or_duplicate_signal(symbol, config.ANTI_DUPLICATE_MINUTES):
                skipped_dup += 1
                continue

            try:
                sig_data = analyze_asset(categoria, asset)
                if sig_data and sig_data.get("score", 0) >= 60:
                    candidates.append(sig_data)
            except Exception as exc:
                logger.warning("Erro ao analisar %s: %s", symbol, exc)

    # Ranqueia por Score do Analista Avançado (maior convicção primeiro)
    candidates.sort(key=lambda item: item.get("score", 0), reverse=True)

    # Filtro anti-correlação opcional (desabilitado por padrão em config.ENABLE_ANTI_CORRELATION_FILTER)
    used_categories = set()
    for sig_data in candidates:
        if len(created) >= max_new_per_run:
            break
        cat = sig_data["categoria"]
        if config.ENABLE_ANTI_CORRELATION_FILTER and cat in used_categories:
            continue
        payload = {k: v for k, v in sig_data.items() if k != "score"}
        sig_id = database.insert_signal(payload)
        full_sig = database.get_signal_by_id(sig_id)
        telegram_sender.publish_signal_to_telegram(full_sig)
        created.append(full_sig)
        used_categories.add(cat)

    database.set_setting("last_scan_at", database.now_str())
    return {
        "checked": checked,
        "skipped_duplicate": skipped_dup,
        "created_count": len(created),
        "created_signals": created,
    }
