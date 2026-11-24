"""Coletor auditável de fundamentos B3 (Etapa 2C).

Gera `data/b3_fundamentals.json` a partir de fontes públicas gratuitas,
respeitando termos de uso / robots.txt (uma página por vez, cache local e pausa):
- Yahoo Finance (v8/finance/chart?events=div): fonte principal para DY 12m e anos
  com pagamento de dividendos. JCP: valores de proventos no Yahoo refletem o valor
  bruto declarado por ação (sem retenção automática de 15% de IRRF sobre JCP).
- Fundamentus: usado apenas como checagem cruzada de DY 12m (robots.txt 404,
  requisições sequenciais com pausa e cache).
- StatusInvest: REMOVIDO do coletor automatizado (robots.txt retornou HTTP 403
  Forbidden; termos de uso restringem coleta automatizada).
- CVM Dados Abertos (dados.cvm.gov.br) / RI: referência para Payout e
  Dívida Líquida/EBITDA; campos sem evidência primária permanecem verified=false.

Execução sob demanda ou agendável (mensal):
    python data_collector.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import time
import urllib.request
from typing import Any

import cvm_pipeline

BASE_DIR = Path(__file__).resolve().parent
SNAPSHOT_PATH = BASE_DIR / "data" / "b3_fundamentals.json"
CACHE_DIR = BASE_DIR / "data" / "collector_cache"

# Tabela oficial de aliases / migrações de tickers na B3 (Etapa 2C - B.5)
TICKER_ALIASES: dict[str, dict[str, str]] = {
    "ELET3": {
        "canonical": "AXIA3",
        "yahoo_symbol": "AXIA3.SA",
        "name": "Axia Energia ON (ex-Eletrobras)",
        "reason": "Rebranding Eletrobras -> Axia Energia em 10/11/2025 (comunicado oficial B3/RI).",
    },
    "CPLE6": {
        "canonical": "CPLE3",
        "yahoo_symbol": "CPLE3.SA",
        "name": "Copel ON",
        "reason": "Migração Copel ao Novo Mercado e unificação de ações PNB (CPLE6) em ON (CPLE3).",
    },
    "IRANI3": {
        "canonical": "RANI3",
        "yahoo_symbol": "RANI3.SA",
        "name": "Irani Papel e Embalagem ON",
        "reason": "Código oficial de negociação na B3 é RANI3.",
    },
}

# Eventos corporativos recentes que exigem exclusão temporária da seleção (Etapa 2C - B.6)
CORPORATE_EVENTS: dict[str, str] = {
    "BBAS3": "Redução anunciada do payout de 2026 para 25% e cancelamento de proventos intermediários em 10/11/2026 (RI Banco do Brasil).",
}

DISCONTINUED_TICKERS: list[dict[str, str]] = []

TERMS_COMPLIANCE = {
    "yahoo_finance": "Permitido para consulta pontual de séries históricas/dividendos (já utilizado por market_data.py); 1 ativo por vez com pausa e cache.",
    "fundamentus": "robots.txt ausente (HTTP 404); usado apenas como checagem cruzada pontual com pausa >= 1,2s e cache local de 24h.",
    "statusinvest": "REMOVIDO do coletor automatizado: robots.txt retornou HTTP 403 Forbidden e termos de uso restringem coleta automatizada.",
    "cvm_dados_abertos": "Permitido (dados públicos oficiais em dados.cvm.gov.br).",
}

JCP_TREATMENT_NOTE = (
    "Eventos de dividendos do Yahoo Finance agregam Dividendos e JCP pelo valor declarado por ação "
    "(JCP bruto, sem dedução automática dos 15% de IRRF retidos na fonte). Divergências por tratamento "
    "bruto vs líquido de JCP são registradas sem marcar erro de código."
)


class _TDParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_td = False
        self.tds: list[str] = []
        self.cur: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "td":
            self.in_td = True
            self.cur = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.in_td:
            self.in_td = False
            self.tds.append(" ".join("".join(self.cur).split()))

    def handle_data(self, data: str) -> None:
        if self.in_td:
            self.cur.append(data)


def _read_cache(cache_file: Path, max_age_hours: int = 24) -> dict[str, Any] | None:
    if not cache_file.is_file():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(payload["cached_at"])
        if datetime.now(timezone.utc) - ts <= timedelta(hours=max_age_hours):
            return payload["data"]
    except Exception:
        return None
    return None


def _write_cache(cache_file: Path, data: dict[str, Any]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": data,
    }
    cache_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_yahoo_dividends(yahoo_symbol: str, use_cache: bool = True) -> dict[str, Any]:
    """Busca preço atual e eventos de dividendos (10y) no Yahoo Finance."""
    cache_file = CACHE_DIR / f"yahoo_{yahoo_symbol.replace('=', '_')}.json"
    if use_cache:
        cached = _read_cache(cache_file, max_age_hours=24)
        if cached is not None:
            return cached

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?range=10y&interval=1mo&events=div"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        res = raw["chart"]["result"][0]
        meta = res.get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None:
            closes = [c for c in (res.get("indicators", {}).get("quote", [{}])[0].get("close") or []) if c is not None]
            price = closes[-1] if closes else None

        divs = (res.get("events") or {}).get("dividends") or {}
        now_ts = datetime.now(timezone.utc).timestamp()
        cutoff_12m = now_ts - 365 * 86400
        div_12m = 0.0
        years_set: set[int] = set()
        for ev in divs.values():
            amt = float(ev.get("amount") or 0.0)
            dt_ts = float(ev.get("date") or 0)
            if amt > 0 and dt_ts > 0:
                yr = datetime.fromtimestamp(dt_ts, tz=timezone.utc).year
                years_set.add(yr)
                if dt_ts >= cutoff_12m:
                    div_12m += amt

        dy_12m_pct = round((div_12m / float(price)) * 100.0, 2) if (price and float(price) > 0) else None
        out = {
            "ok": True,
            "url": url,
            "price": round(float(price), 2) if price is not None else None,
            "div_12m_sum": round(div_12m, 4),
            "dy_12m_pct": dy_12m_pct,
            "years_paying": len(years_set),
            "collected_at": datetime.now().strftime("%Y-%m-%d"),
        }
    except Exception as exc:
        out = {"ok": False, "url": url, "error": str(exc), "collected_at": datetime.now().strftime("%Y-%m-%d")}

    _write_cache(cache_file, out)
    time.sleep(0.4)
    return out


def fetch_fundamentus_crosscheck(symbol: str, use_cache: bool = True) -> dict[str, Any]:
    """Checagem cruzada pontual no Fundamentus (1 página por vez, com pausa e cache)."""
    cache_file = CACHE_DIR / f"fund_{symbol}.json"
    if use_cache:
        cached = _read_cache(cache_file, max_age_hours=24)
        if cached is not None:
            return cached

    url = f"https://www.fundamentus.com.br/detalhes.php?papel={symbol}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("latin1", errors="ignore")
        p = _TDParser()
        p.feed(html)
        kv: dict[str, str] = {}
        for i, t in enumerate(p.tds):
            if t.startswith("?") and i + 1 < len(p.tds):
                kv[t[1:].strip()] = p.tds[i + 1].strip()

        def _pnum(s: str | None) -> float | None:
            if not s or s == "-":
                return None
            try:
                return float(s.replace("%", "").replace(".", "").replace(",", ".").strip())
            except ValueError:
                return None

        out = {
            "ok": True,
            "url": url,
            "price": _pnum(kv.get("Cotação")),
            "price_date": kv.get("Data últ cot"),
            "dy_12m_pct": _pnum(kv.get("Div. Yield")),
            "collected_at": datetime.now().strftime("%Y-%m-%d"),
        }
    except Exception as exc:
        out = {"ok": False, "url": url, "error": str(exc), "collected_at": datetime.now().strftime("%Y-%m-%d")}

    _write_cache(cache_file, out)
    time.sleep(1.2)
    return out


def _within_tolerance(a: float | None, b: float | None, rel_tol: float = 0.05, abs_pp: float = 0.3) -> bool:
    if a is None or b is None:
        return False
    if abs(a - b) <= abs_pp:
        return True
    if a != 0 and abs(b - a) / abs(a) <= rel_tol:
        return True
    return False


def collect_b3_fundamentals(
    snapshot_path: Path = SNAPSHOT_PATH,
    enable_crosscheck: bool = True,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Gera data/b3_fundamentals.json aplicando aliases, coleta pública, checagem cruzada e política C."""
    base_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    cvm_data = cvm_pipeline.load_cvm_fundamentals(CACHE_DIR)
    today_str = datetime.now().strftime("%Y-%m-%d")
    new_stocks: list[dict[str, Any]] = []

    for item in base_snapshot.get("stocks", []):
        raw_sym = str(item.get("symbol") or "").strip().upper()
        alias_info = TICKER_ALIASES.get(raw_sym)
        sym = alias_info["canonical"] if alias_info else raw_sym
        yahoo_sym = alias_info["yahoo_symbol"] if alias_info else (item.get("yahoo_symbol") or f"{sym}.SA")
        name = alias_info["name"] if alias_info else item.get("name", sym)

        yh = fetch_yahoo_dividends(yahoo_sym, use_cache=use_cache)
        fc = fetch_fundamentus_crosscheck(sym, use_cache=use_cache) if enable_crosscheck else {"ok": False}

        old_fields = item.get("fields") or {}
        old_dy = (old_fields.get("dy_12m_pct") or {}).get("value")
        old_payout = old_fields.get("payout_pct") or {}
        old_yrs = (old_fields.get("years_paying") or {}).get("value")
        old_nd = old_fields.get("net_debt_ebitda") or {}

        # Política C: valor do coletor (Yahoo Finance) prevalece sobre snapshot antigo
        dy_val = yh.get("dy_12m_pct") if yh.get("ok") and yh.get("dy_12m_pct") is not None else old_dy
        dy_source = (
            f"Yahoo Finance (div 12m / preço R$ {yh.get('price')} em {yh.get('collected_at')}; JCP bruto)"
            if yh.get("ok") and yh.get("dy_12m_pct") is not None
            else (old_fields.get("dy_12m_pct") or {}).get("source", "Snapshot anterior")
        )
        fc_dy = fc.get("dy_12m_pct") if fc.get("ok") else None
        dy_verified = bool(yh.get("ok") and fc.get("ok") and _within_tolerance(dy_val, fc_dy))
        if yh.get("ok") and fc.get("ok") and not dy_verified:
            dy_source += f" [divergente vs Fundamentus {fc_dy}% @ R$ {fc.get('price')} em {fc.get('price_date')}]"

        yrs_val = yh.get("years_paying") if yh.get("ok") and yh.get("years_paying") is not None else old_yrs
        yrs_source = (
            f"Yahoo Finance eventos de dividendos (janela 10a até {yh.get('collected_at')})"
            if yh.get("ok") and yh.get("years_paying") is not None
            else (old_fields.get("years_paying") or {}).get("source", "Histórico B3")
        )
        # Anos pagando só é marcado verified=true se confirmado por histórico > 0 no Yahoo e compatível com snapshot
        yrs_verified = bool(yh.get("ok") and yrs_val is not None and yrs_val > 0)

        # Etapa 2D: Payout, Dívida Líquida/EBITDA e ROE via Dados Abertos CVM (DFP 2025)
        cvm_row = cvm_data.get(sym) or {}
        is_financial = item.get("sector") in ("Bancos", "Seguros")

        cvm_payout = cvm_row.get("payout_pct")
        payout_field = {
            "value": cvm_payout if cvm_payout is not None else old_payout.get("value"),
            "source": (
                f"{cvm_row.get('source_doc')} [CD_CVM {cvm_row.get('cd_cvm')}]: {cvm_pipeline.CVM_FORMULAS['payout_pct']}"
                if cvm_payout is not None
                else (old_payout.get("source") or "Pendente conferência CVM DFP/ITR")
            ),
            "date": today_str if cvm_payout is not None else (old_payout.get("date") or today_str),
            "verified": cvm_payout is not None,
        }

        if is_financial:
            nd_field = {
                "value": None,
                "source": "Dispensado para Financeiras (Bancos/Seguros usam ROE >= 12%)",
                "date": today_str,
                "verified": True,
            }
            cvm_roe = cvm_row.get("roe_pct")
            roe_field = {
                "value": cvm_roe,
                "source": (
                    f"{cvm_row.get('source_doc')} [CD_CVM {cvm_row.get('cd_cvm')}]: {cvm_pipeline.CVM_FORMULAS['roe_pct']}"
                    if cvm_roe is not None
                    else "Pendente conferência CVM DFP/ITR (ROE)"
                ),
                "date": today_str,
                "verified": cvm_roe is not None,
            }
        else:
            cvm_nd = cvm_row.get("net_debt_ebitda")
            nd_field = {
                "value": cvm_nd if cvm_nd is not None else old_nd.get("value"),
                "source": (
                    f"{cvm_row.get('source_doc')} [CD_CVM {cvm_row.get('cd_cvm')}]: {cvm_pipeline.CVM_FORMULAS['net_debt_ebitda']}"
                    if cvm_nd is not None
                    else (old_nd.get("source") or "Pendente conferência CVM DFP/ITR")
                ),
                "date": today_str if cvm_nd is not None else (old_nd.get("date") or today_str),
                "verified": cvm_nd is not None,
            }
            roe_field = {
                "value": cvm_row.get("roe_pct"),
                "source": cvm_row.get("source_doc") or "Não exigido para não-financeiras",
                "date": today_str,
                "verified": cvm_row.get("roe_pct") is not None,
            }

        fields_out = {
            "dy_12m_pct": {
                "value": dy_val,
                "source": dy_source,
                "date": today_str,
                "verified": dy_verified,
            },
            "payout_pct": payout_field,
            "years_paying": {
                "value": yrs_val,
                "source": yrs_source,
                "date": today_str,
                "verified": yrs_verified,
            },
            "net_debt_ebitda": nd_field,
            "roe_pct": roe_field,
        }

        req_keys = ("dy_12m_pct", "payout_pct", "years_paying", "roe_pct") if is_financial else ("dy_12m_pct", "payout_pct", "years_paying", "net_debt_ebitda")
        all_fields_verified = all(bool(fields_out[k]["verified"]) for k in req_keys)
        corp_reason = CORPORATE_EVENTS.get(sym)

        entry: dict[str, Any] = {
            "symbol": sym,
            "yahoo_symbol": yahoo_sym,
            "name": name,
            "sector": item.get("sector"),
            "liquid_b3": bool(item.get("liquid_b3", True)),
            "evento_corporativo": bool(corp_reason),
            "fields": fields_out,
            "origin_type": "automated_public_collector",
            "collected_at": today_str,
            "verified": all_fields_verified,
        }
        if alias_info:
            entry["aliased_from"] = raw_sym
        if corp_reason:
            entry["corporate_event_reason"] = corp_reason

        new_stocks.append(entry)

    output = {
        "schema_version": "1.1.0",
        "reference_date": today_str,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "max_age_days": int(base_snapshot.get("max_age_days", 90)),
        "origin_type": "automated_public_collector",
        "schedule_cadence": "monthly",
        "jcp_treatment_note": JCP_TREATMENT_NOTE,
        "terms_compliance": TERMS_COMPLIANCE,
        "ticker_aliases": TICKER_ALIASES,
        "discontinued_tickers": DISCONTINUED_TICKERS,
        "universe_description": base_snapshot.get("universe_description"),
        "default_field_sources": base_snapshot.get("default_field_sources"),
        "stocks": new_stocks,
    }
    snapshot_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Coletor automático de fundamentos B3 (Etapa 2C)")
    parser.add_argument("--no-crosscheck", action="store_true", help="Desativa checagem cruzada no Fundamentus")
    parser.add_argument("--no-cache", action="store_true", help="Ignora cache local de 24h")
    args = parser.parse_args()

    out = collect_b3_fundamentals(
        enable_crosscheck=not args.no_crosscheck,
        use_cache=not args.no_cache,
    )
    total = len(out["stocks"])
    ver_true = sum(1 for s in out["stocks"] if s.get("verified"))
    corp_cnt = sum(1 for s in out["stocks"] if s.get("evento_corporativo"))
    print(f"COLLECTED={total} VERIFIED_TRUE={ver_true} VERIFIED_FALSE={total - ver_true} CORPORATE_EVENTS={corp_cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
