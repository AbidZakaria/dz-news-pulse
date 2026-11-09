"""Tunable parameters, loaded from config/intelligence.yml (defaults live here)."""

from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path

import yaml

from dznews import config


@dataclass(frozen=True)
class ClusterSettings:
    window_hours: float = 72
    threshold_same_language: float = 0.76
    threshold_cross_language: float = 0.71
    link_weight: float = 1.0
    shared_term_bonus: float = 0.02
    merge_threshold: float = 0.90
    duplicate_similarity: float = 0.97
    duplicate_title_overlap: float = 0.85
    high_confidence_margin: float = 0.06


def load_cluster_settings(path: Path | None = None) -> ClusterSettings:
    path = path or config.INTEL_CONFIG
    if not path.exists():
        return ClusterSettings()
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("clustering", {})
    known = {f.name for f in fields(ClusterSettings)}
    unknown = set(raw) - known
    if unknown:
        raise ValueError(f"Unknown clustering setting(s) in {path}: {sorted(unknown)}")
    return ClusterSettings(**raw)


@lru_cache(maxsize=1)
def cluster_settings() -> ClusterSettings:
    return load_cluster_settings()
