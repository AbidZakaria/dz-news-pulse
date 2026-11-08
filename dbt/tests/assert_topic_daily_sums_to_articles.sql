{# Singular test: the daily topic aggregate must account for every article exactly once. #}
select 'fact_topic_daily does not add up to fact_articles' as problem
from (
    select
        (select count(*) from {{ ref('fact_articles') }})                  as articles,
        coalesce((select sum(article_count) from {{ ref('fact_topic_daily') }}), 0) as aggregated
) totals
where articles <> aggregated
