"""Extract: download an RSS feed and turn it into plain dicts."""

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dznews import config


def _session() -> requests.Session:
    """HTTP session that retries transient errors (the DAG adds a second retry layer)."""
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = config.USER_AGENT
    return session


def fetch_feed(url: str) -> bytes:
    """Return the raw bytes of a feed. Raises on HTTP errors so the task can retry."""
    response = _session().get(url, timeout=config.HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.content


def parse_feed(content: bytes) -> list[dict]:
    """Parse RSS/Atom bytes into raw records (strings only, nothing cleaned yet)."""
    parsed = feedparser.parse(content)
    records = []
    for entry in parsed.entries:
        tags = entry.get("tags") or []
        full_text = entry.get("content") or []  # <content:encoded>: full text, when published
        records.append(
            {
                "title": entry.get("title"),
                "link": entry.get("link"),
                "summary": entry.get("summary") or entry.get("description"),
                "content": full_text[0].get("value") if full_text else None,
                "categories": [t.get("term") for t in tags if t.get("term")],
                # Keep the *string*: some feeds use non-standard date formats that
                # feedparser cannot parse, and we handle those ourselves in transform.py.
                "published_raw": entry.get("published") or entry.get("updated"),
                "author": entry.get("author"),
                "category_raw": tags[0].get("term") if tags else None,
            }
        )
    return records
