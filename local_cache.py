"""Cache local versionado fora do Google Drive (%LOCALAPPDATA%\\Heuristika\\cache).

Nunca substitui o modo estrito: cada entrada possui SHA-256 de integridade e timestamp,
sinalizando `stale=True` quando ultrapassa `max_age_hours`.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

CACHE_SCHEMA_VERSION = "1.0.0"


def get_cache_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".heuristika")
    d = base / "Heuristika" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def compute_backtest_cache_key(
    strategy_id: str,
    data_signature: str,
    config_obj: dict[str, Any],
    strategy_code_path: Path,
) -> str:
    code_hash = _sha256_bytes(strategy_code_path.read_bytes()) if strategy_code_path.is_file() else "no_code"
    cfg_json = json.dumps(config_obj, sort_keys=True, ensure_ascii=False)
    payload = f"{CACHE_SCHEMA_VERSION}|{strategy_id}|{data_signature}|{cfg_json}|{code_hash}"
    return _sha256_bytes(payload.encode("utf-8"))[:24]


def save_cache_entry(namespace: str, key: str, payload: Any) -> Path:
    ns_dir = get_cache_dir() / namespace
    ns_dir.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    envelope = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "sha256": _sha256_bytes(body.encode("utf-8")),
        "payload": payload,
    }
    target = ns_dir / f"{key}.json"
    target.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return target


def load_cache_entry(namespace: str, key: str, max_age_hours: float = 24.0) -> dict[str, Any]:
    target = get_cache_dir() / namespace / f"{key}.json"
    if not target.is_file():
        return {"hit": False, "stale": True, "reason": "cache_miss", "payload": None}
    try:
        env = json.loads(target.read_text(encoding="utf-8"))
        if env.get("schema_version") != CACHE_SCHEMA_VERSION:
            return {"hit": False, "stale": True, "reason": "schema_mismatch", "payload": None}
        body = json.dumps(env.get("payload"), ensure_ascii=False, sort_keys=True)
        if _sha256_bytes(body.encode("utf-8")) != env.get("sha256"):
            return {"hit": False, "stale": True, "reason": "integrity_mismatch", "payload": None}
        saved_at = datetime.fromisoformat(str(env.get("saved_at")))
        stale = (datetime.now() - saved_at) > timedelta(hours=max_age_hours)
        return {"hit": True, "stale": stale, "saved_at": env.get("saved_at"), "payload": env.get("payload")}
    except Exception as exc:
        return {"hit": False, "stale": True, "reason": f"cache_error: {exc}", "payload": None}
