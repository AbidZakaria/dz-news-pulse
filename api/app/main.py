"""DZ News Pulse API - serves the dbt marts (topics, keywords, articles) over HTTP."""

from pathlib import Path
from typing import Annotated, Literal

import psycopg2
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from psycopg2 import errors

from app import queries
from app.db import query

app = FastAPI(
    title="DZ News Pulse API",
    description=(
        "What is Algerian news talking about? Topics, trending keywords and headlines, "
        "aggregated from French and Arabic news sites by an Airflow + dbt pipeline."
    ),
    version="1.0.0",
)

Days = Annotated[int, Query(ge=1, le=90, description="Look-back window, in days.")]
Language = Annotated[Literal["fr", "ar"] | None, Query(description="Filter by article language.")]


@app.exception_handler(errors.UndefinedTable)
async def _warehouse_not_built(_: Request, __: Exception):
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
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health", tags=["meta"])
def health():
    """Liveness probe (does not touch the database)."""
    return {"status": "ok"}


@app.get("/overview", tags=["analytics"])
def overview():
    """Headline numbers for the whole warehouse."""
    return {**query(queries.OVERVIEW)[0], **query(queries.STORY_TOTALS)[0]}


@app.get("/stories", tags=["stories"])
def stories(
    days: Days = 7,
    min_sources: Annotated[int, Query(ge=1, description="Minimum independent outlets.")] = 1,
    min_articles: Annotated[int, Query(ge=1)] = 1,
    topic: Annotated[str | None, Query(description="Topic id, e.g. 'economy'.")] = None,
    language: Language = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """News stories: groups of articles about the same event, widest coverage first."""
    return query(
        queries.STORIES,
        {"days": days, "min_sources": min_sources, "min_articles": min_articles,
         "topic": topic, "language": language, "limit": limit},
    )


@app.get("/stories/{story_id}", tags=["stories"])
def story(story_id: int):
    """One story with every article that covers it (who published first, how they differ)."""
    found = query(queries.STORY, {"story_id": story_id})
    if not found:
        raise HTTPException(status_code=404, detail="Story not found")
    return {**found[0], "articles": query(queries.STORY_ARTICLES, {"story_id": story_id})}


@app.get("/topics", tags=["analytics"])
def topics(days: Days = 7, language: Language = None):
    """How much each topic is covered (article count and share) over the last N days."""
    return query(queries.TOPICS, {"days": days, "language": language})


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
    topic: Annotated[str | None, Query(description="Topic id, e.g. 'economy'.")] = None,
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


@app.get("/sources", tags=["pipeline"])
def sources():
    """Each news source with its article count and the date of its latest article."""
    return query(queries.SOURCES)


@app.get("/pipeline/runs", tags=["pipeline"])
def pipeline_runs(limit: Annotated[int, Query(ge=1, le=200)] = 20):
    """Recent ingestion attempts (success/failure per source) - a peek at pipeline health."""
    return query(queries.PIPELINE_RUNS, {"limit": limit})
