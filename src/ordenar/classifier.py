"""
Classification engine — decides where each file or folder should go.

Signals applied in priority order:
  1. Path context (existing Trabajo/Empresa/Cliente structure)
  2. Name matches a known company or personal category
  3. Keywords in name / path
  4. File extension
  5. File content (magic bytes → first lines → metadata)
  6. AI fallback (Ollama) — only when steps 1–5 fail
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .config import OrganizerConfig
from .models import ClassificationResult, ItemType, KnownContext
from .taxonomy import (
    DOCUMENT_EXTENSIONS,
    EXTENSION_PERSONAL_MAP,
    EXTENSION_TRABAJO_MAP,
    IMAGE_EXTENSIONS,
    PERSONAL_CATEGORIES,
    PERSONAL_SUBCATEGORIES,
    PROYECTO_KEYWORD_MAP,
    TRABAJO_KEYWORDS,
    VIDEO_EXTENSIONS,
)


class Classifier:
    def __init__(self, config: OrganizerConfig, context: KnownContext) -> None:
        self.config = config
        self.ctx = context
        self._company_lower = {c.lower(): c for c in context.companies}
        self._personal_lower = {
            alias: cat
            for cat, aliases in PERSONAL_CATEGORIES.items()
            for alias in aliases
        }
        self._personal_lower.update({c.lower(): c for c in PERSONAL_CATEGORIES})
        # Family members from config → classify to Familiar/{member}/
        self._family_lower = {m.lower(): m for m in config.family_members}
        # Known cars → classify to Coches/{car}/
        self._cars_lower = {c.lower(): c for c in config.known_cars}
        # Known homes: city → addresses
        self._homes_lower: dict[str, str] = {}
        for city, addresses in config.known_homes.items():
            for addr in addresses:
                self._homes_lower[addr.lower()] = city

    # ── Public API ────────────────────────────────────────────────────────────

    def classify_file(self, path: Path, parent_context: Optional[str] = None) -> ClassificationResult:
        """Classify a single file. parent_context is the partial dest path so far."""
        for method in [
            lambda: self._by_path_context(path, parent_context),
            lambda: self._by_name_keyword(path),
            lambda: self._by_extension(path),
            lambda: self._by_content(path),
        ]:
            result = method()
            if result is not None:
                return ClassificationResult(
                    src=path,
                    item_type=ItemType.FILE,
                    destination=result[0],
                    category=result[1],
                    rule=result[2],
                    confidence=result[3],
                )

        return ClassificationResult(
            src=path,
            item_type=ItemType.FILE,
            destination=None,
            category=None,
            rule="unclassified",
            confidence=0.0,
        )

    def classify_folder(self, path: Path) -> ClassificationResult:
        """
        Classify a folder by sampling its contents.
        If confidence >= threshold → move as block.
        Otherwise → caller will descend into it.
        """
        files = list(_iter_files_shallow(path, max_files=50))

        if not files:
            # Empty folder: classify by name only
            result = self._by_name_for_folder(path)
            if result:
                dest, category, rule, conf = result
                return ClassificationResult(
                    src=path, item_type=ItemType.FOLDER,
                    destination=dest, category=category,
                    rule=rule, confidence=conf,
                    move_as_block=(conf >= self.config.confidence_threshold),
                )
            return ClassificationResult(
                src=path, item_type=ItemType.FOLDER,
                destination=None, category=None,
                rule="unclassified", confidence=0.0,
            )

        votes: dict[str, int] = {}
        for f in files:
            r = self.classify_file(f)
            if r.destination is not None:
                bucket = r.category or str(r.destination)
                votes[bucket] = votes.get(bucket, 0) + 1

        if not votes:
            confidence = 0.0
            top_dest = None
            top_cat = None
            top_rule = "unclassified"
        else:
            top_cat = max(votes, key=votes.__getitem__)
            top_votes = votes[top_cat]
            confidence = top_votes / len(files)
            # Re-classify a sample file to get the destination path for the folder
            sample = next((f for f in files), None)
            sample_r = self.classify_file(sample) if sample else None
            top_dest = sample_r.destination.parent if sample_r and sample_r.destination else None
            top_rule = f"folder_vote:{top_cat}"

        return ClassificationResult(
            src=path,
            item_type=ItemType.FOLDER,
            destination=top_dest,
            category=top_cat,
            rule=top_rule,
            confidence=confidence,
            move_as_block=(confidence >= self.config.confidence_threshold and top_dest is not None),
        )

    # ── Signal 1: Path context ────────────────────────────────────────────────

    def _by_path_context(
        self, path: Path, parent_context: Optional[str]
    ) -> Optional[tuple[Path, str, str, float]]:
        if not parent_context:
            return None
        # Already inside Trabajo/{Empresa}/{Cliente}/... → keep going deeper
        parts = Path(parent_context).parts
        if parts and parts[0] == "Trabajo" and len(parts) >= 3:
            empresa = parts[1]
            cliente = parts[2]
            project = parts[3] if len(parts) > 3 else None
            subdir = _doc_type_subdir(path)
            if project:
                dest = Path("Trabajo") / empresa / cliente / project / subdir / path.name
                return dest, f"Trabajo/{subdir}", "path_context:project", 1.0
            dest = Path("Trabajo") / empresa / cliente / subdir / path.name
            return dest, f"Trabajo/{subdir}", "path_context:cliente", 0.9
        return None

    # ── Signal 2: Name keywords ───────────────────────────────────────────────

    def _by_name_keyword(self, path: Path) -> Optional[tuple[Path, str, str, float]]:
        name_lower = _normalize(path.name)

        # Check company names → Trabajo
        for comp_lower, comp_name in self._company_lower.items():
            if comp_lower in name_lower:
                subdir = _doc_type_subdir(path)
                dest = Path("Trabajo") / comp_name / "_SinCliente" / subdir / path.name
                return dest, f"Trabajo/{subdir}", f"keyword:company:{comp_name}", 0.85

        # Check family members → Personal/Familiar/{member}/
        for member_lower, member_name in self._family_lower.items():
            if member_lower in name_lower:
                dest = Path("Personal") / "Familiar" / member_name / path.name
                return dest, f"Personal/Familiar/{member_name}", f"keyword:family:{member_name}", 0.8

        # Check known cars → Personal/Coches/{car}/
        for car_lower, car_name in self._cars_lower.items():
            if car_lower in name_lower:
                dest = Path("Personal") / "Coches" / car_name / path.name
                return dest, f"Personal/Coches/{car_name}", f"keyword:car:{car_name}", 0.85

        # Check known home addresses → Personal/Vivienda/{city}/
        for addr_lower, city in self._homes_lower.items():
            if addr_lower in name_lower:
                dest = Path("Personal") / "Vivienda" / city / path.name
                return dest, f"Personal/Vivienda/{city}", f"keyword:home:{city}", 0.85

        # Check personal sub-categories (most specific first)
        for key, keywords in PERSONAL_SUBCATEGORIES.items():
            for kw in keywords:
                if kw in name_lower:
                    dest = Path("Personal") / Path(key) / path.name
                    return dest, f"Personal/{key}", f"keyword:personal:{kw}", 0.9

        # Check personal top categories
        for alias, cat in self._personal_lower.items():
            if alias in name_lower:
                dest = Path("Personal") / cat / path.name
                return dest, f"Personal/{cat}", f"keyword:personal_cat:{alias}", 0.75

        # Check trabajo keywords
        for kw in TRABAJO_KEYWORDS:
            if kw in name_lower:
                subdir = _doc_type_subdir(path)
                dest = Path("Trabajo") / "_SinClasificar" / subdir / path.name
                return dest, f"Trabajo/{subdir}", f"keyword:trabajo:{kw}", 0.7

        return None

    # ── Signal 3: Extension ───────────────────────────────────────────────────

    def _by_extension(self, path: Path) -> Optional[tuple[Path, str, str, float]]:
        ext = path.suffix.lower()

        if ext in EXTENSION_PERSONAL_MAP:
            subcat = EXTENSION_PERSONAL_MAP[ext]
            dest = Path("Personal") / subcat / path.name
            return dest, f"Personal/{subcat}", f"extension:{ext}", 0.9

        if ext in EXTENSION_TRABAJO_MAP:
            dest = Path("Trabajo") / "_SinClasificar" / "Recursos" / path.name
            return dest, "Trabajo/Recursos", f"extension:{ext}", 0.8

        if ext in IMAGE_EXTENSIONS:
            dest = Path("Personal") / "Fotos" / path.name
            return dest, "Personal/Fotos", f"extension:{ext}", 0.65

        if ext in VIDEO_EXTENSIONS:
            dest = Path("Personal") / "Fotos" / path.name
            return dest, "Personal/Fotos", f"extension:{ext}", 0.55

        return None

    # ── Signal 4: Content scan ────────────────────────────────────────────────

    def _by_content(self, path: Path) -> Optional[tuple[Path, str, str, float]]:
        if not path.is_file():
            return None

        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.max_content_scan_mb:
            return None

        text = _read_text_snippet(path)
        if not text:
            return None

        text_lower = _normalize(text)

        # Company names in content → Trabajo
        for comp_lower, comp_name in self._company_lower.items():
            if comp_lower in text_lower:
                subdir = _doc_type_subdir(path)
                dest = Path("Trabajo") / comp_name / "_SinCliente" / subdir / path.name
                return dest, f"Trabajo/{subdir}", f"content:company:{comp_name}", 0.75

        # Personal sub-categories (most specific first)
        for key, keywords in PERSONAL_SUBCATEGORIES.items():
            for kw in keywords:
                if kw in text_lower:
                    dest = Path("Personal") / key / path.name
                    return dest, f"Personal/{key}", f"content:{kw}", 0.8

        # Trabajo keywords in content
        for kw in TRABAJO_KEYWORDS:
            if kw in text_lower:
                subdir = _doc_type_subdir(path)
                dest = Path("Trabajo") / "_SinClasificar" / subdir / path.name
                return dest, f"Trabajo/{subdir}", f"content:{kw}", 0.65

        return None

    # ── Folder name signal ────────────────────────────────────────────────────

    def _by_name_for_folder(self, path: Path) -> Optional[tuple[Path, str, str, float]]:
        name_lower = _normalize(path.name)

        for comp_lower, comp_name in self._company_lower.items():
            if comp_lower in name_lower:
                dest = Path("Trabajo") / comp_name
                return dest, "Trabajo", f"folder_name:company:{comp_name}", 0.9

        for alias, cat in self._personal_lower.items():
            if alias in name_lower:
                dest = Path("Personal") / cat
                return dest, f"Personal/{cat}", f"folder_name:personal:{alias}", 0.8

        for kw in TRABAJO_KEYWORDS:
            if kw in name_lower:
                dest = Path("Trabajo") / "_SinClasificar"
                return dest, "Trabajo", f"folder_name:trabajo:{kw}", 0.6

        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, remove accents, replace separators with space, collapse whitespace."""
    text = text.lower()
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ü": "u", "ñ": "n", "ç": "c",
    }
    for src, tgt in replacements.items():
        text = text.replace(src, tgt)
    # Treat underscores, hyphens and dots as spaces so "boarding_pass" matches "boarding pass"
    text = re.sub(r"[_\-\.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _doc_type_subdir(path: Path) -> str:
    """Map a file to a project sub-directory based on its name."""
    name_lower = _normalize(path.name)
    for kw, subdir in PROYECTO_KEYWORD_MAP.items():
        if kw in name_lower:
            return subdir
    return "Recursos"


def _iter_files_shallow(folder: Path, max_files: int = 50):
    """Yield up to max_files regular files from folder (non-recursive)."""
    count = 0
    try:
        for p in folder.iterdir():
            if p.is_file() and not p.name.startswith("."):
                yield p
                count += 1
                if count >= max_files:
                    return
    except PermissionError:
        return


def _read_text_snippet(path: Path, max_chars: int = 2000) -> Optional[str]:
    """Try to read a text snippet from a file for keyword scanning."""
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _read_pdf(path, max_chars)

    if ext in DOCUMENT_EXTENSIONS:
        return _read_plain(path, max_chars)

    # Try reading as plain text (UTF-8 fallback)
    return _read_plain(path, max_chars)


def _read_plain(path: Path, max_chars: int) -> Optional[str]:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read(max_chars)
    except Exception:
        return None


def _read_pdf(path: Path, max_chars: int) -> Optional[str]:
    try:
        import fitz  # type: ignore  # pymupdf
        doc = fitz.open(str(path))
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) >= max_chars:
                break
        doc.close()
        return text[:max_chars]
    except Exception:
        return None
