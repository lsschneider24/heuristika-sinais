"""Script de auditoria automática determinística (Parte 1).
Executa sem depender de rede nos testes, valida configuração, banco SQLite,
governança, snapshot B3 e todos os testes, gerando relatório em audit/reports/.
Retorna exit code 0 apenas se todas as checagens críticas e testes passarem.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
VENV_SITE = BASE_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE.is_dir() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import config  # noqa: E402
import database  # noqa: E402
import market_data  # noqa: E402


def _file_sha256_full(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_reports_manifest(reports_dir: Path) -> tuple[bool, str]:
    manifest_path = reports_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        return True, "MANIFEST.json ainda não inicializado (será criado nesta execução)"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"MANIFEST.json inválido: {exc}"
    entries = manifest.get("reports", {})
    mismatches: list[str] = []
    for name, expected_hash in entries.items():
        target = reports_dir / name
        if not target.is_file():
            mismatches.append(f"{name}: AUSENTE")
            continue
        actual_hash = _file_sha256_full(target)
        if actual_hash != expected_hash:
            mismatches.append(f"{name}: hash divergente ({actual_hash[:12]} != {expected_hash[:12]})")
    if mismatches:
        return False, "; ".join(mismatches)
    return True, f"{len(entries)} relatório(s) íntegro(s) no MANIFEST.json"


def _update_reports_manifest(reports_dir: Path, report_path: Path) -> None:
    manifest_path = reports_dir / "MANIFEST.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    else:
        manifest = {}
    reports = manifest.get("reports")
    if not isinstance(reports, dict):
        reports = {}
    reports[report_path.name] = _file_sha256_full(report_path)
    manifest["schema_version"] = "1.0.0"
    manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
    manifest["reports"] = reports
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        return "AUSENTE"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _get_git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(BASE_DIR), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return "N/A"


def _run_unittest_file(test_file: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BASE_DIR};{VENV_SITE}"
    proc = subprocess.run(
        [sys.executable, str(test_file), "-v"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(BASE_DIR),
        timeout=120,
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output.strip()


def run_all_checks() -> int:
    checks: list[tuple[str, str, str]] = []
    pendencias: list[str] = []

    # 1. Testes automatizados completos (sem rede)
    rc_basic, out_basic = _run_unittest_file(BASE_DIR / "tests" / "test_basic.py")
    checks.append((
        "Suíte principal (tests/test_basic.py)",
        "PASS" if rc_basic == 0 else "FAIL",
        f"exit_code={rc_basic}",
    ))

    rc_spec, out_spec = _run_unittest_file(BASE_DIR / "tests" / "test_audit_specifics.py")
    checks.append((
        "Testes específicos a..h (tests/test_audit_specifics.py)",
        "PASS" if rc_spec == 0 else "FAIL",
        f"exit_code={rc_spec}",
    ))

    rc_glob, out_glob = _run_unittest_file(BASE_DIR / "tests" / "test_global_radar.py")
    checks.append((
        "Testes offline Radar Global 2B (tests/test_global_radar.py)",
        "PASS" if rc_glob == 0 else "FAIL",
        f"exit_code={rc_glob}",
    ))

    # 2. Configuração e segurança
    checks.append((
        "ENABLE_SIMULATION_FALLBACK desligado por padrão",
        "PASS" if not config.ENABLE_SIMULATION_FALLBACK else "FAIL",
        f"ENABLE_SIMULATION_FALLBACK={config.ENABLE_SIMULATION_FALLBACK}",
    ))

    db_abs = str(Path(config.DATABASE_PATH).resolve())
    in_drive = "meu drive" in db_abs.lower() or str(BASE_DIR.resolve()).lower() in db_abs.lower()
    checks.append((
        "DATABASE_PATH fora do Google Drive",
        "PASS" if not in_drive else "FAIL",
        db_abs,
    ))

    drive_env = BASE_DIR / ".env"
    checks.append((
        "Ausência de .env com segredos dentro do Drive",
        "PASS" if not drive_env.exists() else "FAIL",
        f"drive_env_exists={drive_env.exists()} | ENV_PATH={config.ENV_PATH}",
    ))

    drive_db = BASE_DIR / "sinais_vip.db"
    checks.append((
        "Ausência de sinais_vip.db antigo dentro do Drive",
        "PASS" if not drive_db.exists() else "FAIL",
        f"drive_db_exists={drive_db.exists()}",
    ))

    gi_text = (BASE_DIR / ".gitignore").read_text(encoding="utf-8") if (BASE_DIR / ".gitignore").is_file() else ""
    gi_ok = all(tok in gi_text for tok in ("*.db*", ".env", "backups/", "cdi_sgs_cache.json"))
    checks.append((
        ".gitignore cobre *.db*, .env, backups e caches",
        "PASS" if gi_ok else "FAIL",
        "Verificado em .gitignore",
    ))

    # 3. Banco SQLite: tabelas strategy_*, triggers reais em cópia temporária e backup datado
    database.init_db()
    tmp_db_dir = Path(tempfile.mkdtemp(prefix="hk_audit_db_"))
    try:
        tmp_db_copy = tmp_db_dir / "audit_copy.db"
        src_conn = sqlite3.connect(config.DATABASE_PATH)
        dst_conn = sqlite3.connect(tmp_db_copy)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()

        c = sqlite3.connect(tmp_db_copy)
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
        req_tables = {"strategy_portfolios", "strategy_proposals", "strategy_param_versions", "strategy_audit_log"}
        tables_ok = req_tables.issubset(tables)
        checks.append((
            "Tabelas strategy_* existem no SQLite",
            "PASS" if tables_ok else "FAIL",
            f"encontradas={sorted(req_tables & tables)}",
        ))

        triggers = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger';").fetchall()}
        trig_ok = {"trg_strategy_audit_log_no_update", "trg_strategy_audit_log_no_delete"}.issubset(triggers)

        # Testa bloqueio real de UPDATE e DELETE na cópia temporária
        c.execute(
            "INSERT INTO strategy_audit_log (created_at, strategy_id, actor, rule_ref, data_used_json, decision) "
            "VALUES ('2026-11-23 00:00:00', 'audit_test', 'auditor', 'r', '{}', 'ok');"
        )
        c.commit()
        upd_blocked = False
        del_blocked = False
        try:
            c.execute("UPDATE strategy_audit_log SET decision='x' WHERE strategy_id='audit_test';")
        except sqlite3.DatabaseError:
            upd_blocked = True
        try:
            c.execute("DELETE FROM strategy_audit_log WHERE strategy_id='audit_test';")
        except sqlite3.DatabaseError:
            del_blocked = True
        c.close()

        checks.append((
            "Triggers bloqueiam UPDATE e DELETE em strategy_audit_log",
            "PASS" if (trig_ok and upd_blocked and del_blocked) else "FAIL",
            f"triggers={trig_ok}, update_blocked={upd_blocked}, delete_blocked={del_blocked}",
        ))
    finally:
        shutil.rmtree(tmp_db_dir, ignore_errors=True)

    bkp_dir = Path(config.DATABASE_PATH).resolve().parent / "backups"
    bkp_files = sorted(bkp_dir.glob("sinais_vip_backup_*.db")) if bkp_dir.is_dir() else []
    if not bkp_files:
        created_bkp = database.backup_database()
        bkp_files = [Path(created_bkp)]
    checks.append((
        "Backup datado do banco existe",
        "PASS" if len(bkp_files) > 0 else "FAIL",
        str(bkp_files[-1]) if bkp_files else "Nenhum backup encontrado",
    ))

    # 4. Governança em código
    strat_code = (BASE_DIR / "strategies_engine.py").read_text(encoding="utf-8")
    gate_ok = "if not is_admin or not str(admin_user" in strat_code and "PermissionError" in strat_code
    no_sim_in_strat = "_generate_simulated_candles" not in strat_code
    checks.append((
        "approve_or_reject_proposal exige Admin dentro da função",
        "PASS" if gate_ok else "FAIL",
        "Validação de is_admin e PermissionError presente em strategies_engine.py",
    ))
    checks.append((
        "Nenhuma estratégia usa _generate_simulated_candles",
        "PASS" if no_sim_in_strat else "FAIL",
        "strategies_engine.py livre de _generate_simulated_candles",
    ))

    # 5. Snapshot b3_fundamentals.json
    fund = market_data.load_b3_fundamentals()
    total_stocks = len(fund.get("stocks", []))
    verified_true = sum(1 for s in fund.get("stocks", []) if s.get("verified") is True)
    verified_false = total_stocks - verified_true
    no_source_fields = []
    for s in fund.get("stocks", []):
        for fk, fv in (s.get("fields") or {}).items():
            if not fv.get("source"):
                no_source_fields.append(f"{s['symbol']}.{fk}")

    checks.append((
        "Snapshot b3_fundamentals.json íntegro e auditado",
        "PASS" if (total_stocks >= 30 and not no_source_fields) else "FAIL",
        f"total={total_stocks}, verified_true={verified_true}, verified_false={verified_false}, stale={fund.get('is_stale')}, sem_fonte={len(no_source_fields)}",
    ))
    if verified_false > 0:
        pendencias.append(
            f"Snapshot B3: {verified_false} de {total_stocks} ativos com verified=false aguardando conferência de evidência em fonte primária pelo Agente Auditor (AUDITOR.md)."
        )
    if fund.get("is_stale"):
        pendencias.append(
            f"Snapshot B3 com {fund.get('age_days')} dias (acima do limite de {fund.get('max_age_days')} dias): dados desatualizados."
        )

    # 6. Verifica integridade dos relatórios anteriores e gera novo relatório em audit/reports/
    now = datetime.now()
    reports_dir = BASE_DIR / "audit" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest_ok, manifest_detail = _verify_reports_manifest(reports_dir)
    checks.append((
        "Integridade dos relatórios (audit/reports/MANIFEST.json)",
        "PASS" if manifest_ok else "FAIL",
        manifest_detail,
    ))
    report_path = reports_dir / f"audit_{now.strftime('%Y-%m-%d_%H%M')}.md"

    all_passed = all(status == "PASS" for _, status, _ in checks)
    exit_code = 0 if all_passed else 1

    key_files = [
        BASE_DIR / "config.py",
        BASE_DIR / "database.py",
        BASE_DIR / "market_data.py",
        BASE_DIR / "global_radar.py",
        BASE_DIR / "strategies_engine.py",
        BASE_DIR / "strategies_config.json",
        BASE_DIR / "data" / "b3_fundamentals.json",
        BASE_DIR / "data" / "global_valuation.json",
        BASE_DIR / "tests" / "test_basic.py",
        BASE_DIR / "tests" / "test_audit_specifics.py",
        BASE_DIR / "tests" / "test_global_radar.py",
    ]
    hashes_lines = [f"- `{p.relative_to(BASE_DIR)}`: `{_file_sha256(p)}`" for p in key_files]
    table_lines = [
        "| Checagem | Status | Detalhe |",
        "| --- | --- | --- |",
    ] + [f"| {name} | **{status}** | `{detail}` |" for name, status, detail in checks]

    pend_lines = [f"- {p}" for p in pendencias] if pendencias else ["- Nenhuma pendência bloqueante."]

    md = "\n".join([
        f"# Relatório de Auditoria Automática — {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- **Resultado Final:** `{'PASS (EXIT 0)' if exit_code == 0 else 'FAIL (EXIT 1)'}`",
        f"- **Commit Git:** `{_get_git_head()}`",
        "",
        "## Tabela de Checagens",
        *table_lines,
        "",
        "## Hashes SHA-256 (12 chars) dos Arquivos Auditados",
        *hashes_lines,
        "",
        "## Pendências Registradas",
        *pend_lines,
        "",
        "## Saída Bruta — tests/test_basic.py",
        "```text",
        out_basic,
        "```",
        "",
        "## Saída Bruta — tests/test_audit_specifics.py",
        "```text",
        out_spec,
        "```",
        "",
        "## Saída Bruta — tests/test_global_radar.py",
        "```text",
        out_glob,
        "```",
        "",
    ])
    report_path.write_text(md, encoding="utf-8")
    _update_reports_manifest(reports_dir, report_path)

    print(f"AUDIT_REPORT={report_path}")
    print(f"AUDIT_EXIT_CODE={exit_code}")
    for p in pendencias:
        print(f"PENDENCIA={p}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run_all_checks())
