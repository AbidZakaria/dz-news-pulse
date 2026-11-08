from datetime import UTC, datetime

import pytest

from dznews import config, extract, transform
from dznews.sources import Source

SOURCE = Source("test_fr", "Test FR", "fr", "general", "https://example.dz", "https://example.dz/feed")
NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def frame(fixture: str):
    records = extract.parse_feed((config.SAMPLE_DIR / fixture).read_bytes())
    return transform.build_articles_frame(records, SOURCE, "batch-1", NOW)


def test_clean_text_strips_html_entities_and_wordpress_footer():
    raw = "<p>Hello&nbsp;&amp; <b>world</b></p><p>The post X appeared first on Y.</p>"
    assert transform.clean_text(raw) == "Hello & world"


def test_clean_text_strips_french_wordpress_footer():
    raw = (
        "<p>Le match a lieu samedi.</p>"
        "<p>L’article Derby est apparu en premier sur Algérie360.</p>"
    )
    assert transform.clean_text(raw) == "Le match a lieu samedi."


def test_clean_text_returns_none_for_empty_content():
    assert transform.clean_text("  <p> </p> ") is None
    assert transform.clean_text(None) is None


def test_clean_text_truncates():
    assert len(transform.clean_text("word " * 500, max_len=100)) <= 100


def test_canonical_url_drops_tracking_params_fragment_and_trailing_slash():
    a = transform.canonical_url("HTTPS://Example.dz/a/b/?utm_source=rss&id=7#top")
    b = transform.canonical_url("https://example.dz/a/b?id=7")
    assert a == b == "https://example.dz/a/b?id=7"


def test_article_id_is_stable_and_ignores_tracking():
    one = transform.make_article_id("https://example.dz/x/?utm_medium=link")
    two = transform.make_article_id("https://example.dz/x")
    assert one == two and len(one) == 16


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Sun, 08 Nov 2026 19:00:19 +0000", datetime(2026, 11, 8, 19, 0, 19, tzinfo=UTC)),
        ("Sun, 08 Nov 2026 20:00:19 +0100", datetime(2026, 11, 8, 19, 0, 19, tzinfo=UTC)),
        ("2026-11-08T19:00:19Z", datetime(2026, 11, 8, 19, 0, 19, tzinfo=UTC)),
        # El Khabar format, Algiers time (UTC+1) -> converted to UTC
        ("20:07 | 08-11-2026", datetime(2026, 11, 8, 19, 7, tzinfo=UTC)),
    ],
)
def test_parse_published_formats(raw, expected):
    assert transform.parse_published(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "not a date at all", "99:99 | 99-99-9999"])
def test_parse_published_returns_none_for_garbage(raw):
    assert transform.parse_published(raw) is None


def test_french_fixture_is_validated_and_deduplicated():
    df, rejected = frame("sample_fr.xml")
    # 10 items: 1 without title (rejected) + 1 duplicate URL (rejected) -> 8 kept
    assert len(df) == 8
    assert rejected == 2
    assert df["article_id"].is_unique
    assert list(df.columns) == transform.COLUMNS
    assert (df["language"] == "fr").all()
    assert not df["summary"].astype(str).str.contains("<").any()


def test_arabic_text_survives_cleaning():
    df, _ = frame("sample_ar.xml")
    assert len(df) == 8
    assert df["title"].str.contains("الحكومة").any()


def test_unparseable_dates_become_null_not_errors():
    df, _ = frame("sample_elkhabar.xml")
    assert len(df) == 3
    assert df["published_at"].isna().sum() == 1  # the "not a date at all" item
    assert df["published_at"].notna().sum() == 2


def test_empty_feed_gives_empty_frame():
    df, rejected = transform.build_articles_frame([], SOURCE, "b", NOW)
    assert df.empty and rejected == 0
    assert list(df.columns) == transform.COLUMNS
