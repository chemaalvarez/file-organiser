"""
JSONL append-only logger.

One file per run: {root}/.ordenar/runs/{timestamp}.log.jsonl
Symlink: {root}/.ordenar/latest.log.jsonl → latest run
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import ActionType, Decision, ExecutionResult, RunSummary


class RunLogger:
    def __init__(self, root: Path, run_id: str, dry_run: bool = False) -> None:
        self.run_id = run_id
        self.root = root
        self.dry_run = dry_run
        self._log_dir = root / ".ordenar" / "runs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        self._log_path = self._log_dir / f"{ts}.log.jsonl"
        self._fh = open(self._log_path, "a", encoding="utf-8")
        self._start = time.monotonic()

        # Write run header
        self._write({
            "ts": _now_iso(),
            "run_id": run_id,
            "action": "start",
            "root": str(root),
            "dry_run": dry_run,
        })

    def log_result(self, result: ExecutionResult) -> None:
        entry: dict = {
            "ts": _now_iso(),
            "run_id": self.run_id,
            "action": result.action.value,
            "item_type": result.decision.item_type.value,
            "src": str(result.decision.src),
            "dst": str(result.decision.dst),
            "category": result.decision.category,
            "rule": result.decision.rule,
            "confidence": round(result.decision.confidence, 4),
            "sha256": result.decision.sha256,
            "size_bytes": result.decision.size_bytes,
            "duplicate_of": result.decision.duplicate_of,
        }
        if result.error_msg:
            entry["error_msg"] = result.error_msg
        self._write(entry)

    def finalize(self, summary: RunSummary) -> Path:
        elapsed = time.monotonic() - self._start
        self._write({
            "ts": _now_iso(),
            "run_id": self.run_id,
            "action": "summary",
            "total_scanned": summary.total_scanned,
            "moved": summary.moved,
            "skipped": summary.skipped,
            "errors": summary.errors,
            "unclassified": summary.unclassified,
            "duration_seconds": round(elapsed, 2),
        })
        self._fh.close()

        # Update symlink to latest
        latest = self.root / ".ordenar" / "latest.log.jsonl"
        try:
            if latest.is_symlink() or latest.exists():
                latest.unlink()
            os.symlink(self._log_path, latest)
        except OSError:
            pass

        return self._log_path

    def _write(self, entry: dict) -> None:
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()

    def __del__(self) -> None:
        try:
            if not self._fh.closed:
                self._fh.close()
        except Exception:
            pass


# ── Log reader ────────────────────────────────────────────────────────────────

def read_log(log_path: Path) -> list[dict]:
    """Read all entries from a JSONL log file."""
    entries = []
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def find_latest_log(root: Path) -> Optional[Path]:
    """Return the path of the most recent run log."""
    latest = root / ".ordenar" / "latest.log.jsonl"
    if latest.is_symlink() and latest.exists():
        return latest.resolve()
    runs_dir = root / ".ordenar" / "runs"
    if runs_dir.is_dir():
        logs = sorted(runs_dir.glob("*.log.jsonl"))
        if logs:
            return logs[-1]
    return None


# ── Hashing ───────────────────────────────────────────────────────────────────

def sha256_of(path: Path, chunk: int = 65536) -> Optional[str]:
    """Compute SHA-256 of a file. Returns None on error."""
    if not path.is_file():
        return None
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            while data := fh.read(chunk):
                h.update(data)
        return h.hexdigest()
    except OSError:
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds")
