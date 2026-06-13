"""
Executor — moves files and folders according to the plan.

Handles:
  - Creating destination directories
  - Duplicate detection by SHA-256
  - Renaming on collision (name_1.ext, name_2.ext …)
  - Building ExecutionResults for the logger
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .logger import RunLogger, sha256_of
from .models import ActionType, Decision, ExecutionResult, ItemType, RunSummary


class Executor:
    def __init__(
        self,
        root: Path,
        logger: RunLogger,
        on_duplicate: str = "rename",   # skip | rename | overwrite
        dry_run: bool = False,
    ) -> None:
        self.root = root
        self.logger = logger
        self.on_duplicate = on_duplicate
        self.dry_run = dry_run
        self._seen_hashes: dict[str, Path] = {}   # sha256 → first seen path

    def execute_plan(self, decisions: list[Decision]) -> RunSummary:
        summary = RunSummary(
            run_id=self.logger.run_id,
            root=self.root,
            dry_run=self.dry_run,
            total_scanned=len(decisions),
        )

        for decision in decisions:
            result = self._execute_one(decision)
            self.logger.log_result(result)

            if result.action == ActionType.MOVE:
                summary.moved += 1
            elif result.action == ActionType.SKIP:
                summary.skipped += 1
            elif result.action == ActionType.ERROR:
                summary.errors += 1

            if decision.category == "_SinClasificar":
                summary.unclassified += 1

        return summary

    def _execute_one(self, decision: Decision) -> ExecutionResult:
        src = decision.src

        if not src.exists():
            return ExecutionResult(
                decision=decision,
                action=ActionType.ERROR,
                error_msg=f"Source not found: {src}",
            )

        # Duplicate check (file only)
        if decision.item_type == ItemType.FILE and decision.sha256:
            if decision.sha256 in self._seen_hashes:
                orig = self._seen_hashes[decision.sha256]
                decision.duplicate_of = str(orig)
                if self.on_duplicate == "skip":
                    return ExecutionResult(decision=decision, action=ActionType.SKIP)
            else:
                self._seen_hashes[decision.sha256] = src

        dst = self._resolve_dst(decision)

        if self.dry_run:
            return ExecutionResult(decision=decision, action=ActionType.MOVE)

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            decision.dst = dst
            return ExecutionResult(decision=decision, action=ActionType.MOVE)
        except Exception as exc:
            return ExecutionResult(
                decision=decision,
                action=ActionType.ERROR,
                error_msg=str(exc),
            )

    def _resolve_dst(self, decision: Decision) -> Path:
        """
        Resolve the final destination path, handling collisions.
        For folders: if destination already exists, merge contents.
        For files: apply on_duplicate strategy.
        """
        dst = decision.dst

        if decision.item_type == ItemType.FOLDER:
            # Folders: destination may already exist (merge is fine — shutil.move handles it)
            return dst

        if not dst.exists():
            return dst

        # Destination file exists — check if it's the same content
        if decision.sha256 and sha256_of(dst) == decision.sha256:
            if self.on_duplicate == "overwrite":
                return dst
            # skip or rename: mark as duplicate
            decision.duplicate_of = str(dst)
            if self.on_duplicate == "skip":
                return dst   # will be caught above as skip

        if self.on_duplicate == "overwrite":
            return dst

        # rename: add numeric suffix
        return _unique_path(dst)


def _unique_path(path: Path) -> Path:
    """Return a non-existing path by appending _1, _2 … before the extension."""
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
