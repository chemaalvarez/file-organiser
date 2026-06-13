"""
Hierarchical top-down processor.

Works level by level:
  Level 1 — root contents → Trabajo or Personal (in block if confident)
  Level 2 — Trabajo/  → empresa;   Personal/ → category
  Level 3 — Empresa/  → client
  Level 4 — Client/   → project
  Level 5 — Project/  → doc type (leaf — file by file)
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Generator

from .classifier import Classifier
from .config import OrganizerConfig
from .models import ClassificationResult, Decision, ItemType, KnownContext
from .taxonomy import IGNORE_NAMES, IGNORE_SUFFIXES, PROYECTO_SUBDIRS, TRABAJO


def build_plan(
    root: Path,
    config: OrganizerConfig,
    context: KnownContext,
) -> list[Decision]:
    """
    Walk the root folder level by level and return a flat list of Decisions
    (the plan) without touching anything on disk.
    """
    classifier = Classifier(config, context)
    decisions: list[Decision] = []

    _process_level1(root, classifier, config, decisions)

    return decisions


# ── Level processors ──────────────────────────────────────────────────────────

def _process_level1(
    root: Path,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Root contents → move to Trabajo/ or Personal/ (in block if confident)."""
    for item in _scandir(root, config):
        rel = item.relative_to(root)

        # Skip the two canonical branches — we only need to process their contents
        if rel.parts[0] in ("Trabajo", "Personal", ".ordenar"):
            if item.is_dir():
                _process_level2(root, item, classifier, config, decisions)
            continue

        if item.is_dir():
            result = classifier.classify_folder(item)
            if result.move_as_block and result.destination is not None:
                dest_abs = root / result.destination.parent / item.name
                decisions.append(_make_decision(item, dest_abs, result))
            else:
                # Mixed folder: descend with whatever branch hint we got
                _process_mixed_folder(root, item, result, classifier, config, decisions)
        else:
            result = classifier.classify_file(item)
            if result.destination is not None:
                dest_abs = root / result.destination
                decisions.append(_make_decision(item, dest_abs, result))
            else:
                dest_abs = root / "Personal" / "_SinClasificar" / item.name
                decisions.append(_make_decision(
                    item, dest_abs,
                    ClassificationResult(
                        src=item, item_type=ItemType.FILE,
                        destination=dest_abs.relative_to(root),
                        category="_SinClasificar", rule="unclassified", confidence=0.0,
                    ),
                ))


def _process_level2(
    root: Path,
    branch: Path,           # Trabajo/ or Personal/
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Process direct children of Trabajo/ or Personal/."""
    branch_name = branch.name

    for item in _scandir(branch, config):
        if branch_name == TRABAJO:
            _process_trabajo_item(root, branch, item, classifier, config, decisions)
        else:
            _process_personal_item(root, branch, item, classifier, config, decisions)


def _process_trabajo_item(
    root: Path,
    trabajo_dir: Path,
    item: Path,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Item inside Trabajo/ — decide empresa, then recurse."""
    company_lower = {c.lower(): c for c in classifier.ctx.companies}
    name_lower = item.name.lower()

    if item.is_dir():
        if name_lower in company_lower:
            # Already a known empresa folder — go deeper
            _process_level3_empresa(root, item, classifier, config, decisions)
        elif item.name.startswith("_"):
            # Placeholder (_SinClasificar etc.) — leave as-is
            pass
        else:
            # Unknown folder inside Trabajo — try to classify and re-nest
            result = classifier.classify_folder(item)
            if result.move_as_block and result.destination is not None:
                dest_abs = root / result.destination.parent / item.name
                decisions.append(_make_decision(item, dest_abs, result))
            else:
                _process_level3_empresa(root, item, classifier, config, decisions)
    else:
        # Loose file inside Trabajo/
        result = classifier.classify_file(item, parent_context="Trabajo")
        if result.destination is not None:
            dest_abs = root / result.destination
            decisions.append(_make_decision(item, dest_abs, result))


def _process_personal_item(
    root: Path,
    personal_dir: Path,
    item: Path,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Item inside Personal/ — classify to subcategory."""
    if item.is_file():
        result = classifier.classify_file(item, parent_context="Personal")
        if result.destination is not None:
            dest_abs = root / result.destination
            decisions.append(_make_decision(item, dest_abs, result))


def _process_level3_empresa(
    root: Path,
    empresa_dir: Path,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Inside Trabajo/{Empresa}/ — identify clients."""
    empresa = empresa_dir.name
    known_clients = {c.lower(): c for c in classifier.ctx.clients.get(empresa, [])}

    for item in _scandir(empresa_dir, config):
        if item.is_dir():
            if item.name.lower() in known_clients or not item.name.startswith("_"):
                _process_level4_cliente(root, empresa_dir, item, classifier, config, decisions)
        else:
            # Loose file inside Empresa/ — needs a client
            result = classifier.classify_file(item, parent_context=f"Trabajo/{empresa}")
            if result.destination is not None:
                dest_abs = root / result.destination
                decisions.append(_make_decision(item, dest_abs, result))
            else:
                dest_abs = root / "Trabajo" / empresa / "_SinCliente" / item.name
                decisions.append(_make_decision(
                    item, dest_abs,
                    ClassificationResult(
                        src=item, item_type=ItemType.FILE,
                        destination=dest_abs.relative_to(root),
                        category=f"Trabajo/{empresa}/_SinCliente",
                        rule="unclassified", confidence=0.0,
                    ),
                ))


def _process_level4_cliente(
    root: Path,
    empresa_dir: Path,
    cliente_dir: Path,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Inside Trabajo/{Empresa}/{Cliente}/ — identify projects."""
    empresa = empresa_dir.name
    cliente = cliente_dir.name
    key = f"{empresa}/{cliente}"
    known_projects = set(classifier.ctx.projects.get(key, []))

    for item in _scandir(cliente_dir, config):
        if item.is_dir():
            if item.name in PROYECTO_SUBDIRS or item.name in known_projects:
                # Already a project or doc-type folder — process files inside
                _process_level5_proyecto(root, item, classifier, config, decisions)
            elif not item.name.startswith("_"):
                # Treat as a project folder
                _process_level5_proyecto(root, item, classifier, config, decisions)
        else:
            # Loose file inside Cliente/ — put in a doc-type subfolder
            result = classifier.classify_file(
                item, parent_context=f"Trabajo/{empresa}/{cliente}"
            )
            if result.destination is not None:
                dest_abs = root / result.destination
                decisions.append(_make_decision(item, dest_abs, result))


def _process_level5_proyecto(
    root: Path,
    proyecto_dir: Path,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Leaf level — classify each file into a doc-type subfolder."""
    for item in _iter_files_recursive(proyecto_dir, config):
        # Files already in a PROYECTO_SUBDIRS folder are fine
        rel_parts = item.relative_to(proyecto_dir).parts
        if len(rel_parts) == 2 and rel_parts[0] in PROYECTO_SUBDIRS:
            continue
        if len(rel_parts) == 1:
            # File directly in project root — classify it
            result = classifier.classify_file(
                item, parent_context=str(proyecto_dir.relative_to(root))
            )
            if result.destination is not None:
                dest_abs = root / result.destination
                if dest_abs != item:
                    decisions.append(_make_decision(item, dest_abs, result))


def _process_mixed_folder(
    root: Path,
    folder: Path,
    folder_result: ClassificationResult,
    classifier: Classifier,
    config: OrganizerConfig,
    decisions: list[Decision],
) -> None:
    """Folder confidence too low — process its contents individually."""
    for item in _scandir(folder, config):
        if item.is_dir():
            result = classifier.classify_folder(item)
            if result.move_as_block and result.destination is not None:
                dest_abs = root / result.destination.parent / item.name
                decisions.append(_make_decision(item, dest_abs, result))
            else:
                _process_mixed_folder(root, item, result, classifier, config, decisions)
        else:
            result = classifier.classify_file(item)
            if result.destination is not None:
                dest_abs = root / result.destination
                decisions.append(_make_decision(item, dest_abs, result))
            else:
                dest_abs = root / "Personal" / "_SinClasificar" / item.name
                decisions.append(_make_decision(
                    item, dest_abs,
                    ClassificationResult(
                        src=item, item_type=ItemType.FILE,
                        destination=dest_abs.relative_to(root),
                        category="_SinClasificar", rule="unclassified", confidence=0.0,
                    ),
                ))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_decision(src: Path, dst: Path, result: ClassificationResult) -> Decision:
    from .logger import sha256_of  # avoid circular import at module level
    size = src.stat().st_size if src.exists() and src.is_file() else 0
    sha = sha256_of(src) if src.is_file() else None
    return Decision(
        src=src,
        dst=dst,
        item_type=result.item_type,
        category=result.category or "_SinClasificar",
        rule=result.rule,
        confidence=result.confidence,
        sha256=sha,
        size_bytes=size,
    )


def _scandir(path: Path, config: OrganizerConfig) -> Generator[Path, None, None]:
    """Yield direct children of path, respecting ignore patterns."""
    try:
        for item in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if _should_ignore(item, config):
                continue
            yield item
    except PermissionError:
        return


def _iter_files_recursive(path: Path, config: OrganizerConfig) -> Generator[Path, None, None]:
    try:
        for item in path.rglob("*"):
            if item.is_file() and not _should_ignore(item, config):
                yield item
    except PermissionError:
        return


def _should_ignore(path: Path, config: OrganizerConfig) -> bool:
    name = path.name
    if name in IGNORE_NAMES:
        return True
    if path.suffix.lower() in IGNORE_SUFFIXES:
        return True
    if name.startswith(".") and name not in (".ordenar",):
        return True
    for pattern in config.ignore_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False
