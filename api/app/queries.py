"""SQL for each endpoint. All windows are anchored on the newest article in the warehouse
(not on today's date), so the API still answers sensibly if the pipeline paused for a few days.
"""

ANCHOR = "anchor AS (SELECT max(date) AS d FROM marts.dim_date)"

OVERVIEW = """
SELECT
    count(*)                              AS total_articles,
    count(DISTINCT f.source_key)          AS sources,
    count(DISTINCT f.topic_key) FILTER (WHERE t.topic_id <> 'other') AS topics_detected,
    min(f.published_at)                   AS first_article_at,
    max(f.published_at)                   AS latest_article_at
FROM marts.fact_articles f
JOIN marts.dim_topic t USING (topic_key)
"""

STORY_TOTALS = """
SELECT count(*)::int AS stories,
       count(*) FILTER (WHERE independent_source_count >= 2)::int AS multi_source_stories,
       count(*) FILTER (WHERE is_multilingual)::int AS multilingual_stories
FROM marts.dim_story
"""

TOPICS = f"""
WITH {ANCHOR},
totals AS (
    SELECT t.topic_id,
           t.topic_name_en AS topic,
           t.topic_name_fr,
           t.topic_name_ar,
           sum(f.article_count)::int AS articles
    FROM marts.fact_topic_daily f
    JOIN marts.dim_topic t USING (topic_key)
    JOIN marts.dim_date  d USING (date_key), anchor
    WHERE d.date > anchor.d - %(days)s::int
      AND (%(language)s::text IS NULL OR f.language = %(language)s::text)
    GROUP BY t.topic_id, t.topic_name_en, t.topic_name_fr, t.topic_name_ar
)
SELECT *, round(100.0 * articles / sum(articles) OVER (), 1)::float AS share_pct
FROM totals
ORDER BY articles DESC, topic
"""

KEYWORDS = f"""
WITH {ANCHOR}
SELECT k.keyword, k.language, sum(k.articles)::int AS mentions
FROM marts.fact_keyword_daily k
JOIN marts.dim_date d USING (date_key), anchor
WHERE d.date > anchor.d - %(days)s::int
  AND (%(language)s::text IS NULL OR k.language = %(language)s::text)
GROUP BY k.keyword, k.language
HAVING sum(k.articles) >= %(min_mentions)s::int
ORDER BY mentions DESC, k.keyword
LIMIT %(limit)s::int
"""

ARTICLES = f"""
WITH {ANCHOR}
SELECT f.article_id, f.title, f.url, f.language, f.published_at,
       s.source_id, s.source_name,
       t.topic_id, t.topic_name_en AS topic
FROM marts.fact_articles f
JOIN marts.dim_source s USING (source_key)
JOIN marts.dim_topic  t USING (topic_key)
JOIN marts.dim_date   d USING (date_key), anchor
WHERE d.date > anchor.d - %(days)s::int
  AND (%(topic)s::text    IS NULL OR t.topic_id  = %(topic)s::text)
  AND (%(source)s::text   IS NULL OR s.source_id = %(source)s::text)
  AND (%(language)s::text IS NULL OR f.language  = %(language)s::text)
  AND (%(q)s::text        IS NULL OR f.title ILIKE '%%' || %(q)s::text || '%%')
ORDER BY f.published_at DESC
LIMIT %(limit)s::int
"""

SOURCES = """
SELECT s.source_id, s.source_name, s.language, s.focus,
       count(f.article_id)::int AS articles,
       max(f.published_at)      AS latest_article_at
FROM marts.dim_source s
LEFT JOIN marts.fact_articles f USING (source_key)
GROUP BY s.source_id, s.source_name, s.language, s.focus
ORDER BY articles DESC, s.source_name
"""

PIPELINE_RUNS = """
SELECT source_id, status, fetched_count, rejected_count, inserted_count, finished_at, error
FROM raw.ingestion_log
ORDER BY id DESC
LIMIT %(limit)s::int
"""

STORIES = f"""
WITH {ANCHOR}
SELECT st.story_key AS story_id, st.headline, st.representative_article_id,
       st.article_count, st.independent_source_count, st.outlet_count,
       st.languages, st.is_multilingual,
       st.first_published_at, st.last_published_at,
       t.topic_id, t.topic_name_en AS topic,
       round(st.avg_similarity::numeric, 3)::float AS avg_similarity
FROM marts.dim_story st
LEFT JOIN marts.dim_topic t USING (topic_key), anchor
WHERE st.last_published_date > anchor.d - %(days)s::int
  AND st.independent_source_count >= %(min_sources)s::int
  AND st.article_count >= %(min_articles)s::int
  AND (%(topic)s::text IS NULL OR t.topic_id = %(topic)s::text)
  AND (%(language)s::text IS NULL OR %(language)s::text = ANY (st.languages))
ORDER BY st.independent_source_count DESC, st.article_count DESC, st.last_published_at DESC
LIMIT %(limit)s::int
"""

STORY = """
SELECT st.story_key AS story_id, st.headline, st.representative_article_id,
       st.article_count, st.independent_source_count, st.outlet_count, st.copy_count,
       st.languages, st.first_published_at, st.last_published_at,
       t.topic_id, t.topic_name_en AS topic,
       round(st.avg_similarity::numeric, 3)::float AS avg_similarity,
       round(st.min_similarity::numeric, 3)::float AS min_similarity
FROM marts.dim_story st
LEFT JOIN marts.dim_topic t USING (topic_key)
WHERE st.story_key = %(story_id)s::bigint
"""

STORY_ARTICLES = """
SELECT f.article_id, f.title, f.url, f.published_at,
       s.source_id, s.source_name, b.detected_language AS language,
       b.similarity, b.confidence, b.is_copy, b.duplicate_of,
       b.assignment_reason AS reason,
       row_number() OVER (ORDER BY f.published_at) = 1 AS published_first
FROM marts.bridge_story_article b
JOIN marts.fact_articles f USING (article_id)
JOIN marts.dim_source s USING (source_key)
WHERE b.story_key = %(story_id)s::bigint
ORDER BY f.published_at
"""
