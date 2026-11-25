"""Camada do Agente do Laboratório de Estratégias (Fase 3).

- Modo determinístico como PADRÃO (zero custo, sem depender de LLM).
- Adaptador de LLM opcional e desligado por padrão (LLM_ENABLED=false), com limites
  de requisições/tokens e fallback automático para o modo determinístico.
- 12 ferramentas acopladas a strategies_engine, global_radar, market_data e database.
- Nunca calcula números de cabeça, recusa recomendação personalizada e rotula
  candidatos como 'CANDIDATO A ESTUDO' (entrada só via proposta + aprovação Admin).
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
import os
import re
import time
from typing import Any

import config
import database
import global_radar
import market_data
import strategies_engine

INDISPONIVEL = market_data.INDISPONIVEL
CANDIDATO_LABEL = "CANDIDATO A ESTUDO"

_PERSONALIZED_ADVICE_PATTERNS = (
    r"\bo que (eu )?(devo|posso|compro|comprar)\b",
    r"\bqual a[çc][ãa]o comprar\b",
    r"\bdevo comprar\b",
    r"\bdevo vender\b",
    r"\bquanto (eu )?devo investir\b",
    r"\bme recomende\b",
    r"\brecomenda[çc][ãa]o personalizada\b",
    r"\bmonte minha carteira\b",
    r"\bpara o meu perfil\b",
)


class _RateLimiter:
    """Controle de taxa (req/min e req/dia) para adaptador LLM opcional."""

    def __init__(self, max_per_min: int = 5, max_per_day: int = 50) -> None:
        self.max_per_min = max(1, int(max_per_min))
        self.max_per_day = max(1, int(max_per_day))
        self._minute_hits: deque[float] = deque()
        self._day_key: str = datetime.now().strftime("%Y-%m-%d")
        self._day_count: int = 0

    def allow(self) -> tuple[bool, str]:
        now = time.time()
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._day_key:
            self._day_key = today
            self._day_count = 0
        while self._minute_hits and now - self._minute_hits[0] > 60.0:
            self._minute_hits.popleft()
        if len(self._minute_hits) >= self.max_per_min:
            return False, "limite por minuto atingido"
        if self._day_count >= self.max_per_day:
            return False, "limite diário atingido"
        self._minute_hits.append(now)
        self._day_count += 1
        return True, "ok"


class OptionalLLMAdapter:
    """Adaptador abstrato opcional de LLM (desligado por padrão; chave só no servidor)."""

    def __init__(self, llm_cfg: dict[str, Any] | None = None) -> None:
        cfg = llm_cfg or {}
        self.enabled = bool(getattr(config, "LLM_ENABLED", False)) and bool(cfg.get("enabled_default", False) or os.getenv("LLM_ENABLED", "").lower() in ("1", "true", "yes"))
        self.provider = str(cfg.get("provider") or "gemini_free")
        self.max_tokens = int(cfg.get("max_tokens_per_response", 450))
        self.limiter = _RateLimiter(
            max_per_min=int(cfg.get("max_requests_per_minute", 5)),
            max_per_day=int(cfg.get("max_requests_per_day", 50)),
        )

    def summarize(self, deterministic_text: str, user_query: str) -> tuple[str, str]:
        """Retorna (texto_final, modo). Faz fallback automático para determinístico em qualquer falha."""
        if not self.enabled:
            return deterministic_text, "deterministic"
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return deterministic_text, "deterministic"
        allowed, _ = self.limiter.allow()
        if not allowed:
            return deterministic_text, "deterministic"
        # Por segurança e custo zero, mantém saída determinística validada sem alterar números
        return deterministic_text, "deterministic"


class StrategyAgent:
    """Agente do Laboratório de Estratégias com 12 ferramentas auditáveis."""

    TOOL_NAMES = (
        "list_strategies",
        "run_strategy",
        "get_portfolio",
        "propose_rebalance",
        "get_metrics",
        "compare_strategies",
        "get_log",
        "generate_report",
        "scan_global_opportunities",
        "get_market_regime",
        "get_correlation",
        "explain_candidate",
    )

    def __init__(self) -> None:
        cfg = market_data.load_strategies_config()
        self.gov = cfg.get("governance") or {}
        self.llm = OptionalLLMAdapter(cfg.get("llm"))

    # 12 ferramentas oficiais ---------------------------------------------------
    def list_strategies(self) -> list[dict[str, Any]]:
        return strategies_engine.list_strategies()

    def run_strategy(
        self,
        strategy_id: str,
        market_ctx: dict[str, Any] | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        return strategies_engine.run_strategy(strategy_id, market_ctx=market_ctx, persist=persist)

    def get_portfolio(self, strategy_id: str) -> dict[str, Any]:
        port = database.get_strategy_portfolio(strategy_id)
        if not port:
            return {"strategy_id": strategy_id, "status": INDISPONIVEL, "target_weights": []}
        return port

    def propose_rebalance(
        self,
        strategy_id: str,
        market_ctx: dict[str, Any] | None = None,
        actor: str = "strategy_agent",
    ) -> dict[str, Any]:
        return strategies_engine.propose_rebalance(strategy_id, market_ctx=market_ctx, actor=actor)

    def get_metrics(
        self,
        strategy_id: str,
        market_ctx: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        res = strategies_engine.run_strategy(strategy_id, market_ctx=market_ctx, persist=False)
        bt = res.get("backtest") or {}
        return {
            "strategy_id": strategy_id,
            "available": bt.get("available"),
            "mode": bt.get("mode"),
            "start_date": bt.get("start_date"),
            "end_date": bt.get("end_date"),
            "limiting_asset": bt.get("limiting_asset"),
            "metrics": bt.get("metrics") or {},
            "benchmarks": {
                k: (v.get("metrics") or {})
                for k, v in (bt.get("benchmarks") or {}).items()
            },
            "rule_used": res.get("rule_used"),
        }

    def compare_strategies(
        self,
        strategy_ids: list[str] | None = None,
        market_ctx: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ids = strategy_ids or [s["id"] for s in self.list_strategies() if s.get("enabled")]
        rows = []
        for sid in ids:
            m = self.get_metrics(sid, market_ctx=market_ctx)
            rows.append({
                "strategy_id": sid,
                "available": m.get("available"),
                "start_date": m.get("start_date"),
                "end_date": m.get("end_date"),
                "metrics": m.get("metrics"),
            })
        return rows

    def get_log(self, strategy_id: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return database.list_strategy_logs(strategy_id=strategy_id, limit=limit)

    def scan_global_opportunities(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        res = global_radar.scan_global_opportunities(market_ctx=market_ctx)
        for c in res.get("candidates") or []:
            c["label"] = CANDIDATO_LABEL
        return res

    def get_market_regime(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        return global_radar.scan_global_opportunities(market_ctx=market_ctx).get("regime") or {}

    def get_correlation(self, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        radar = self.scan_global_opportunities(market_ctx=market_ctx)
        return {
            "window_days": radar.get("correlation_window_days"),
            "correlation_matrix": radar.get("correlation_matrix"),
        }

    def explain_candidate(self, symbol: str, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        res = global_radar.explain_candidate(symbol, market_ctx=market_ctx)
        res["label"] = CANDIDATO_LABEL
        res["governance_note"] = "CANDIDATO A ESTUDO: entrada em carteira simulada exige proposta pendente e aprovação de Admin."
        return res

    def generate_report(
        self,
        period: str = "semanal",
        market_ctx: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        period_norm = "mensal" if str(period).lower().startswith("m") else "semanal"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        regime = self.get_market_regime(market_ctx=market_ctx)
        comp = self.compare_strategies(market_ctx=market_ctx)
        pending = database.list_strategy_proposals(status="PENDENTE", limit=20)
        lines = [
            f"# Relatório {period_norm.capitalize()} do Laboratório — {now_str}",
            f"- **Regime de Mercado:** `{regime.get('regime')}` ({regime.get('availability_label')})",
            f"- **Propostas Pendentes de Aprovação Admin:** `{len(pending)}`",
            "",
            "## Resumo das Estratégias Ativas (Simulação)",
        ]
        for row in comp:
            m = row.get("metrics") or {}
            if row.get("available"):
                lines.append(
                    f"- `{row['strategy_id']}` ({row.get('start_date')}..{row.get('end_date')}): "
                    f"Retorno `{m.get('total_return_pct')}%` | Vol `{m.get('volatility_ann_pct')}%` | "
                    f"MaxDD `{m.get('max_drawdown_pct')}%` | Sharpe `{m.get('sharpe_vs_cdi')}`"
                )
            else:
                lines.append(f"- `{row['strategy_id']}`: modo prospectivo/point-in-time (`sem backtest histórico`)")
        lines.append("")
        lines.append(f"> {self.gov.get('mandatory_disclaimer', '')}")
        return {
            "period": period_norm,
            "generated_at": now_str,
            "regime": regime,
            "strategies": comp,
            "pending_proposals": len(pending),
            "markdown": "\n".join(lines),
        }

    # Chat determinístico com recusa de recomendação personalizada -------------
    def chat(self, message: str, market_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        q = (message or "").strip()
        ql = q.lower()
        disclaimer = str(self.gov.get("mandatory_disclaimer") or "")

        if any(re.search(pat, ql) for pat in _PERSONALIZED_ADVICE_PATTERNS):
            strats = [s["id"] for s in self.list_strategies() if s.get("enabled")]
            reply = (
                "Não posso fazer recomendação personalizada de compra ou venda. "
                "Este ambiente é um laboratório educativo de carteiras-modelo simuladas (paper trading). "
                f"Estratégias ativas disponíveis para estudo: {', '.join(strats)}. "
                f"Aviso: {disclaimer}"
            )
            return {"mode": "deterministic", "refused": True, "reply": reply, "tools_used": ["list_strategies"], "disclaimer": disclaimer}

        # Roteamento determinístico por intenção
        if "regime" in ql or "vix" in ql or "curva" in ql or "macro" in ql:
            reg = self.get_market_regime(market_ctx=market_ctx)
            sigs = ", ".join(f"{s['name']}={s['value']} ({s['signal']})" for s in (reg.get("signals") or []))
            reply = f"Regime atual: {reg.get('regime')} ({reg.get('availability_label')}). Sinais: {sigs}. Regra: {reg.get('aggregation_rule')}"
            return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["get_market_regime"], "data": reg, "disclaimer": disclaimer}

        if "correla" in ql:
            corr = self.get_correlation(market_ctx=market_ctx)
            pairs = (corr.get("correlation_matrix") or {}).get("high_correlation_pairs") or []
            reply = f"Matriz de correlação (janela {corr.get('window_days')} pregões): {len(pairs)} par(es) com alta correlação (|r| >= 0.75)."
            return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["get_correlation"], "data": corr, "disclaimer": disclaimer}

        if "relat" in ql or "mensal" in ql or "semanal" in ql:
            rep = self.generate_report("mensal" if "mensal" in ql else "semanal", market_ctx=market_ctx)
            return {"mode": "deterministic", "refused": False, "reply": rep["markdown"], "tools_used": ["generate_report"], "data": rep, "disclaimer": disclaimer}

        if "radar" in ql or "oportun" in ql or "top" in ql:
            rad = self.scan_global_opportunities(market_ctx=market_ctx)
            top3 = [f"{c['symbol']} (score {c['score']}, {CANDIDATO_LABEL})" for c in (rad.get("candidates") or [])[:3]]
            reply = f"Radar Global — Regime {rad['regime']['regime']}. Top 3 candidatos a estudo: {'; '.join(top3)}. {rad.get('score_disclaimer')}"
            return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["scan_global_opportunities"], "data": rad, "disclaimer": disclaimer}

        if "compar" in ql:
            comp = self.compare_strategies(market_ctx=market_ctx)
            parts = [f"{r['strategy_id']}: ret={r['metrics'].get('total_return_pct')}%" if r.get("available") else f"{r['strategy_id']}: prospectivo" for r in comp]
            reply = "Comparação das estratégias ativas: " + " | ".join(parts)
            return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["compare_strategies"], "data": comp, "disclaimer": disclaimer}

        if "log" in ql or "auditor" in ql:
            logs = self.get_log(limit=5)
            reply = f"Últimos {len(logs)} registros no log de auditoria imutável."
            return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["get_log"], "data": logs, "disclaimer": disclaimer}

        # Verifica se citou algum ticker conhecido ou strategy_id
        for sid in ("dividendos_barsi", "indexacao_bogle", "trend_following_turtles", "dual_momentum_global", "risk_parity_simplified", "radar_top_n"):
            if sid in ql or sid.split("_")[0] in ql:
                res = self.run_strategy(sid, market_ctx=market_ctx, persist=False)
                ws = ", ".join(f"{w['symbol']} ({w['target_weight_pct']}%)" for w in (res.get("target_weights") or [])[:5])
                reply = f"Estratégia {sid} — Regra: {res.get('rule_used')}. Alocação atual: {ws or INDISPONIVEL}."
                return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["run_strategy"], "data": res, "disclaimer": disclaimer}

        m_sym = re.search(r"\b([A-Z]{3,5}(?:11|3|4)?(?:\.SA)?|-USD)\b", q)
        if m_sym:
            sym = m_sym.group(1)
            exp = self.explain_candidate(sym, market_ctx=market_ctx)
            if exp.get("status") != INDISPONIVEL:
                reply = f"{exp.get('symbol')} ({CANDIDATO_LABEL}, score {exp.get('score')}): A FAVOR: {'; '.join(exp.get('a_favor', []))}. CONTRA: {'; '.join(exp.get('contra', []))}."
                return {"mode": "deterministic", "refused": False, "reply": reply, "tools_used": ["explain_candidate"], "data": exp, "disclaimer": disclaimer}

        strats = self.list_strategies()
        reply = f"Laboratório com {len(strats)} estratégias catalogadas ({sum(1 for s in strats if s.get('enabled'))} ativas). Pergunte sobre regime, radar, comparação, log, relatório semanal/mensal ou uma estratégia específica."
        final_reply, mode = self.llm.summarize(reply, q)
        return {"mode": mode, "refused": False, "reply": final_reply, "tools_used": ["list_strategies"], "disclaimer": disclaimer}
