"""Extract: download an RSS feed and turn it into plain dicts."""

import re

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


_IMG_SRC_RE = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def find_image(entry) -> str | None:
    """The article's lead image, in the order outlets tend to publish it.

    WordPress media plugins use <media:content>, some feeds an image <enclosure>, and the
    rest embed the picture as the first <img> of the full text or the summary.
    """
    for media in (entry.get("media_content") or []) + (entry.get("media_thumbnail") or []):
        url = media.get("url")
        if url and (media.get("medium") in (None, "image") or "image" in (media.get("type") or "")):
            return url
    for link in entry.get("links") or []:
        if link.get("rel") == "enclosure" and (link.get("type") or "").startswith("image"):
            return link.get("href")
    for block in [*(c.get("value", "") for c in entry.get("content") or []), entry.get("summary", "")]:
        match = _IMG_SRC_RE.search(block or "")
        if match:
            return match.group(1)
    return None


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
                "image_url": find_image(entry),
                # Keep the *string*: some feeds use non-standard date formats that
                # feedparser cannot parse, and we handle those ourselves in transform.py.
                "published_raw": entry.get("published") or entry.get("updated"),
                "author": entry.get("author"),
                "category_raw": tags[0].get("term") if tags else None,
            }
        )
    return records
