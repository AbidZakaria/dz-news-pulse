{# Grain: day x topic x language. Pre-aggregated so the API answers instantly. #}
select
    date_key,
    topic_key,
    language,
    count(*)              as article_count,
    avg(topic_score)      as avg_topic_score
from {{ ref('fact_articles') }}
group by date_key, topic_key, language
