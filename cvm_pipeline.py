"""Pipeline de Dados Abertos da CVM (LTM: DFP 2025 + ITR 9M26) para Payout, Dívida Líquida/EBITDA e ROE.

Regras (Etapa 2E - C):
- Dado ausente nunca vira zero: conta ausente ou sem distribuição positiva = None ('indisponível').
- Usa demonstrações consolidadas (_con_) com fallback para individuais (_ind_) quando a cia não consolida (ex.: ABCB4, SAPR11).
- Payout: DVA (7.08.04 / 7.09.04 / 7.11.04) com fallback para DFC financiamento (6.03.* Dividendos/JCP pagos) quando DVA vier zerada.
- LTM: DFP_2025 - ITR_9M25 + ITR_9M26 para fluxos (DRE, DVA, DFC); saldo mais recente (ITR 3T26 ou DFP 2025) para balanço (BPA, BPP).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any
import urllib.request
import zipfile

CVM_DFP_2025_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip"
CVM_ITR_2026_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_2026.zip"

B3_TO_CD_CVM: dict[str, str] = {
    "BBAS3": "001023",
    "ITUB4": "019348",
    "SANB11": "020532",
    "BBDC4": "000906",
    "ABCB4": "020958",
    "TAEE11": "020257",
    "EGIE3": "017329",
    "CPFE3": "018660",
    "CMIG4": "002453",
    "ISAE4": "018376",
    "CPLE3": "014311",
    "AXIA3": "002437",
    "AURE3": "026620",
    "BBSE3": "023159",
    "CXSE3": "023795",
    "PSSA3": "016659",
    "SAPR11": "018627",
    "CSMG3": "019445",
    "SBSP3": "014443",
    "VIVT3": "017671",
    "TIMS3": "024929",
    "PETR4": "009512",
    "PRIO3": "022187",
    "VALE3": "004170",
    "CMIN3": "025585",
    "GGBR4": "003980",
    "KLBN11": "012653",
    "SUZB3": "013986",
    "RANI3": "002429",
    "WEGE3": "005410",
    "LEVE3": "008575",
    "ABEV3": "023264",
    "B3SA3": "021610",
    "RADL3": "005258",
    "CSAN3": "019836",
}

CVM_FORMULAS = {
    "payout_pct": "LTM (DFP25 - 9M25 + 9M26): (Dividendos + JCP via DVA 7.08/7.09/7.11 ou DFC 6.03.*) / Lucro Líquido (DRE 3.11) * 100",
    "net_debt_ebitda": "(BPP 2.01.04 + BPP 2.02.01 - BPA 1.01.01 - BPA 1.01.02 em 3T26) / (EBIT LTM DRE 3.05 + D&A LTM DFC)",
    "roe_pct": "Lucro Líquido LTM (DRE 3.11) / Patrimônio Líquido (BPP 2.03 em 3T26) * 100 (Bancos e Seguros)",
}

_DVA_DIV_ACCOUNTS = ("7.08.04.01", "7.08.04.02", "7.09.04.01", "7.09.04.02", "7.11.04.01", "7.11.04.02")


def _ensure_zip(cache_dir: Path, filename: str, url: str) -> Path | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    zp = cache_dir / filename
    if zp.is_file() and zp.stat().st_size > 500_000:
        return zp
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HeuristikaQuant/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            zp.write_bytes(resp.read())
        return zp
    except Exception:
        return None


def _parse_cvm_csv(
    z: zipfile.ZipFile,
    filename: str,
    target_cvms: set[str],
    is_itr: bool = False,
    is_flow: bool = True,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Retorna (ultimo, penultimo) por CD_CVM. Para ITR de fluxo, filtra acumulado 9M (01-01 a 09-30)."""
    cur: dict[str, dict[str, float]] = {}
    prev: dict[str, dict[str, float]] = {}
    if filename not in z.namelist():
        return cur, prev
    with z.open(filename) as f:
        r = csv.DictReader(io.TextIOWrapper(f, encoding="latin1"), delimiter=";")
        for row in r:
            cvm = row.get("CD_CVM", "")
            if cvm not in target_cvms:
                continue
            if is_itr and is_flow:
                dt_ini = row.get("DT_INI_EXERC", "")
                dt_fim = row.get("DT_FIM_EXERC", "")
                if not (dt_ini.endswith("-01-01") and dt_fim.endswith("-09-30")):
                    continue
            ordem = row.get("ORDEM_EXERC", "")
            if ordem not in ("ÚLTIMO", "PENÚLTIMO"):
                continue
            try:
                val = float(row.get("VL_CONTA") or 0.0)
            except ValueError:
                continue
            dest = cur if ordem == "ÚLTIMO" else prev
            bucket = dest.setdefault(cvm, {})
            conta = row.get("CD_CONTA", "")
            bucket[conta] = val

            ds = (row.get("DS_CONTA") or "").upper()
            if "DFC" in filename:
                if ("DEPREC" in ds or "AMORT" in ds) and val != 0.0:
                    bucket["__DA__"] = bucket.get("__DA__", 0.0) + abs(val)
                if conta.startswith("6.03") and val < 0 and any(k in ds for k in ("DIVID", "JCP", "JUROS SOBRE")):
                    if "RECEB" not in ds:
                        bucket["__DFC_DIV__"] = bucket.get("__DFC_DIV__", 0.0) + abs(val)
    return cur, prev


def _merge_con_ind(con_map: dict[str, dict[str, float]], ind_map: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    merged = dict(ind_map)
    merged.update(con_map)
    return merged


def _extract_div_from_dva(dva_dict: dict[str, float]) -> float:
    return sum(abs(dva_dict.get(code, 0.0)) for code in _DVA_DIV_ACCOUNTS)


def load_cvm_fundamentals(cache_dir: Path) -> dict[str, dict[str, Any]]:
    """Extrai Payout, Dívida Líquida/EBITDA e ROE da CVM (LTM: DFP 2025 + ITR 9M26) por ticker B3."""
    zp_dfp = _ensure_zip(cache_dir, "dfp_cia_aberta_2025.zip", CVM_DFP_2025_URL)
    if zp_dfp is None:
        return {}
    zp_itr = _ensure_zip(cache_dir, "itr_cia_aberta_2026.zip", CVM_ITR_2026_URL)

    target_cvms = set(B3_TO_CD_CVM.values())
    with zipfile.ZipFile(zp_dfp) as z:
        dre25 = _merge_con_ind(
            _parse_cvm_csv(z, "dfp_cia_aberta_DRE_con_2025.csv", target_cvms)[0],
            _parse_cvm_csv(z, "dfp_cia_aberta_DRE_ind_2025.csv", target_cvms)[0],
        )
        dva25 = _merge_con_ind(
            _parse_cvm_csv(z, "dfp_cia_aberta_DVA_con_2025.csv", target_cvms)[0],
            _parse_cvm_csv(z, "dfp_cia_aberta_DVA_ind_2025.csv", target_cvms)[0],
        )
        bpa25 = _merge_con_ind(
            _parse_cvm_csv(z, "dfp_cia_aberta_BPA_con_2025.csv", target_cvms, is_flow=False)[0],
            _parse_cvm_csv(z, "dfp_cia_aberta_BPA_ind_2025.csv", target_cvms, is_flow=False)[0],
        )
        bpp25 = _merge_con_ind(
            _parse_cvm_csv(z, "dfp_cia_aberta_BPP_con_2025.csv", target_cvms, is_flow=False)[0],
            _parse_cvm_csv(z, "dfp_cia_aberta_BPP_ind_2025.csv", target_cvms, is_flow=False)[0],
        )
        dfc25 = _merge_con_ind(
            _parse_cvm_csv(z, "dfp_cia_aberta_DFC_MI_con_2025.csv", target_cvms)[0],
            _parse_cvm_csv(z, "dfp_cia_aberta_DFC_MI_ind_2025.csv", target_cvms)[0],
        )

    dre9m26: dict[str, dict[str, float]] = {}
    dre9m25: dict[str, dict[str, float]] = {}
    dva9m26: dict[str, dict[str, float]] = {}
    dva9m25: dict[str, dict[str, float]] = {}
    dfc9m26: dict[str, dict[str, float]] = {}
    dfc9m25: dict[str, dict[str, float]] = {}
    bpa3t26: dict[str, dict[str, float]] = {}
    bpp3t26: dict[str, dict[str, float]] = {}

    if zp_itr is not None:
        with zipfile.ZipFile(zp_itr) as z:
            c1, p1 = _parse_cvm_csv(z, "itr_cia_aberta_DRE_con_2026.csv", target_cvms, is_itr=True, is_flow=True)
            c2, p2 = _parse_cvm_csv(z, "itr_cia_aberta_DRE_ind_2026.csv", target_cvms, is_itr=True, is_flow=True)
            dre9m26, dre9m25 = _merge_con_ind(c1, c2), _merge_con_ind(p1, p2)

            c1, p1 = _parse_cvm_csv(z, "itr_cia_aberta_DVA_con_2026.csv", target_cvms, is_itr=True, is_flow=True)
            c2, p2 = _parse_cvm_csv(z, "itr_cia_aberta_DVA_ind_2026.csv", target_cvms, is_itr=True, is_flow=True)
            dva9m26, dva9m25 = _merge_con_ind(c1, c2), _merge_con_ind(p1, p2)

            c1, p1 = _parse_cvm_csv(z, "itr_cia_aberta_DFC_MI_con_2026.csv", target_cvms, is_itr=True, is_flow=True)
            c2, p2 = _parse_cvm_csv(z, "itr_cia_aberta_DFC_MI_ind_2026.csv", target_cvms, is_itr=True, is_flow=True)
            dfc9m26, dfc9m25 = _merge_con_ind(c1, c2), _merge_con_ind(p1, p2)

            bpa3t26 = _merge_con_ind(
                _parse_cvm_csv(z, "itr_cia_aberta_BPA_con_2026.csv", target_cvms, is_itr=True, is_flow=False)[0],
                _parse_cvm_csv(z, "itr_cia_aberta_BPA_ind_2026.csv", target_cvms, is_itr=True, is_flow=False)[0],
            )
            bpp3t26 = _merge_con_ind(
                _parse_cvm_csv(z, "itr_cia_aberta_BPP_con_2026.csv", target_cvms, is_itr=True, is_flow=False)[0],
                _parse_cvm_csv(z, "itr_cia_aberta_BPP_ind_2026.csv", target_cvms, is_itr=True, is_flow=False)[0],
            )

    results: dict[str, dict[str, Any]] = {}
    for sym, cvm in B3_TO_CD_CVM.items():
        d25 = dre25.get(cvm, {})
        has_ltm = cvm in dre9m26 and cvm in dre9m25

        def _ni(d: dict[str, float]) -> float | None:
            v = d.get("3.11")
            return v if v is not None else d.get("3.09")

        ni25 = _ni(d25)
        if has_ltm and ni25 is not None and _ni(dre9m26[cvm]) is not None and _ni(dre9m25[cvm]) is not None:
            net_inc = ni25 - _ni(dre9m25[cvm]) + _ni(dre9m26[cvm])  # type: ignore[operator]
            data_base = "2026-09-30"
            source_doc = "CVM LTM (DFP 2025 + ITR 9M26)"
        else:
            net_inc = ni25
            data_base = "2025-12-31"
            source_doc = "CVM DFP 2025"

        # Proventos: tenta DVA, se zerado/ausente cai para DFC 6.03.* (Regra C.1/C.3: nunca retorna 0.0 se ausente)
        div_dva25 = _extract_div_from_dva(dva25.get(cvm, {}))
        if has_ltm:
            div_dva = max(0.0, div_dva25 - _extract_div_from_dva(dva9m25.get(cvm, {})) + _extract_div_from_dva(dva9m26.get(cvm, {})))
        else:
            div_dva = div_dva25

        div_method = "DVA"
        total_div = div_dva
        if total_div <= 0.0:
            dfc25_div = dfc25.get(cvm, {}).get("__DFC_DIV__", 0.0)
            if has_ltm:
                dfc_ltm = max(0.0, dfc25_div - dfc9m25.get(cvm, {}).get("__DFC_DIV__", 0.0) + dfc9m26.get(cvm, {}).get("__DFC_DIV__", 0.0))
            else:
                dfc_ltm = dfc25_div
            if dfc_ltm > 0.0:
                total_div = dfc_ltm
                div_method = "DFC (6.03.*)"

        payout = round((total_div / net_inc) * 100.0, 2) if (total_div > 0.0 and net_inc is not None and net_inc > 0.0) else None

        bpp_cur = bpp3t26.get(cvm) or bpp25.get(cvm, {})
        bpa_cur = bpa3t26.get(cvm) or bpa25.get(cvm, {})

        pl = bpp_cur.get("2.03")
        roe = round((net_inc / pl) * 100.0, 2) if (net_inc is not None and pl is not None and pl > 0.0) else None

        has_cash = "1.01.01" in bpa_cur
        has_debt = "2.01.04" in bpp_cur or "2.02.01" in bpp_cur
        ebit25 = d25.get("3.05")
        if has_ltm and ebit25 is not None and "3.05" in dre9m26.get(cvm, {}) and "3.05" in dre9m25.get(cvm, {}):
            ebit = ebit25 - dre9m25[cvm]["3.05"] + dre9m26[cvm]["3.05"]
            da = max(0.0, dfc25.get(cvm, {}).get("__DA__", 0.0) - dfc9m25.get(cvm, {}).get("__DA__", 0.0) + dfc9m26.get(cvm, {}).get("__DA__", 0.0))
        else:
            ebit = ebit25
            da = dfc25.get(cvm, {}).get("__DA__", 0.0)

        nd_ebitda = None
        if ebit is not None and has_cash and has_debt:
            cash = bpa_cur.get("1.01.01", 0.0) + bpa_cur.get("1.01.02", 0.0)
            debt = bpp_cur.get("2.01.04", 0.0) + bpp_cur.get("2.02.01", 0.0)
            ebitda = ebit + da
            if ebitda > 0.0:
                nd_ebitda = round((debt - cash) / ebitda, 2)

        results[sym] = {
            "cd_cvm": cvm,
            "data_base": data_base,
            "payout_pct": payout,
            "div_method": div_method if payout is not None else "indisponível",
            "net_debt_ebitda": nd_ebitda,
            "roe_pct": roe,
            "source_doc": source_doc,
        }
    return results
