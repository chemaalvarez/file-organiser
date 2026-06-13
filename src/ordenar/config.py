"""Configuration loader — reads config.yaml and merges with defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class AIConfig(BaseModel):
    enabled: bool = False
    provider: str = "ollama"
    model: str = "llama3.2"
    max_tokens: int = 200


class ExtraKeywords(BaseModel):
    trabajo: list[str] = Field(default_factory=list)
    personal_gastos: list[str] = Field(default_factory=list)
    personal_salud: list[str] = Field(default_factory=list)
    personal_vivienda: list[str] = Field(default_factory=list)
    personal_documentos: list[str] = Field(default_factory=list)


class OrganizerConfig(BaseModel):
    root: str = "~/Downloads"
    confidence_threshold: float = 0.85
    on_duplicate: str = "rename"         # skip | rename | overwrite
    max_content_scan_mb: int = 100
    max_depth: int = 0
    ai: AIConfig = Field(default_factory=AIConfig)
    companies: list[str] = Field(default_factory=list)
    family_members: list[str] = Field(default_factory=list)
    known_cars: list[str] = Field(default_factory=list)
    known_homes: dict[str, list[str]] = Field(default_factory=dict)
    extra_keywords: ExtraKeywords = Field(default_factory=ExtraKeywords)
    ignore_patterns: list[str] = Field(default_factory=lambda: [
        ".DS_Store", "Thumbs.db", ".localized", "desktop.ini",
        "*.tmp", "*.part", ".git", ".ordenar",
    ])

    # YAML emits `null` for empty list fields (e.g. `companies:` with no items)
    @field_validator(
        "companies", "family_members", "known_cars", "ignore_patterns",
        mode="before",
    )
    @classmethod
    def _coerce_none_to_list(cls, v):
        return v if v is not None else []

    @field_validator("known_homes", mode="before")
    @classmethod
    def _coerce_none_to_dict(cls, v):
        return v if v is not None else {}

    @property
    def root_path(self) -> Path:
        return Path(self.root).expanduser().resolve()


_DEFAULT_CONFIG_NAMES = ["config.yaml", "config.yml", ".ordenar.yaml"]


def _find_config(root: Optional[Path] = None) -> Optional[Path]:
    """Search for a config file next to the tool or in the root folder."""
    search_dirs: list[Path] = []
    if root:
        search_dirs.append(root)
    # Directory where this file lives (package dir) → project root
    pkg_dir = Path(__file__).parent
    search_dirs += [pkg_dir.parent.parent, pkg_dir.parent]

    for directory in search_dirs:
        for name in _DEFAULT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def load_config(config_path: Optional[Path] = None, root: Optional[Path] = None) -> OrganizerConfig:
    """Load configuration from YAML file, falling back to defaults."""
    path = config_path or _find_config(root)

    if path and path.is_file():
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return OrganizerConfig.model_validate(data)

    return OrganizerConfig()
