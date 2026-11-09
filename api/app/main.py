"""DZ News Pulse API - serves the dbt marts (stories, topics, keywords, articles) over HTTP,
plus the dashboard that reads them."""

import logging
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import psycopg2
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg2 import errors

from app import queries
from app.db import query
from app.search import like_escape, search_terms

STATIC_DIR = Path(__file__).parent / "static"
log = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="DZ News Pulse API",
    description=(
        "What is Algerian news talking about? Stories, topics, trending keywords and headlines, "
        "aggregated from French and Arabic news sites by an Airflow + dbt pipeline."
    ),
    version="1.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def _revalidate_dashboard_files(request: Request, call_next):
    """The dashboard's files change with each release: let browsers cache them but always
    revalidate (cheap, ETag-based), so nobody runs a mix of old and new modules."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response

Days = Annotated[int, Query(ge=1, le=90, description="Look-back window, in days.")]
Language = Annotated[Literal["fr", "ar"] | None, Query(description="Filter by article language.")]
TopicId = Annotated[str | None, Query(max_length=40, description="Topic id, e.g. 'economy'.")]


@app.exception_handler(errors.UndefinedTable)
@app.exception_handler(errors.UndefinedColumn)
async def _warehouse_not_built(request: Request, exc: Exception):
    log.warning("Warehouse object missing for %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "The warehouse is not built yet - run the 'dz_news_pulse' DAG in Airflow."
        },
    )


@app.exception_handler(psycopg2.OperationalError)
async def _warehouse_down(_: Request, __: Exception):
    return JSONResponse(status_code=503, content={"detail": "Cannot reach the warehouse database."})


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["meta"])
def health():
    """Liveness probe (does not touch the database)."""
    return {"status": "ok"}


@app.get("/overview", tags=["analytics"])
def overview():
    """Headline numbers for the whole warehouse, plus when the pipeline last collected."""
    totals = query(queries.OVERVIEW)
    return {
        **(totals[0] if totals else {"total_articles": 0}),
        **query(queries.STORY_TOTALS)[0],
        **query(queries.COLLECTION)[0],
    }


@app.get("/activity", tags=["analytics"])
def activity(window: Annotated[Literal["24h", "7d", "30d"], Query()] = "24h"):
    """Articles published per hour (24h) or per day (7d, 30d), split by language.

    Days before collection started are null ("not collected"), not zero.
    """
    if window == "24h":
        rows = query(queries.ACTIVITY_HOURLY)
    else:
        rows = query(queries.ACTIVITY_DAILY, {"days": 7 if window == "7d" else 30})
    return {"window": window, "unit": "hour" if window == "24h" else "day", "buckets": rows}


@app.get("/stories", tags=["stories"])
def stories(
    days: Days = 7,
    hours: Annotated[int | None, Query(ge=1, le=168, description="Only stories with an article "
                                       "in the last N hours (applied on top of days).")] = None,
    on: Annotated[date | None, Query(description="Only stories with an article on this day.")] = None,
    min_sources: Annotated[int, Query(ge=1, description="Minimum independent outlets.")] = 1,
    min_articles: Annotated[int, Query(ge=1)] = 1,
    topic: TopicId = None,
    language: Language = None,
    sort: Annotated[Literal["coverage", "recent"], Query()] = "coverage",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """News stories: groups of articles about the same event, widest coverage first."""
    return query(
        queries.STORIES,
        {"days": days, "hours": hours, "date": on, "min_sources": min_sources,
         "min_articles": min_articles, "topic": topic, "language": language,
         "sort": sort, "limit": limit},
    )


@app.get("/stories/{story_id}", tags=["stories"])
def story(story_id: int):
    """One story with every article that covers it (who published first, how they differ)."""
    found = query(queries.STORY, {"story_id": story_id})
    if not found:
        raise HTTPException(status_code=404, detail="Story not found")
    return {**found[0], "articles": query(queries.STORY_ARTICLES, {"story_id": story_id})}


@app.get("/briefing", tags=["stories"])
def briefing(
    on: Annotated[date | None, Query(alias="date", description="Day (Algiers time); "
                                     "defaults to the newest day with articles.")] = None,
):
    """The day in brief: its most widely covered stories, its main topics, and notable
    single-outlet reports. Everything is extracted from the articles; nothing is generated."""
    days = query(queries.BRIEFING_DAYS)
    if not days:
        raise HTTPException(status_code=404, detail="No articles collected yet")
    day = on or days[0]["day"]
    params = {"date": day}
    story_params = {
        "days": 90, "hours": None, "date": day, "min_sources": 2, "min_articles": 2,
        "topic": None, "language": None, "sort": "coverage", "limit": 8,
    }
    return {
        "date": day,
        "days": days,
        **query(queries.BRIEFING_DAY, params)[0],
        "topics": query(queries.BRIEFING_TOPICS, params),
        "stories": query(queries.STORIES, story_params),
        "also": query(queries.BRIEFING_SINGLES, {**params, "limit": 8}),
    }


@app.get("/topics", tags=["analytics"])
def topics(days: Days = 7, language: Language = None):
    """How much each topic is covered over the last N days, with a daily series and the
    previous period (null until the previous period has been fully collected)."""
    return query(queries.TOPICS, {"days": days, "language": language})


@app.get("/topics/{topic_id}", tags=["analytics"])
def topic(topic_id: str, days: Days = 14):
    """One topic: daily coverage by language, its keywords and which outlets cover it."""
    params = {"topic": topic_id, "days": days}
    found = query(queries.TOPIC, params)
    if not found:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {
        **found[0],
        "days": days,
        "daily": query(queries.TOPIC_DAILY, params),
        "keywords": query(queries.TOPIC_KEYWORDS, params),
        "sources": query(queries.TOPIC_SOURCES, params),
    }


@app.get("/keywords/trending", tags=["analytics"])
def trending_keywords(
    days: Days = 3,
    language: Language = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    min_mentions: Annotated[int, Query(ge=1)] = 2,
):
    """The words that appear in the most articles over the last N days."""
    return query(
        queries.KEYWORDS,
        {"days": days, "language": language, "limit": limit, "min_mentions": min_mentions},
    )


@app.get("/articles", tags=["analytics"])
def articles(
    days: Days = 7,
    topic: TopicId = None,
    source: Annotated[str | None, Query(description="Source id, e.g. 'echorouk'.")] = None,
    language: Language = None,
    q: Annotated[str | None, Query(min_length=2, description="Search in titles.")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
):
    """Latest headlines with their detected topic."""
    return query(
        queries.ARTICLES,
        {
            "days": days, "topic": topic, "source": source,
            "language": language, "q": q, "limit": limit,
        },
    )


@app.get("/search", tags=["analytics"])
def search(
    q: Annotated[str, Query(min_length=2, max_length=120, description="Words to find.")],
    days: Annotated[int, Query(ge=1, le=365)] = 90,
    language: Language = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
):
    """Find articles whose title or summary contains every word, in French or Arabic.

    Accents, Arabic letter variants and diacritics are ignored; title matches rank first.
    """
    terms = search_terms(q)
    if not terms:
        return {"query": q, "terms": [], "total": 0, "results": []}
    rows = query(
        queries.SEARCH,
        {"terms": [like_escape(t) for t in terms], "days": days, "language": language,
         "limit": limit},
    )
    total = rows[0]["total"] if rows else 0
    return {
        "query": q,
        "terms": terms,
        "total": total,
        "results": [{k: v for k, v in r.items() if k != "total"} for r in rows],
    }


@app.get("/sources", tags=["pipeline"])
def sources():
    """Each outlet: articles, shared stories, main topics and its latest collection run."""
    return query(queries.SOURCES)


@app.get("/pipeline/runs", tags=["pipeline"])
def pipeline_runs(limit: Annotated[int, Query(ge=1, le=200)] = 20):
    """Recent ingestion attempts (success/failure per source) - a peek at pipeline health."""
    return query(queries.PIPELINE_RUNS, {"limit": limit})
