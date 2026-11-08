{#
  Topic classification, transparent on purpose: every topic owns a list of keywords
  (seeds/topic_keywords.csv). An article scores the sum of the weights of the keywords
  it contains (title matches count double); the highest score wins.
  No match -> topic 'other'.
#}
with keywords as (

    select
        topic_id,
        language,
        {{ normalize_token(normalize_text('keyword'), 'language') }} as keyword,
        weight
    from {{ ref('topic_keywords') }}

),

scores as (

    select
        t.article_id,
        k.topic_id,
        sum(k.weight * case when t.field = 'title' then 2 else 1 end) as topic_score,
        count(distinct k.keyword)                                      as matched_keywords
    from {{ ref('int_article_tokens') }} t
    join keywords k
      on k.language = t.language
     and k.keyword  = t.token
    group by t.article_id, k.topic_id

),

ranked as (

    select
        *,
        row_number() over (
            partition by article_id
            order by topic_score desc, matched_keywords desc, topic_id
        ) as rank_in_article
    from scores

)

select
    a.article_id,
    coalesce(r.topic_id, 'other')       as topic_id,
    coalesce(r.topic_score, 0)          as topic_score,
    coalesce(r.matched_keywords, 0)     as matched_keywords
from {{ ref('stg_articles') }} a
left join ranked r
       on r.article_id = a.article_id
      and r.rank_in_article = 1
