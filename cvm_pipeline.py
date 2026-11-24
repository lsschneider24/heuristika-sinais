"""Pipeline de Dados Abertos da CVM (DFP 2025) para Payout, Dívida Líquida/EBITDA e ROE."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any
import urllib.request
import zipfile

CVM_DFP_2025_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip"

# Mapeamento explícito ticker B3 -> CD_CVM (6 dígitos)
B3_TO_CD_CVM: dict[str, str] = {
    "BBAS3": "001023",
    "ITUB4": "019348",
    "SANB11": "020532",
    "BBDC4": "000906",
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
    "payout_pct": "(DVA 7.08.04.01 JCP + DVA 7.08.04.02 Dividendos) / DRE 3.11 Lucro Líquido * 100",
    "net_debt_ebitda": "(BPP 2.01.04 + BPP 2.02.01 - BPA 1.01.01 - BPA 1.01.02) / (DRE 3.05 EBIT + DFC_MI D&A)",
    "roe_pct": "DRE 3.11 Lucro Líquido / BPP 2.03 Patrimônio Líquido * 100 (aplicado a Bancos e Seguros)",
}


def _ensure_dfp_zip(cache_dir: Path) -> Path | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    zp = cache_dir / "dfp_cia_aberta_2025.zip"
    if zp.is_file() and zp.stat().st_size > 1_000_000:
        return zp
    try:
        req = urllib.request.Request(CVM_DFP_2025_URL, headers={"User-Agent": "HeuristikaQuant/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            zp.write_bytes(resp.read())
        return zp
    except Exception:
        return None


def _read_cvm_accounts(z: zipfile.ZipFile, filename: str, target_cvms: set[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if filename not in z.namelist():
        return out
    with z.open(filename) as f:
        r = csv.DictReader(io.TextIOWrapper(f, encoding="latin1"), delimiter=";")
        for row in r:
            if row.get("ORDEM_EXERC") != "ÚLTIMO":
                continue
            cvm = row.get("CD_CVM", "")
            if cvm not in target_cvms:
                continue
            conta = row.get("CD_CONTA", "")
            try:
                val = float(row.get("VL_CONTA") or 0.0)
            except ValueError:
                continue
            out.setdefault(cvm, {})[conta] = val
            # Guarda D&A pela descrição no DFC_MI
            if "DFC_MI" in filename:
                ds = (row.get("DS_CONTA") or "").upper()
                if ("DEPREC" in ds or "AMORT" in ds) and val != 0.0:
                    out[cvm]["__DA__"] = out[cvm].get("__DA__", 0.0) + abs(val)
    return out


def load_cvm_fundamentals(cache_dir: Path) -> dict[str, dict[str, Any]]:
    """Extrai Payout, Dívida Líquida/EBITDA e ROE da CVM (DFP 2025) por ticker B3."""
    zp = _ensure_dfp_zip(cache_dir)
    if zp is None:
        return {}

    target_cvms = set(B3_TO_CD_CVM.values())
    with zipfile.ZipFile(zp) as z:
        dre = _read_cvm_accounts(z, "dfp_cia_aberta_DRE_con_2025.csv", target_cvms)
        dva = _read_cvm_accounts(z, "dfp_cia_aberta_DVA_con_2025.csv", target_cvms)
        bpa = _read_cvm_accounts(z, "dfp_cia_aberta_BPA_con_2025.csv", target_cvms)
        bpp = _read_cvm_accounts(z, "dfp_cia_aberta_BPP_con_2025.csv", target_cvms)
        dfc = _read_cvm_accounts(z, "dfp_cia_aberta_DFC_MI_con_2025.csv", target_cvms)

    results: dict[str, dict[str, Any]] = {}
    for sym, cvm in B3_TO_CD_CVM.items():
        d_dre = dre.get(cvm, {})
        d_dva = dva.get(cvm, {})
        d_bpa = bpa.get(cvm, {})
        d_bpp = bpp.get(cvm, {})
        d_dfc = dfc.get(cvm, {})

        net_inc = d_dre.get("3.11")
        if net_inc is None:
            net_inc = d_dre.get("3.09")

        jcp = abs(d_dva.get("7.08.04.01", 0.0))
        divs = abs(d_dva.get("7.08.04.02", 0.0))
        has_dva = "7.08.04.01" in d_dva or "7.08.04.02" in d_dva
        payout = round(((jcp + divs) / net_inc) * 100.0, 2) if (has_dva and net_inc and net_inc > 0) else None

        pl = d_bpp.get("2.03")
        roe = round((net_inc / pl) * 100.0, 2) if (net_inc is not None and pl and pl > 0) else None

        cash = d_bpa.get("1.01.01", 0.0) + d_bpa.get("1.01.02", 0.0)
        debt = d_bpp.get("2.01.04", 0.0) + d_bpp.get("2.02.01", 0.0)
        ebit = d_dre.get("3.05")
        da = d_dfc.get("__DA__", 0.0)
        nd_ebitda = None
        if ebit is not None and ("1.01.01" in d_bpa) and ("2.01.04" in d_bpp or "2.02.01" in d_bpp):
            ebitda = ebit + da
            if ebitda > 0:
                nd_ebitda = round((debt - cash) / ebitda, 2)

        results[sym] = {
            "cd_cvm": cvm,
            "payout_pct": payout,
            "net_debt_ebitda": nd_ebitda,
            "roe_pct": roe,
            "source_doc": "CVM DFP 2025 (dados.cvm.gov.br)",
        }
    return results
