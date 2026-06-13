"""Phase 0 — Bootstrap: read existing Trabajo/ and Personal/ structure."""

from __future__ import annotations

from pathlib import Path

from .models import KnownContext
from .taxonomy import PERSONAL_CATEGORIES


def bootstrap(root: Path, config_companies: list[str]) -> KnownContext:
    """
    Scan root for existing Trabajo/ and Personal/ folders and build
    a catalogue of known companies, clients, projects and personal categories.

    Config companies are merged with whatever is found on disk; the existing
    folder names always take precedence as ground-truth identifiers.
    """
    ctx = KnownContext()

    _load_trabajo(root, ctx, config_companies)
    _load_personal(root, ctx)

    return ctx


# ── Trabajo ───────────────────────────────────────────────────────────────────

def _load_trabajo(root: Path, ctx: KnownContext, config_companies: list[str]) -> None:
    trabajo_dir = root / "Trabajo"

    # Start with companies declared in config
    known = {c.lower(): c for c in config_companies}

    if trabajo_dir.is_dir():
        for empresa_dir in _subdirs(trabajo_dir):
            name = empresa_dir.name
            known[name.lower()] = name
            _load_empresa(empresa_dir, ctx)

    ctx.companies = list(known.values())


def _load_empresa(empresa_dir: Path, ctx: KnownContext) -> None:
    empresa = empresa_dir.name
    clientes: list[str] = []

    for cliente_dir in _subdirs(empresa_dir):
        # Skip internal placeholders
        if cliente_dir.name.startswith("_"):
            continue
        clientes.append(cliente_dir.name)
        _load_cliente(empresa, cliente_dir, ctx)

    if clientes:
        ctx.clients[empresa] = clientes


def _load_cliente(empresa: str, cliente_dir: Path, ctx: KnownContext) -> None:
    proyectos: list[str] = []

    for proyecto_dir in _subdirs(cliente_dir):
        if proyecto_dir.name.startswith("_"):
            continue
        proyectos.append(proyecto_dir.name)

    if proyectos:
        key = f"{empresa}/{cliente_dir.name}"
        ctx.projects[key] = proyectos


# ── Personal ──────────────────────────────────────────────────────────────────

def _load_personal(root: Path, ctx: KnownContext) -> None:
    personal_dir = root / "Personal"
    if not personal_dir.is_dir():
        return

    canonical = {alias: cat for cat, aliases in PERSONAL_CATEGORIES.items()
                 for alias in aliases}
    canonical.update({cat.lower(): cat for cat in PERSONAL_CATEGORIES})

    for subdir in _subdirs(personal_dir):
        name = subdir.name
        canonical_name = canonical.get(name.lower(), name)
        if canonical_name not in ctx.personal_categories:
            ctx.personal_categories.append(canonical_name)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _subdirs(path: Path) -> list[Path]:
    """Return immediate subdirectories, sorted."""
    try:
        return sorted(
            (p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")),
            key=lambda p: p.name.lower(),
        )
    except PermissionError:
        return []
