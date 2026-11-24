"""Executa backtests reais e Radar Global com dados públicos (Etapa 2C - Item D).
Gera relatório em audit/reports/backtest_evidence_YYYY-MM-DD.md.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
VENV_SITE = BASE_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE.is_dir() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import global_radar  # noqa: E402
import market_data  # noqa: E402
import strategies_engine  # noqa: E402


PRICE_STRATEGIES = [
    "indexacao_bogle",
    "trend_following_turtles",
    "dual_momentum_global",
    "risk_parity_simplified",
    "radar_top_n",
]


def main() -> int:
    lines: list[str] = [
        f"# Evidência Real de Backtests e Radar Global — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Backtests Reais (Estratégias Baseadas em Preço)",
        "",
    ]

    summaries: dict[str, dict] = {}
    for sid in PRICE_STRATEGIES:
        res = strategies_engine.run_strategy(sid, persist=False)
        bt = res.get("backtest") or {}
        avail = bt.get("available")
        metrics = bt.get("metrics") or {}
        bms = bt.get("benchmarks") or {}
        curve = bt.get("curve") or []
        summaries[sid] = {
            "available": avail,
            "start_date": bt.get("start_date"),
            "end_date": bt.get("end_date"),
            "bars": len(curve),
            "limiting_asset": bt.get("limiting_asset"),
            "metrics": metrics,
            "brokerage_bps": bt.get("brokerage_bps"),
            "slippage_bps": bt.get("slippage_bps"),
            "benchmarks": {
                k: {
                    "label": v.get("label"),
                    "total_return_pct": (v.get("metrics") or {}).get("total_return_pct"),
                    "return_type": v.get("return_type"),
                }
                for k, v in bms.items()
            },
        }
        lines.append(f"### `{sid}`")
        if not avail:
            lines.append(f"- **Status:** `indisponível` ({bt.get('reason') or res.get('alerts')})")
            lines.append("")
            continue
        lines.append(f"- **Janela:** `{bt.get('start_date')}` a `{bt.get('end_date')}` ({len(curve)} barras)")
        lines.append(f"- **Ativo limitante:** `{bt.get('limiting_asset')}`")
        lines.append(
            f"- **Métricas:** Retorno Total `{metrics.get('total_return_pct')}%` | "
            f"Volatilidade `{metrics.get('volatility_ann_pct')}%` | "
            f"Drawdown Máx `{metrics.get('max_drawdown_pct')}%` | "
            f"Sharpe vs CDI `{metrics.get('sharpe_vs_cdi')}`"
        )
        lines.append(
            f"- **Custos aplicados:** corretagem `{bt.get('brokerage_bps')} bps`, "
            f"slippage `{bt.get('slippage_bps')} bps`, execução `t+1`"
        )
        sharpe = metrics.get("sharpe_vs_cdi")
        dd = metrics.get("max_drawdown_pct")
        plaus_flags = []
        if isinstance(sharpe, (int, float)) and sharpe > 2.5:
            plaus_flags.append(f"Sharpe elevado ({sharpe} > 2.5)")
        if isinstance(dd, (int, float)) and dd == 0.0:
            plaus_flags.append("Drawdown zero")
        lines.append(
            f"- **Plausibilidade (D.3):** `{'ALERTA: ' + '; '.join(plaus_flags) if plaus_flags else 'OK (sem anomalias de look-ahead ou curva sem drawdown)'}`"
        )
        lines.append("- **Comparação com Benchmarks:**")
        for bkey, bval in bms.items():
            bm_ret = (bval.get("metrics") or {}).get("total_return_pct")
            lines.append(
                f"  - `{bkey}` ({bval.get('label')}, `{bval.get('return_type')}`): `{bm_ret}%`"
            )
        lines.append("")

    # Radar Global (D.4)
    lines.append("## 2. Radar Global com Dados Reais (D.4)")
    lines.append("")
    radar = global_radar.scan_global_opportunities()
    regime = radar.get("regime") or {}
    sigs = regime.get("signals") or []
    lines.append(
        f"- **Regime atual:** `{regime.get('regime')}` — `{regime.get('availability_label')}` "
        f"(Risk-On: `{regime.get('risk_on_count')}`, Risk-Off: `{regime.get('risk_off_count')}`)"
    )
    for sinfo in sigs:
        lines.append(
            f"  - `{sinfo.get('name')}`: valor=`{sinfo.get('value')} {sinfo.get('unit', '')}`, "
            f"sinal=`{sinfo.get('signal')}`, regra=`{sinfo.get('rule')}`"
        )

    # Teste de unidades ^TNX e ^IRX diretamente via market_data
    tnx = market_data.get_strict_daily_candles("^TNX", limit=30, allow_fallback=False)
    irx = market_data.get_strict_daily_candles("^IRX", limit=30, allow_fallback=False)
    tnx_px = tnx.get("last_price")
    irx_px = irx.get("last_price")
    spread_pp = round(float(tnx_px) - float(irx_px), 2) if isinstance(tnx_px, (int, float)) and isinstance(irx_px, (int, float)) else "indisponível"
    units_ok = isinstance(tnx_px, (int, float)) and 0.5 <= float(tnx_px) <= 15.0 and isinstance(irx_px, (int, float)) and 0.0 <= float(irx_px) <= 15.0
    lines.append(
        f"- **Teste de unidades ^TNX e ^IRX:** `^TNX={tnx_px}% a.a.`, `^IRX={irx_px}% a.a.`, "
        f"`spread={spread_pp} pp` -> `{'PASS (valores em % a.a., não em pontos-base x10)' if units_ok else 'FAIL/INDISPONÍVEL'}`"
    )

    lines.append("")
    lines.append("### Top 5 Candidatos (A FAVOR e CONTRA)")
    top5 = (radar.get("candidates") or [])[:5]
    for cand in top5:
        lines.append(
            f"- **{cand.get('symbol')}** ({cand.get('name')} | {cand.get('asset_class')} | "
            f"Score heurístico: `{cand.get('score')}`):"
        )
        for pro in cand.get("a_favor", []):
            lines.append(f"  - A FAVOR: {pro}")
        for con in cand.get("contra", []):
            lines.append(f"  - CONTRA: {con}")

    corr = radar.get("correlation_matrix") or {}
    corr_win = radar.get("correlation_window_days")
    corr_syms = corr.get("symbols") or list((corr.get("matrix") or {}).keys())
    high_pairs = corr.get("high_correlation_pairs") or []
    lines.append("")
    lines.append("### Resumo da Matriz de Correlação")
    lines.append(
        f"- **Janela:** `{corr_win}` pregões | **Ativos:** `{len(corr_syms)}` | "
        f"**Pares com |corr| >= 0.75:** `{len(high_pairs)}`"
    )
    for hp in high_pairs[:10]:
        lines.append(f"  - `{hp.get('pair') or (str(hp.get('a')) + ' x ' + str(hp.get('b')))}`: `{hp.get('correlation')}`")

    out_dir = BASE_DIR / "audit" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / f"backtest_evidence_{datetime.now().strftime('%Y-%m-%d')}.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cache_json = BASE_DIR / "data" / "collector_cache" / "last_backtest_evidence.json"
    cache_json.parent.mkdir(parents=True, exist_ok=True)
    cache_json.write_text(json.dumps({"summaries": summaries, "regime": regime}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"EVIDENCE_REPORT={out_md}")
    print(f"RADAR regime={regime.get('regime')} {regime.get('availability_label')} top5={[c.get('symbol') for c in top5]} TNX={tnx_px} IRX={irx_px}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
