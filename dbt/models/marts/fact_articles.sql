{# Grain: one row per article. The central fact table of the star schema. #}
select
    a.article_id,
    s.source_key,
    to_char(a.published_date, 'YYYYMMDD')::int as date_key,
    t.topic_key,
    a.title,
    a.url,
    a.language,
    a.published_at,
    p.topic_score,
    p.matched_keywords,
    length(a.title)                            as title_length
from {{ ref('stg_articles') }}         a
join {{ ref('int_article_topics') }}   p on p.article_id = a.article_id
join {{ ref('dim_source') }}           s on s.source_id  = a.source_id
join {{ ref('dim_topic') }}            t on t.topic_id   = p.topic_id
