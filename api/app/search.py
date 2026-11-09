"""Turn a search box query into match terms.

Mirrors the warehouse normalisation (dbt/macros/normalize.sql and dznews.text), so that
"economie" finds "Économie" and "الجزائر" finds "الجزائرية". Terms are matched as
substrings, so the light stemming below only ever widens a match.
"""

import re
import unicodedata

_ARABIC_MARKS_RE = re.compile("[ً-ْـ]")
_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)
_ARABIC_FOLD = str.maketrans("أإآىة", "ااايه")
MAX_TERMS = 6


def _strip_accent(ch: str) -> str:
    # Only Latin letters lose their accents. Decomposing Arabic would also turn hamza
    # letters (ئ, ؤ) into bare ones, which the SQL side does not do.
    if ord(ch) >= 0x0250:
        return ch
    return "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))


def normalize(text: str) -> str:
    text = _ARABIC_MARKS_RE.sub("", text.lower().translate(_ARABIC_FOLD))
    return "".join(_strip_accent(ch) for ch in text)


def _stem(term: str) -> str:
    if term.startswith("ال") and len(term) - 2 >= 3:  # Arabic definite article
        return term[2:]
    if term.isascii() and len(term) > 4 and term.endswith("s"):  # French/English plural
        return term[:-1]
    return term


def search_terms(query: str) -> list[str]:
    """Distinct terms of at least 2 characters, in order, capped at MAX_TERMS."""
    seen: dict[str, None] = {}
    for raw in _SPLIT_RE.split(normalize(query)):
        term = _stem(raw.strip("_"))
        if len(term) >= 2:
            seen.setdefault(term)
    return list(seen)[:MAX_TERMS]


def like_escape(term: str) -> str:
    """Neutralise LIKE wildcards typed by the user."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
