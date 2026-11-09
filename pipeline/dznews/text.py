"""Language-aware text helpers (French / Arabic / English), dependency-free.

The normalisation mirrors dbt/macros/normalize.sql so Python and SQL agree on what a
"word" is. Stop-words come from the same CSV the dbt models use.
"""

import csv
import re
import unicodedata
from functools import lru_cache

from dznews import config

_ARABIC_MARKS_RE = re.compile("[ً-ْـ]")  # harakat + tatweel
_ARABIC_LETTER_RE = re.compile("[ء-ي]")
_LATIN_LETTER_RE = re.compile("[a-zA-ZÀ-ÿ]")
_TOKEN_SPLIT_RE = re.compile("[^a-z0-9ء-ي]+")
_ARABIC_FOLD = str.maketrans("أإآىة", "ااايه")

# Small closed lists are enough to tell French from English on news text.
_FR_HINTS = {"le", "la", "les", "des", "du", "une", "est", "pour", "dans", "sur", "que", "qui",
             "au", "aux", "et", "en", "par", "avec", "ses", "plus", "pas", "ont", "cette"}
_EN_HINTS = {"the", "of", "and", "to", "in", "is", "for", "on", "with", "as", "by", "at",
             "from", "that", "this", "are", "will", "was", "has", "set"}


def strip_arabic_marks(text: str) -> str:
    return _ARABIC_MARKS_RE.sub("", text)


def normalize_text(text: str) -> str:
    """Lower-case, drop French accents, fold Arabic letter variants, remove diacritics."""
    text = strip_arabic_marks(text.lower().translate(_ARABIC_FOLD))
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_token(token: str, language: str) -> str:
    """Light stemming: drop Arabic "al-", drop a French plural "s"."""
    if language == "ar" and token.startswith("ال") and len(token) - 2 >= 3:
        return token[2:]
    if language == "fr" and len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token


def detect_language(text: str) -> str:
    """Return 'ar', 'fr' or 'en' from the text itself (feeds sometimes mix languages)."""
    sample = text[:1500]
    arabic = len(_ARABIC_LETTER_RE.findall(sample))
    latin = len(_LATIN_LETTER_RE.findall(sample))
    if arabic + latin == 0:
        return "fr"
    if arabic >= latin:
        return "ar"
    words = set(re.findall(r"[a-z]+", sample.lower()))
    return "en" if len(words & _EN_HINTS) > len(words & _FR_HINTS) else "fr"


@lru_cache(maxsize=1)
def _stopwords() -> dict[str, frozenset[str]]:
    words: dict[str, set[str]] = {"fr": set(), "ar": set(), "en": set()}
    path = config.STOPWORDS_CSV
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                lang = row["language"]
                words.setdefault(lang, set()).add(
                    normalize_token(normalize_text(row["word"]), lang)
                )
    words["en"] |= _EN_HINTS
    return {lang: frozenset(ws) for lang, ws in words.items()}


def key_terms(text: str, language: str, min_len: int = 4) -> set[str]:
    """Distinctive normalised words of a text (no stop-words), used as a secondary signal."""
    stop = _stopwords().get(language, frozenset())
    terms = set()
    for raw in _TOKEN_SPLIT_RE.split(normalize_text(text)):
        token = normalize_token(raw, language)
        if len(token) >= min_len and not token.isdigit() and token not in stop:
            terms.add(token)
    return terms


def embedding_text(title: str, summary: str | None, content: str | None, max_chars: int = 500) -> str:
    """What gets embedded: the headline plus the opening of the best available body text.

    Models only read their first ~128 tokens anyway, so the opening is what matters.
    """
    body = (content or summary or "").strip()
    return strip_arabic_marks(f"{title.strip()}. {body[:max_chars]}").strip()
