"""Backup portátil do histórico Git (git bundle) e do banco SQLite (Etapa F - 6b).

Uso:
    python audit/tools/backup_drive_state.py
Gera:
    - backups_repo/sinais_repo_AAAA-MM-DD_HHMM.bundle
    - backups_db/sinais_vip_backup_AAAA-MM-DD_HHMMSS.db (via database.backup_database)
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
EXT_VENV_SITE = Path(os.environ.get("LOCALAPPDATA", "")) / "Heuristika" / "venv-sinais" / "Lib" / "site-packages"
if EXT_VENV_SITE.is_dir() and str(EXT_VENV_SITE) not in sys.path:
    sys.path.insert(0, str(EXT_VENV_SITE))

import database  # noqa: E402


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d_%H%M")
    repo_bkp_dir = BASE_DIR / "backups_repo"
    repo_bkp_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = repo_bkp_dir / f"sinais_repo_{now}.bundle"

    proc = subprocess.run(
        ["git", "-C", str(BASE_DIR), "bundle", "create", str(bundle_path), "--all"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        print("ERRO git bundle:", proc.stderr or proc.stdout)
        return 1

    db_bkp_dir = BASE_DIR / "backups_db"
    db_bkp_dir.mkdir(parents=True, exist_ok=True)
    db_bkp_path = database.backup_database(backup_dir=str(db_bkp_dir))

    print(f"GIT_BUNDLE={bundle_path} ({bundle_path.stat().st_size} bytes)")
    print(f"DB_BACKUP={db_bkp_path} ({Path(db_bkp_path).stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
