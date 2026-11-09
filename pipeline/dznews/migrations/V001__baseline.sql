-- Raw landing zone. Idempotent: safe to run on every pipeline run.
-- Everything downstream (staging, intermediate, marts) is built by dbt.

CREATE SCHEMA IF NOT EXISTS raw;

-- One row per article, exactly as scraped from the RSS feeds (lightly cleaned).
CREATE TABLE IF NOT EXISTS raw.articles (
    article_id    text PRIMARY KEY,          -- sha1 of the canonical URL
    source_id     text        NOT NULL,
    url           text        NOT NULL,
    title         text        NOT NULL,
    summary       text,
    published_at  timestamptz,               -- NULL when the feed date is unreadable
    published_raw text,                      -- original date string, kept for debugging
    author        text,
    category_raw  text,
    language      text        NOT NULL,
    fetched_at    timestamptz NOT NULL,
    batch_id      text        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_articles_fetched_at ON raw.articles (fetched_at);

-- Audit trail: one row per source per run. Used by the data-quality task and the API.
CREATE TABLE IF NOT EXISTS raw.ingestion_log (
    id             bigserial PRIMARY KEY,
    batch_id       text        NOT NULL,
    source_id      text        NOT NULL,
    finished_at    timestamptz NOT NULL DEFAULT now(),
    fetched_count  integer     NOT NULL DEFAULT 0,
    rejected_count integer     NOT NULL DEFAULT 0,
    inserted_count integer     NOT NULL DEFAULT 0,
    status         text        NOT NULL CHECK (status IN ('success', 'failed')),
    error          text
);
