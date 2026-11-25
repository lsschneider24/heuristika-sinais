"""Ferramentas permanentes de auditoria independente (audit/independent/run_checks.py)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def check_no_zero_for_missing() -> list[str]:
    snap = json.loads((BASE_DIR / "data" / "b3_fundamentals.json").read_text(encoding="utf-8"))
    issues = []
    for s in snap.get("stocks", []):
        sym = s.get("symbol")
        for k, f in (s.get("fields") or {}).items():
            if f.get("value") == 0.0 and "indispon" in str(f.get("source", "")).lower():
                issues.append(f"{sym}.{k}: valor 0.0 com fonte indicando indisponível")
    return issues


def check_no_abs_paths_or_secrets() -> list[str]:
    issues = []
    pat_abs = re.compile(r"([A-Za-z]:\\\\|J:/|C:/Users/)")
    for p in BASE_DIR.glob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if pat_abs.search(txt):
            issues.append(f"{p.name}: caminho absoluto encontrado")
    if (BASE_DIR / ".env").exists():
        issues.append(".env real encontrado dentro do repositório/Drive")
    return issues


def main() -> int:
    z_issues = check_no_zero_for_missing()
    p_issues = check_no_abs_paths_or_secrets()
    all_issues = z_issues + p_issues
    print(f"INDEPENDENT_CHECKS_ISSUES={len(all_issues)}")
    for i in all_issues:
        print(f" - {i}")
    return 1 if all_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
