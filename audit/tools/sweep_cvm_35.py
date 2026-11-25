"""Varredura CVM dos 35 ativos: LTM vs DFP 2025, elegíveis Dividendos e eventos corporativos."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cvm_pipeline


def _ni(d: dict[str, float]) -> float | None:
    v = d.get("3.11")
    return v if v is not None else d.get("3.09")


def main():
    snap = json.loads((BASE_DIR / "data" / "b3_fundamentals.json").read_text(encoding="utf-8"))
    assets = {s["symbol"]: s for s in snap.get("stocks", []) if isinstance(s, dict) and s.get("symbol")}
    cache_dir = BASE_DIR / "data" / "cvm_cache"
    cvm_data = cvm_pipeline.load_cvm_fundamentals(cache_dir)

    # Também calcula DFP 2025 puro para comparar LTM vs DFP 2025 nos 35 ativos
    target_cvms = set(cvm_pipeline.B3_TO_CD_CVM.values())
    with zipfile.ZipFile(cache_dir / "dfp_cia_aberta_2025.zip") as z:
        dre25 = cvm_pipeline._merge_con_ind(
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_DRE_con_2025.csv", target_cvms)[0],
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_DRE_ind_2025.csv", target_cvms)[0],
        )
        dva25 = cvm_pipeline._merge_con_ind(
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_DVA_con_2025.csv", target_cvms)[0],
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_DVA_ind_2025.csv", target_cvms)[0],
        )
        bpa25 = cvm_pipeline._merge_con_ind(
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_BPA_con_2025.csv", target_cvms, is_flow=False)[0],
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_BPA_ind_2025.csv", target_cvms, is_flow=False)[0],
        )
        bpp25 = cvm_pipeline._merge_con_ind(
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_BPP_con_2025.csv", target_cvms, is_flow=False)[0],
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_BPP_ind_2025.csv", target_cvms, is_flow=False)[0],
        )
        dfc25 = cvm_pipeline._merge_con_ind(
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_DFC_MI_con_2025.csv", target_cvms)[0],
            cvm_pipeline._parse_cvm_csv(z, "dfp_cia_aberta_DFC_MI_ind_2025.csv", target_cvms)[0],
        )

    print(f"Total ativos no snapshot: {len(assets)} | CVM carregados: {len(cvm_data)}")
    print("\n=== COMPARAÇÃO LTM (CVM) vs DFP 2025 (> 30 pp em payout/roe ou > 1.0x em div/ebitda) ===")
    for sym, a in sorted(assets.items()):
        cvm = cvm_pipeline.B3_TO_CD_CVM.get(sym)
        c = cvm_data.get(sym, {})
        ltm_p = c.get("payout_pct")
        ltm_r = c.get("roe_pct")
        ltm_d = c.get("net_debt_ebitda")

        d25 = dre25.get(cvm, {})
        ni25 = _ni(d25)
        div25 = cvm_pipeline._extract_div_from_dva(dva25.get(cvm, {}))
        if div25 <= 0:
            div25 = dfc25.get(cvm, {}).get("__DFC_DIV__", 0.0)
        dfp_p = round((div25 / ni25) * 100.0, 2) if (div25 > 0 and ni25 and ni25 > 0) else None
        pl25 = bpp25.get(cvm, {}).get("__PL__") or bpp25.get(cvm, {}).get("2.03")
        dfp_r = round((ni25 / pl25) * 100.0, 2) if (ni25 is not None and pl25 and pl25 > 0) else None

        ebit25 = d25.get("3.05")
        da25 = dfc25.get(cvm, {}).get("__DA__", 0.0)
        bpa_c = bpa25.get(cvm, {})
        bpp_c = bpp25.get(cvm, {})
        dfp_d = None
        if ebit25 is not None and "1.01.01" in bpa_c and ("2.01.04" in bpp_c or "2.02.01" in bpp_c):
            cash25 = bpa_c.get("1.01.01", 0.0) + bpa_c.get("1.01.02", 0.0)
            debt25 = bpp_c.get("2.01.04", 0.0) + bpp_c.get("2.02.01", 0.0)
            ebitda25 = ebit25 + da25
            if ebitda25 > 0:
                dfp_d = round((debt25 - cash25) / ebitda25, 2)

        dp = (ltm_p - dfp_p) if (ltm_p is not None and dfp_p is not None) else None
        dr = (ltm_r - dfp_r) if (ltm_r is not None and dfp_r is not None) else None
        dd = (ltm_d - dfp_d) if (ltm_d is not None and dfp_d is not None) else None
        flag = (
            (dp is not None and abs(dp) > 30.0)
            or (dr is not None and abs(dr) > 30.0)
            or (dd is not None and abs(dd) > 1.0)
            or (ltm_p is None and dfp_p is not None)
            or (ltm_p is not None and dfp_p is None)
        )
        if flag:
            print(
                f"{sym:<7} | payout LTM={ltm_p} vs DFP25={dfp_p} (diff={None if dp is None else round(dp,1)})"
                f" | roe LTM={ltm_r} vs DFP25={dfp_r} (diff={None if dr is None else round(dr,1)})"
                f" | nd/eb LTM={ltm_d} vs DFP25={dfp_d}"
            )

    print("\n=== 9 ATIVOS ELEGÍVEIS DIVIDENDOS ===")
    elig = ["ABCB4", "CMIG4", "LEVE3", "VIVT3", "PSSA3", "CPLE3", "CXSE3", "TIMS3", "B3SA3"]
    for sym in elig:
        a = assets[sym]
        f = a["fields"]
        print(
            f"{sym:<6} | {a.get('sector'):<11} | DY={f['dy_12m_pct']['value']} ({f['dy_12m_pct']['source']}) [v={f['dy_12m_pct']['verified']}]"
            f" | Payout={f['payout_pct']['value']} ({f['payout_pct']['source']}) [v={f['payout_pct']['verified']}]"
            f" | ROE={f['roe_pct']['value']} [v={f['roe_pct']['verified']}]"
            f" | ND/EB={f['net_debt_ebitda']['value']} [v={f['net_debt_ebitda']['verified']}]"
            f" | base={a.get('data_base_cvm')}"
        )

    print("\n=== ATIVOS COM evento_corporativo=true ===")
    cnt = 0
    for sym, a in sorted(assets.items()):
        if a.get("evento_corporativo"):
            cnt += 1
            print(f"{cnt:2d}. {sym:<7} | {a.get('corporate_event_reason')}")


if __name__ == "__main__":
    main()
