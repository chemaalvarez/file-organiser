"""Data models for the file organizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ActionType(str, Enum):
    MOVE = "move"
    SKIP = "skip"
    ERROR = "error"
    SUMMARY = "summary"


class ItemType(str, Enum):
    FILE = "file"
    FOLDER = "folder"


@dataclass
class ClassificationResult:
    """Result of classifying a single file or folder."""

    src: Path
    item_type: ItemType
    destination: Optional[Path]          # None = unclassified
    category: Optional[str]             # e.g. "Trabajo/Facturas"
    rule: str                            # signal that triggered the decision
    confidence: float                    # 0.0–1.0
    move_as_block: bool = False          # folder moved as a whole unit


@dataclass
class Decision:
    """A planned action: move src → dst."""

    src: Path
    dst: Path
    item_type: ItemType
    category: str
    rule: str
    confidence: float
    sha256: Optional[str] = None
    size_bytes: int = 0
    duplicate_of: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of executing a single Decision."""

    decision: Decision
    action: ActionType
    error_msg: Optional[str] = None


@dataclass
class RunSummary:
    """Aggregated stats for a complete run."""

    run_id: str
    root: Path
    dry_run: bool
    total_scanned: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    unclassified: int = 0
    duration_seconds: float = 0.0


@dataclass
class KnownContext:
    """Catalogue built from the existing Trabajo/ and Personal/ structure."""

    companies: list[str] = field(default_factory=list)
    # company_name → list of known client names
    clients: dict[str, list[str]] = field(default_factory=dict)
    # company/client → list of known project names
    projects: dict[str, list[str]] = field(default_factory=dict)
    # existing Personal/ subcategory folders
    personal_categories: list[str] = field(default_factory=list)
