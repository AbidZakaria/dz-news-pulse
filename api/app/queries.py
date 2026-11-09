"""SQL for each endpoint. All windows are anchored on the newest article in the warehouse
(not on today's date), so the API still answers sensibly if the pipeline paused for a few days.
"""

ANCHOR = "anchor AS (SELECT max(date) AS d FROM marts.dim_date)"
# The newest article's timestamp, for windows measured in hours.
ANCHOR_TS = "anchor_ts AS (SELECT max(published_at) AS ts FROM marts.fact_articles)"


def normalized(expr: str) -> str:
    """Same text normalisation as dbt/macros/normalize.sql (French accents, Arabic letter forms)."""
    return f"""regexp_replace(
        translate(
            lower(translate({expr}, 'ÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ', 'aaaeeeeiioouuuc')),
            'àâäéèêëîïôöùûüçœأإآىة',
            'aaaeeeeiioouuucoااايه'
        ),
        '[ً-ْـ]', '', 'g')"""


OVERVIEW = f"""
WITH {ANCHOR_TS}
SELECT
    count(*)                              AS total_articles,
    count(DISTINCT f.source_key)          AS sources,
    count(DISTINCT f.topic_key) FILTER (WHERE t.topic_id <> 'other') AS topics_detected,
    min(f.published_at)                   AS first_article_at,
    max(f.published_at)                   AS latest_article_at,
    count(*) FILTER (WHERE f.published_at > anchor_ts.ts - interval '24 hours')::int AS articles_24h,
    count(*) FILTER (WHERE f.published_at >  anchor_ts.ts - interval '48 hours'
                       AND f.published_at <= anchor_ts.ts - interval '24 hours')::int AS articles_prev_24h
FROM marts.fact_articles f
JOIN marts.dim_topic t USING (topic_key), anchor_ts
GROUP BY anchor_ts.ts
"""

STORY_TOTALS = """
SELECT count(*)::int AS stories,
       count(*) FILTER (WHERE independent_source_count >= 2)::int AS multi_source_stories,
       count(*) FILTER (WHERE is_multilingual)::int AS multilingual_stories
FROM marts.dim_story
"""

# When collection started and when it last ran. Feeds also carry a few old articles, so the
# first *published* date says nothing about how much history the warehouse really holds.
COLLECTION = """
SELECT min(finished_at)                                    AS collecting_since,
       max(finished_at) FILTER (WHERE status = 'success')  AS last_run_at,
       count(DISTINCT source_id) FILTER (
           WHERE status = 'failed'
             AND finished_at > (SELECT max(finished_at) FROM raw.ingestion_log) - interval '1 hour'
       )::int                                              AS sources_failing
FROM raw.ingestion_log
"""

TOPICS = f"""
WITH {ANCHOR},
collected AS (SELECT (min(finished_at) AT TIME ZONE interval '1 hour')::date AS first_day
              FROM raw.ingestion_log),
days AS (
    SELECT generate_series(anchor.d - (%(days)s::int - 1), anchor.d, interval '1 day')::date AS day
    FROM anchor
),
counts AS (
    SELECT f.topic_key, d.date AS day, sum(f.article_count)::int AS n
    FROM marts.fact_topic_daily f
    JOIN marts.dim_date d USING (date_key), anchor
    WHERE d.date > anchor.d - 2 * %(days)s::int
      AND (%(language)s::text IS NULL OR f.language = %(language)s::text)
    GROUP BY f.topic_key, d.date
),
totals AS (
    SELECT t.topic_key, t.topic_id,
           t.topic_name_en AS topic, t.topic_name_fr, t.topic_name_ar,
           coalesce(sum(c.n) FILTER (WHERE c.day >  anchor.d - %(days)s::int), 0)::int AS articles,
           coalesce(sum(c.n) FILTER (WHERE c.day <= anchor.d - %(days)s::int), 0)::int AS prev_raw
    FROM marts.dim_topic t
    LEFT JOIN counts c USING (topic_key), anchor
    GROUP BY t.topic_key, t.topic_id, t.topic_name_en, t.topic_name_fr, t.topic_name_ar
)
SELECT tt.topic_id, tt.topic, tt.topic_name_fr, tt.topic_name_ar, tt.articles,
       round(100.0 * tt.articles / nullif(sum(tt.articles) OVER (), 0), 1)::float AS share_pct,
       -- Only compare with the previous window when it was fully collected.
       CASE WHEN collected.first_day <= anchor.d - 2 * %(days)s::int + 1 THEN tt.prev_raw END
           AS prev_articles,
       -- Days before collection started are NULL: feeds carry a little backlog, which would
       -- otherwise look like a rising trend.
       (SELECT array_agg(CASE WHEN dd.day >= collected.first_day THEN coalesce(c.n, 0) END
                         ORDER BY dd.day)
        FROM days dd LEFT JOIN counts c ON c.topic_key = tt.topic_key AND c.day = dd.day) AS daily,
       (SELECT min(day) FROM days) AS daily_from,
       greatest(0, anchor.d - collected.first_day + 1)::int AS days_collected
FROM totals tt, anchor, collected
WHERE tt.articles > 0
ORDER BY tt.articles DESC, tt.topic
"""

TOPIC = f"""
WITH {ANCHOR}
SELECT t.topic_id, t.topic_name_en AS topic, t.topic_name_fr, t.topic_name_ar, t.description,
       count(f.article_id)::int AS articles,
       count(DISTINCT f.source_key)::int AS sources
FROM marts.dim_topic t
LEFT JOIN marts.fact_articles f
       ON f.topic_key = t.topic_key
      AND f.date_key > to_char((SELECT d FROM anchor) - %(days)s::int, 'YYYYMMDD')::int
WHERE t.topic_id = %(topic)s
GROUP BY t.topic_id, t.topic_name_en, t.topic_name_fr, t.topic_name_ar, t.description
"""

TOPIC_DAILY = f"""
WITH {ANCHOR},
since AS (SELECT (min(finished_at) AT TIME ZONE interval '1 hour')::date AS first_day
          FROM raw.ingestion_log),
days AS (
    SELECT generate_series(anchor.d - (%(days)s::int - 1), anchor.d, interval '1 day')::date AS day
    FROM anchor
)
SELECT dd.day,
       CASE WHEN dd.day >= since.first_day THEN
           coalesce(sum(f.article_count) FILTER (WHERE f.language = 'fr'), 0) END::int AS fr,
       CASE WHEN dd.day >= since.first_day THEN
           coalesce(sum(f.article_count) FILTER (WHERE f.language = 'ar'), 0) END::int AS ar
FROM days dd
LEFT JOIN marts.dim_date d ON d.date = dd.day
LEFT JOIN marts.fact_topic_daily f
       ON f.date_key = d.date_key
      AND f.topic_key = (SELECT topic_key FROM marts.dim_topic WHERE topic_id = %(topic)s), since
GROUP BY dd.day, since.first_day
ORDER BY dd.day
"""

TOPIC_KEYWORDS = f"""
WITH {ANCHOR}
SELECT k.token AS keyword, k.language, count(DISTINCT k.article_id)::int AS mentions
FROM intermediate.int_article_tokens k
JOIN marts.fact_articles f USING (article_id)
JOIN marts.dim_topic t USING (topic_key)
JOIN marts.dim_date d USING (date_key), anchor
WHERE t.topic_id = %(topic)s
  AND d.date > anchor.d - %(days)s::int
  AND NOT k.is_stopword
  AND length(k.token) >= CASE WHEN k.language = 'ar' THEN 3 ELSE 4 END
GROUP BY k.token, k.language
HAVING count(DISTINCT k.article_id) >= 2
ORDER BY mentions DESC, keyword
LIMIT 24
"""

TOPIC_SOURCES = f"""
WITH {ANCHOR}
SELECT s.source_id, s.source_name, s.language, s.focus, count(*)::int AS articles,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)::float AS share_pct
FROM marts.fact_articles f
JOIN marts.dim_topic t USING (topic_key)
JOIN marts.dim_source s USING (source_key)
JOIN marts.dim_date d USING (date_key), anchor
WHERE t.topic_id = %(topic)s AND d.date > anchor.d - %(days)s::int
GROUP BY s.source_id, s.source_name, s.language, s.focus
ORDER BY articles DESC
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
SELECT f.article_id, f.title, f.summary, f.url, f.image_url, f.language, f.published_at,
       s.source_id, s.source_name,
       t.topic_id, t.topic_name_en AS topic,
       b.story_key AS story_id
FROM marts.fact_articles f
LEFT JOIN marts.bridge_story_article b USING (article_id)
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

# Every search term must appear (accent- and Arabic-letter-insensitive) in the title or the
# summary. Title hits rank above summary-only hits, then the newest first.
SEARCH = f"""
WITH {ANCHOR},
terms AS (SELECT {normalized("term")} AS term FROM unnest(%(terms)s::text[]) AS term),
docs AS (
    SELECT f.*, {normalized("f.title")} AS n_title,
           {normalized("coalesce(f.summary, '')")} AS n_summary
    FROM marts.fact_articles f
    JOIN marts.dim_date d USING (date_key), anchor
    WHERE d.date > anchor.d - %(days)s::int
      AND (%(language)s::text IS NULL OR f.language = %(language)s::text)
),
hits AS (
    SELECT docs.*,
           (SELECT count(*) FROM terms WHERE docs.n_title LIKE '%%' || terms.term || '%%') AS title_hits
    FROM docs
    WHERE NOT EXISTS (
        SELECT 1 FROM terms
        WHERE docs.n_title NOT LIKE '%%' || terms.term || '%%'
          AND docs.n_summary NOT LIKE '%%' || terms.term || '%%'
    )
)
SELECT h.article_id, h.title, h.summary, h.url, h.image_url, h.language, h.published_at,
       s.source_id, s.source_name, t.topic_id, t.topic_name_en AS topic,
       b.story_key AS story_id,
       h.title_hits = (SELECT count(*) FROM terms) AS matched_title,
       count(*) OVER () AS total
FROM hits h
JOIN marts.dim_source s USING (source_key)
JOIN marts.dim_topic  t USING (topic_key)
LEFT JOIN marts.bridge_story_article b USING (article_id)
ORDER BY matched_title DESC, h.title_hits DESC, h.published_at DESC
LIMIT %(limit)s::int
"""

SOURCES = """
WITH latest_run AS (
    SELECT DISTINCT ON (source_id) source_id, status, finished_at
    FROM raw.ingestion_log
    ORDER BY source_id, id DESC
),
topic_mix AS (
    SELECT f.source_key, t.topic_id, t.topic_name_en, count(*)::int AS articles,
           row_number() OVER (PARTITION BY f.source_key ORDER BY count(*) DESC, t.topic_id) AS rank
    FROM marts.fact_articles f
    JOIN marts.dim_topic t USING (topic_key)
    GROUP BY f.source_key, t.topic_id, t.topic_name_en
)
SELECT s.source_id, s.source_name, s.language, s.focus, s.website,
       count(DISTINCT f.article_id)::int                         AS articles,
       count(DISTINCT f.article_id) FILTER (WHERE f.image_url IS NOT NULL)::int AS with_image,
       count(DISTINCT b.story_key) FILTER (WHERE st.independent_source_count >= 2)::int
                                                                 AS shared_stories,
       max(f.published_at)                                       AS latest_article_at,
       lr.status                                                 AS last_run_status,
       lr.finished_at                                            AS last_run_at,
       (SELECT json_agg(json_build_object('topic_id', m.topic_id, 'topic', m.topic_name_en,
                                          'articles', m.articles) ORDER BY m.rank)
        FROM topic_mix m WHERE m.source_key = s.source_key AND m.rank <= 4) AS top_topics
FROM marts.dim_source s
LEFT JOIN marts.fact_articles f USING (source_key)
LEFT JOIN marts.bridge_story_article b ON b.article_id = f.article_id
LEFT JOIN marts.dim_story st ON st.story_key = b.story_key
LEFT JOIN latest_run lr ON lr.source_id = s.source_id
GROUP BY s.source_key, s.source_id, s.source_name, s.language, s.focus, s.website,
         lr.status, lr.finished_at
ORDER BY articles DESC, s.source_name
"""

PIPELINE_RUNS = """
SELECT source_id, status, fetched_count, rejected_count, inserted_count, finished_at, error
FROM raw.ingestion_log
ORDER BY id DESC
LIMIT %(limit)s::int
"""

ACTIVITY_HOURLY = f"""
WITH {ANCHOR_TS},
buckets AS (
    SELECT generate_series(date_trunc('hour', ts) - interval '23 hours', date_trunc('hour', ts),
                           interval '1 hour') AS bucket
    FROM anchor_ts
)
SELECT b.bucket,
       count(f.article_id) FILTER (WHERE f.language = 'fr')::int AS fr,
       count(f.article_id) FILTER (WHERE f.language = 'ar')::int AS ar
FROM buckets b
LEFT JOIN marts.fact_articles f ON date_trunc('hour', f.published_at) = b.bucket
GROUP BY b.bucket
ORDER BY b.bucket
"""

# Days before collection started are NULL ("not collected"), not zero ("nothing published").
ACTIVITY_DAILY = f"""
WITH {ANCHOR},
since AS (SELECT (min(finished_at) AT TIME ZONE interval '1 hour')::date AS first_day
          FROM raw.ingestion_log),
days AS (
    SELECT generate_series(anchor.d - (%(days)s::int - 1), anchor.d, interval '1 day')::date AS day
    FROM anchor
)
SELECT dd.day AS bucket,
       CASE WHEN dd.day >= since.first_day THEN
           coalesce(sum(f.article_count) FILTER (WHERE f.language = 'fr'), 0) END::int AS fr,
       CASE WHEN dd.day >= since.first_day THEN
           coalesce(sum(f.article_count) FILTER (WHERE f.language = 'ar'), 0) END::int AS ar
FROM days dd
LEFT JOIN marts.dim_date d ON d.date = dd.day
LEFT JOIN marts.fact_topic_daily f ON f.date_key = d.date_key, since
GROUP BY dd.day, since.first_day
ORDER BY dd.day
"""

# Shared by the story list, the briefing and the story page.
#   versions: the best article in each language (not a copy), so the UI can show a story in
#             the reader's language when an outlet covered it in that language.
#   outlets:  who covered it, in order of first publication.
_STORY_EXTRAS = """
LEFT JOIN marts.fact_articles rep ON rep.article_id = base.representative_article_id
LEFT JOIN LATERAL (
    SELECT f.image_url
    FROM marts.bridge_story_article b JOIN marts.fact_articles f USING (article_id)
    WHERE b.story_key = base.story_id AND f.image_url IS NOT NULL
    ORDER BY (f.article_id = base.representative_article_id) DESC, f.published_at
    LIMIT 1
) img ON true
LEFT JOIN LATERAL (
    SELECT json_agg(json_build_object('source_id', o.source_id, 'source_name', o.source_name)
                    ORDER BY o.first_at) AS outlets
    FROM (
        SELECT s.source_id, s.source_name, min(f.published_at) AS first_at
        FROM marts.bridge_story_article b
        JOIN marts.fact_articles f USING (article_id)
        JOIN marts.dim_source s USING (source_key)
        WHERE b.story_key = base.story_id
        GROUP BY s.source_id, s.source_name
    ) o
) outs ON true
LEFT JOIN LATERAL (
    SELECT json_object_agg(v.language, json_build_object(
               'article_id', v.article_id, 'title', v.title, 'summary', v.summary)) AS versions
    FROM (
        SELECT DISTINCT ON (b.detected_language)
               b.detected_language AS language, f.article_id, f.title, f.summary
        FROM marts.bridge_story_article b
        JOIN marts.fact_articles f USING (article_id)
        WHERE b.story_key = base.story_id AND NOT b.is_copy
        ORDER BY b.detected_language,
                 (f.article_id = base.representative_article_id) DESC,
                 b.similarity DESC NULLS LAST, f.published_at
    ) v
) vers ON true
"""

STORIES = f"""
WITH {ANCHOR}, {ANCHOR_TS},
base AS (
    SELECT st.story_key AS story_id, st.headline, st.representative_article_id,
           st.article_count, st.independent_source_count, st.outlet_count,
           st.languages, st.is_multilingual,
           st.first_published_at, st.last_published_at,
           t.topic_id, t.topic_name_en AS topic,
           round(st.avg_similarity::numeric, 3)::float AS avg_similarity
    FROM marts.dim_story st
    LEFT JOIN marts.dim_topic t USING (topic_key), anchor, anchor_ts
    WHERE st.last_published_date > anchor.d - %(days)s::int
      AND (%(hours)s::int IS NULL
           OR st.last_published_at > anchor_ts.ts - make_interval(hours => %(hours)s::int))
      AND (%(date)s::date IS NULL OR EXISTS (
            SELECT 1 FROM marts.bridge_story_article b
            JOIN marts.fact_articles f USING (article_id)
            WHERE b.story_key = st.story_key
              AND f.date_key = to_char(%(date)s::date, 'YYYYMMDD')::int))
      AND st.independent_source_count >= %(min_sources)s::int
      AND st.article_count >= %(min_articles)s::int
      AND (%(topic)s::text IS NULL OR t.topic_id = %(topic)s::text)
      AND (%(language)s::text IS NULL OR %(language)s::text = ANY (st.languages))
    ORDER BY CASE WHEN %(sort)s::text = 'recent' THEN st.last_published_at END DESC NULLS LAST,
             st.independent_source_count DESC, st.article_count DESC, st.last_published_at DESC
    LIMIT %(limit)s::int
)
SELECT base.*, rep.summary, img.image_url, outs.outlets, vers.versions
FROM base
{_STORY_EXTRAS}
ORDER BY CASE WHEN %(sort)s::text = 'recent' THEN base.last_published_at END DESC NULLS LAST,
         base.independent_source_count DESC, base.article_count DESC, base.last_published_at DESC
"""

STORY = f"""
WITH base AS (
    SELECT st.story_key AS story_id, st.headline, st.representative_article_id,
           st.article_count, st.independent_source_count, st.outlet_count, st.copy_count,
           st.languages, st.is_multilingual, st.first_published_at, st.last_published_at,
           t.topic_id, t.topic_name_en AS topic,
           round(st.avg_similarity::numeric, 3)::float AS avg_similarity,
           round(st.min_similarity::numeric, 3)::float AS min_similarity
    FROM marts.dim_story st
    LEFT JOIN marts.dim_topic t USING (topic_key)
    WHERE st.story_key = %(story_id)s::bigint
)
SELECT base.*, rep.summary, img.image_url, outs.outlets, vers.versions
FROM base
{_STORY_EXTRAS}
"""

STORY_ARTICLES = """
SELECT f.article_id, f.title, f.summary, f.url, f.image_url, f.published_at,
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

# Which days have articles, newest first (for the briefing's day picker).
BRIEFING_DAYS = """
SELECT d.date AS day, count(*)::int AS articles
FROM marts.fact_articles f
JOIN marts.dim_date d USING (date_key)
WHERE d.date >= (SELECT (min(finished_at) AT TIME ZONE interval '1 hour')::date - 1
                 FROM raw.ingestion_log)
GROUP BY d.date
ORDER BY d.date DESC
LIMIT 60
"""

BRIEFING_DAY = """
SELECT count(*)::int                    AS articles,
       count(DISTINCT f.source_key)::int AS sources,
       count(*) FILTER (WHERE f.language = 'fr')::int AS fr,
       count(*) FILTER (WHERE f.language = 'ar')::int AS ar
FROM marts.fact_articles f
WHERE f.date_key = to_char(%(date)s::date, 'YYYYMMDD')::int
"""

BRIEFING_TOPICS = """
SELECT t.topic_id, t.topic_name_en AS topic, count(*)::int AS articles
FROM marts.fact_articles f
JOIN marts.dim_topic t USING (topic_key)
WHERE f.date_key = to_char(%(date)s::date, 'YYYYMMDD')::int AND t.topic_id <> 'other'
GROUP BY t.topic_id, t.topic_name_en
ORDER BY articles DESC, t.topic_id
LIMIT 5
"""

BRIEFING_SINGLES = """
SELECT f.article_id, f.title, f.summary, f.url, f.image_url, f.language, f.published_at,
       s.source_id, s.source_name, t.topic_id, t.topic_name_en AS topic
FROM marts.fact_articles f
JOIN marts.dim_source s USING (source_key)
JOIN marts.dim_topic t USING (topic_key)
LEFT JOIN marts.bridge_story_article b USING (article_id)
LEFT JOIN marts.dim_story st ON st.story_key = b.story_key
WHERE f.date_key = to_char(%(date)s::date, 'YYYYMMDD')::int
  AND coalesce(st.independent_source_count, 1) < 2
  AND t.topic_id <> 'other'
ORDER BY f.published_at DESC
LIMIT %(limit)s::int
"""
