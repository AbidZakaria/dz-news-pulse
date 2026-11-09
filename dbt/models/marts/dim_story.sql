{#
  One row per live news story: a group of articles (from one or more outlets, in one or
  more languages) about the same real-world event. Stories are produced by the Python
  clustering step; this model adds the topic and the coverage statistics.

  independent_source_count excludes copies of another outlet's article, so syndicated
  text is never presented as extra, independent coverage.
#}
with stories as (

    select * from {{ source('intel', 'stories') }} where status = 'active'

),

members as (

    select
        n.story_id,
        n.article_id,
        n.story_score,
        n.duplicate_of,
        f.topic_key,
        f.source_key
    from {{ source('intel', 'article_nlp') }} n
    join {{ ref('fact_articles') }} f on f.article_id = n.article_id
    where n.story_id is not null

),

topic_votes as (

    select
        m.story_id,
        m.topic_key,
        t.topic_id,
        count(*) as votes,
        -- a real topic beats "other" even with fewer votes
        row_number() over (
            partition by m.story_id
            order by (t.topic_id = 'other'), count(*) desc, m.topic_key
        ) as rank_in_story
    from members m
    join {{ ref('dim_topic') }} t on t.topic_key = m.topic_key
    group by m.story_id, m.topic_key, t.topic_id

),

stats as (

    select
        story_id,
        count(distinct source_key)                                         as outlet_count,
        count(*) filter (where duplicate_of is not null)                   as copy_count,
        avg(story_score)                                                   as avg_similarity,
        min(story_score)                                                   as min_similarity
    from members
    group by story_id

)

select
    s.story_id                          as story_key,
    s.headline,
    s.representative_article_id,
    s.article_count,
    s.source_count                      as independent_source_count,
    st.outlet_count,
    st.copy_count,
    s.languages,
    cardinality(s.languages) > 1        as is_multilingual,
    s.first_published_at,
    s.last_published_at,
    (s.first_published_at at time zone interval '1 hour')::date as first_published_date,
    (s.last_published_at  at time zone interval '1 hour')::date as last_published_date,
    tv.topic_key,
    st.avg_similarity,
    st.min_similarity
from stories s
join stats st on st.story_id = s.story_id
left join topic_votes tv on tv.story_id = s.story_id and tv.rank_in_story = 1
