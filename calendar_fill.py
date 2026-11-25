"""Regra de calendário (Etapa 3): ativo sem preço numa data usa o último preço válido.

- Nunca exclui um ativo por diferença de calendário (B3, EUA, cripto).
- Preenchimento limitado a ``max_fill`` datas consecutivas; além disso a data fica ausente.
- Antes do primeiro preço válido do ativo nada é preenchido (ativo ainda inexistente).
- Todo preenchimento é registrado (sinalizado) no log retornado.
"""
from __future__ import annotations

from typing import Any

DEFAULT_MAX_FILL = 5


def ffill_price_maps(
    px_maps: dict[str, dict[str, float]],
    dates: list[str],
    max_fill: int = DEFAULT_MAX_FILL,
) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
    filled: dict[str, dict[str, float]] = {}
    log: dict[str, int] = {}
    for sym, m in px_maps.items():
        out: dict[str, float] = {}
        last: float | None = None
        run = 0
        n_fill = 0
        for d in dates:
            v = m.get(d)
            if v is not None:
                out[d] = v
                last = v
                run = 0
            elif last is not None and run < max_fill:
                out[d] = last
                run += 1
                n_fill += 1
            elif last is not None:
                run += 1
        # mantém datas originais fora da grade (ex.: fins de semana de cripto)
        for d, v in m.items():
            out.setdefault(d, v)
        filled[sym] = out
        log[sym] = n_fill
    return filled, log


def ffill_candle_maps(
    by_sym: dict[str, dict[str, dict[str, Any]]],
    dates: list[str],
    max_fill: int = DEFAULT_MAX_FILL,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, int]]:
    """Versão para candles OHLC: barra preenchida = último fechamento (high=low=open=close), flag ffill=True."""
    filled: dict[str, dict[str, dict[str, Any]]] = {}
    log: dict[str, int] = {}
    for sym, m in by_sym.items():
        out: dict[str, dict[str, Any]] = {}
        last: dict[str, Any] | None = None
        run = 0
        n_fill = 0
        for d in dates:
            bar = m.get(d)
            if bar is not None:
                out[d] = bar
                last = bar
                run = 0
            elif last is not None and run < max_fill:
                c = float(last["close"])
                out[d] = {"date": d, "open": c, "high": c, "low": c, "close": c, "ffill": True}
                run += 1
                n_fill += 1
            elif last is not None:
                run += 1
        for d, bar in m.items():
            out.setdefault(d, bar)
        filled[sym] = out
        log[sym] = n_fill
    return filled, log
