"""API tests run without a database: the SQL layer is replaced by a fake."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from psycopg2 import errors

from app import main

client = TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def fake_query(monkeypatch):
    calls = []

    def fake(sql, params=None):
        calls.append((sql, params))
        return fake.rows

    fake.rows = []
    fake.calls = calls
    monkeypatch.setattr(main, "query", fake)
    return fake


def test_health_does_not_need_the_database():
    assert client.get("/health").json() == {"status": "ok"}


def test_dashboard_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "DZ News Pulse" in response.text


def test_topics_passes_filters_to_sql(fake_query):
    fake_query.rows = [{"topic": "Sports", "articles": 3, "share_pct": 100.0}]
    response = client.get("/topics?days=14&language=ar")
    assert response.status_code == 200
    assert response.json() == fake_query.rows
    assert fake_query.calls[0][1] == {"days": 14, "language": "ar"}


def test_overview_returns_first_row(fake_query):
    fake_query.rows = [{"total_articles": 42}]
    assert client.get("/overview").json() == {"total_articles": 42}


@pytest.mark.parametrize(
    "url",
    ["/topics?days=0", "/topics?days=500", "/topics?language=en", "/keywords/trending?limit=0",
     "/articles?q=a", "/articles?limit=1000"],
)
def test_invalid_parameters_are_rejected(fake_query, url):
    assert client.get(url).status_code == 422
    assert fake_query.calls == []


def test_articles_defaults(fake_query):
    client.get("/articles")
    assert fake_query.calls[0][1] == {
        "days": 7, "topic": None, "source": None, "language": None, "q": None, "limit": 25,
    }


def test_missing_tables_give_a_helpful_503(monkeypatch):
    def boom(*_args, **_kwargs):
        raise errors.UndefinedTable("relation marts.fact_articles does not exist")

    monkeypatch.setattr(main, "query", boom)
    response = client.get("/overview")
    assert response.status_code == 503
    assert "dz_news_pulse" in response.json()["detail"]


def test_overview_merges_warehouse_story_and_collection_totals(monkeypatch):
    answers = iter([
        [{"total_articles": 10}],
        [{"stories": 4, "multi_source_stories": 1}],
        [{"last_run_at": "2026-11-09T18:00:00+00:00", "sources_failing": 0}],
    ])
    monkeypatch.setattr(main, "query", lambda *_a, **_k: next(answers))
    assert client.get("/overview").json() == {
        "total_articles": 10, "stories": 4, "multi_source_stories": 1,
        "last_run_at": "2026-11-09T18:00:00+00:00", "sources_failing": 0,
    }


def test_stories_filters_are_passed_through(fake_query):
    client.get("/stories?days=3&hours=24&on=2026-11-09&min_sources=2&topic=economy&language=ar"
               "&sort=recent&limit=5")
    assert fake_query.calls[0][1] == {
        "days": 3, "hours": 24, "date": date(2026, 11, 9), "min_sources": 2, "min_articles": 1,
        "topic": "economy", "language": "ar", "sort": "recent", "limit": 5,
    }


@pytest.mark.parametrize("url", ["/stories?sort=popular", "/stories?hours=0", "/stories?on=yesterday",
                                 "/activity?window=1y", "/search?q=a", "/search"])
def test_new_endpoints_reject_bad_parameters(fake_query, url):
    assert client.get(url).status_code == 422
    assert fake_query.calls == []


def test_activity_uses_hourly_or_daily_buckets(fake_query):
    fake_query.rows = [{"bucket": "2026-11-09", "fr": 1, "ar": 2}]
    hourly = client.get("/activity").json()
    daily = client.get("/activity?window=30d").json()
    assert hourly["unit"] == "hour" and daily["unit"] == "day"
    assert fake_query.calls[0][0] == main.queries.ACTIVITY_HOURLY
    assert fake_query.calls[1] == (main.queries.ACTIVITY_DAILY, {"days": 30})


def test_briefing_defaults_to_the_newest_day(monkeypatch):
    calls = []

    def fake(sql, params=None):
        calls.append((sql, params))
        if sql == main.queries.BRIEFING_DAYS:
            return [{"day": date(2026, 11, 9), "articles": 5}, {"day": date(2026, 11, 8), "articles": 3}]
        if sql == main.queries.BRIEFING_DAY:
            return [{"articles": 5, "sources": 2, "fr": 2, "ar": 3}]
        return []

    monkeypatch.setattr(main, "query", fake)
    body = client.get("/briefing").json()
    assert body["date"] == "2026-11-09" and body["articles"] == 5
    story_call = next(p for s, p in calls if s == main.queries.STORIES)
    assert story_call["date"] == date(2026, 11, 9) and story_call["min_sources"] == 2


def test_briefing_without_data_is_a_404(fake_query):
    assert client.get("/briefing").status_code == 404


def test_unknown_topic_is_a_404(fake_query):
    assert client.get("/topics/astrology").status_code == 404


def test_search_normalises_terms_and_strips_the_total_column(fake_query):
    fake_query.rows = [{"article_id": "a", "title": "x", "total": 7}]
    body = client.get("/search?q=Économie%20les%20exportations").json()
    sql, params = fake_query.calls[0]
    assert params["terms"] == ["economie", "les", "exportation"]
    assert body["total"] == 7 and body["results"] == [{"article_id": "a", "title": "x"}]


def test_search_with_only_punctuation_does_not_hit_the_database(fake_query):
    assert client.get("/search?q=%21%21").json()["total"] == 0
    assert fake_query.calls == []


def test_dashboard_files_are_served_and_always_revalidated():
    for path in ["/", "/static/js/app.js", "/static/css/app.css"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["cache-control"] == "no-cache"


def test_story_detail_includes_articles(monkeypatch):
    answers = iter([[{"story_id": 7, "headline": "h"}], [{"article_id": "a1", "published_first": True}]])
    monkeypatch.setattr(main, "query", lambda *_a, **_k: next(answers))
    body = client.get("/stories/7").json()
    assert body["story_id"] == 7 and body["articles"][0]["article_id"] == "a1"


def test_unknown_story_is_a_404(fake_query):
    fake_query.rows = []
    assert client.get("/stories/999").status_code == 404
