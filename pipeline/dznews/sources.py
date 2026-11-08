"""The list of news sources.

The CSV is a dbt seed too, so Python and the warehouse share ONE definition of
what a "source" is (name, language, focus) - no copy-pasted constants.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from dznews import config


@dataclass(frozen=True)
class Source:
    source_id: str
    source_name: str
    language: str
    focus: str
    website: str
    feed_url: str


def load_sources(path: Path | None = None) -> list[Source]:
    with open(path or config.SOURCES_CSV, newline="", encoding="utf-8") as fh:
        return [Source(**row) for row in csv.DictReader(fh)]


def get_source(source_id: str) -> Source:
    for source in load_sources():
        if source.source_id == source_id:
            return source
    raise KeyError(f"Unknown source_id: {source_id!r}")
