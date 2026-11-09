-- Intelligence layer: full text, embeddings, stories.
-- Additive only: nothing collected so far is touched or deleted.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Richer raw articles: publisher-provided full text (where the feed has it) and all tags.
ALTER TABLE raw.articles ADD COLUMN IF NOT EXISTS content    text;
ALTER TABLE raw.articles ADD COLUMN IF NOT EXISTS categories text[];

CREATE SCHEMA IF NOT EXISTS intel;

-- 2. Stories = groups of articles about the same real-world event.
CREATE TABLE IF NOT EXISTS intel.stories (
    story_id                  bigserial PRIMARY KEY,
    representative_article_id text REFERENCES raw.articles (article_id) ON DELETE SET NULL,
    headline                  text,
    centroid                  vector(768),
    article_count             integer     NOT NULL DEFAULT 0,
    source_count              integer     NOT NULL DEFAULT 0,   -- independent sources only
    languages                 text[]      NOT NULL DEFAULT '{}',
    first_published_at        timestamptz,
    last_published_at         timestamptz,
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now(),
    status                    text        NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'merged')),
    merged_into               bigint
);

CREATE INDEX IF NOT EXISTS idx_stories_active_recent
    ON intel.stories (last_published_at) WHERE status = 'active';

-- 3. Everything the NLP stages derive from an article. One row per article; the
--    status/version columns make processing incremental and re-runnable.
CREATE TABLE IF NOT EXISTS intel.article_nlp (
    article_id          text PRIMARY KEY REFERENCES raw.articles (article_id) ON DELETE CASCADE,
    detected_language   text,                       -- ar / fr / en, detected from the text itself
    embedding_model     text,
    embedding           vector(768),
    embedded_at         timestamptz,
    pipeline_version    integer     NOT NULL DEFAULT 1,
    status              text        NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'embedded', 'assigned', 'failed')),
    error               text,
    -- story assignment
    story_id            bigint REFERENCES intel.stories (story_id) ON DELETE SET NULL,
    story_score         real,                       -- similarity that justified the assignment
    story_confidence    text CHECK (story_confidence IN ('high', 'medium', 'seed')),
    assignment_reason   jsonb,                      -- the signals behind the decision (explainability)
    assigned_at         timestamptz,
    -- a copy of another outlet's article must not count as independent coverage
    duplicate_of        text REFERENCES raw.articles (article_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_article_nlp_status ON intel.article_nlp (status);
CREATE INDEX IF NOT EXISTS idx_article_nlp_story  ON intel.article_nlp (story_id);
CREATE INDEX IF NOT EXISTS idx_article_nlp_embedding
    ON intel.article_nlp USING hnsw (embedding vector_cosine_ops);
