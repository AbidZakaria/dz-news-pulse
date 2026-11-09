"""Transform: clean raw feed records into a validated pandas DataFrame.

Only *technical* cleaning happens here (HTML, whitespace, dates, ids, duplicates).
Business logic - topics, keywords, star schema - lives in dbt, as SQL.
"""

import hashlib
import html
import re
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from dznews.sources import Source

COLUMNS = [
    "article_id",
    "source_id",
    "url",
    "title",
    "summary",
    "published_at",
    "published_raw",
    "author",
    "category_raw",
    "content",
    "categories",
    "language",
    "fetched_at",
    "batch_id",
]

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
# WordPress feeds append a footer to every summary:
#   EN "The post ... appeared first on ..."   FR "L'article ... est apparu en premier sur ..."
_WP_FOOTER_RE = re.compile(
    r"(The post .*? appeared first on .*|L['’]article .*? est apparu en premier sur .*)$",
    re.IGNORECASE | re.DOTALL,
)
# El Khabar publishes dates as "20:07 | 08-11-2026" instead of RFC 822.
_ELKHABAR_DATE_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*\|\s*(\d{1,2})-(\d{1,2})-(\d{4})\s*$")
_ALGIERS_TZ = timezone(timedelta(hours=1))  # Algeria: UTC+1 all year, no DST
_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid"}
_MAX_SUMMARY_CHARS = 1000
_MAX_CONTENT_CHARS = 20000


def clean_text(value: str | None, max_len: int | None = None) -> str | None:
    """Strip HTML tags/entities and collapse whitespace. Returns None for empty text."""
    if not value:
        return None
    text = _WP_FOOTER_RE.sub("", value)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text).strip()
    if not text:
        return None
    return text[:max_len].rstrip() if max_len else text


def _clean_categories(value) -> list[str] | None:
    """Tags as a de-duplicated list of clean strings (None when there are none)."""
    if not isinstance(value, list):
        return None
    seen: dict[str, None] = {}
    for tag in value:
        cleaned = clean_text(tag, 80)
        if cleaned:
            seen.setdefault(cleaned)
    return list(seen) or None


def canonical_url(url: str) -> str:
    """Normalise a URL so the same article always gets the same id."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _TRACKING_PARAMS]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def make_article_id(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def parse_published(raw: str | None) -> datetime | None:
    """Parse the date formats seen in the wild. Returns an aware UTC datetime or None."""
    if not raw:
        return None
    raw = raw.strip()

    match = _ELKHABAR_DATE_RE.match(raw)
    if match:
        hour, minute, day, month, year = map(int, match.groups())
        try:
            return datetime(year, month, day, hour, minute, tzinfo=_ALGIERS_TZ).astimezone(UTC)
        except ValueError:
            return None

    parsed = None
    try:
        parsed = parsedate_to_datetime(raw)  # RFC 822, used by most RSS feeds
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))  # Atom / ISO 8601
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build_articles_frame(
    records: list[dict], source: Source, batch_id: str, fetched_at: datetime
) -> tuple[pd.DataFrame, int]:
    """Clean + validate records. Returns (articles, number_of_rejected_records)."""
    if not records:
        return pd.DataFrame(columns=COLUMNS), 0

    df = pd.DataFrame(records)
    df["title"] = df["title"].map(clean_text)
    df["summary"] = df["summary"].map(lambda v: clean_text(v, _MAX_SUMMARY_CHARS))
    if "content" not in df:
        df["content"] = None
    if "categories" not in df:
        df["categories"] = None
    df["content"] = df["content"].map(lambda v: clean_text(v, _MAX_CONTENT_CHARS))
    df["categories"] = df["categories"].map(_clean_categories)
    df["url"] = df["link"].map(lambda v: canonical_url(v) if isinstance(v, str) and v else None)

    # Validation: an article without a title or a link is useless -> reject.
    valid = df["title"].notna() & df["url"].notna()
    rejected = int((~valid).sum())
    df = df[valid].copy()

    df["article_id"] = df["url"].map(make_article_id)
    before = len(df)
    df = df.drop_duplicates(subset="article_id", keep="first")
    rejected += before - len(df)  # duplicates inside one feed count as rejected too

    df["published_at"] = df["published_raw"].map(parse_published)
    df["source_id"] = source.source_id
    df["language"] = source.language
    df["fetched_at"] = fetched_at
    df["batch_id"] = batch_id
    return df[COLUMNS].reset_index(drop=True), rejected
