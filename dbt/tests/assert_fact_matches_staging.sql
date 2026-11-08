{# Singular test: no article may be lost or duplicated on its way into the fact table. #}
select 'article count differs between staging and fact_articles' as problem
from (
    select
        (select count(*) from {{ ref('stg_articles') }})  as staged,
        (select count(*) from {{ ref('fact_articles') }}) as in_fact
) counts
where staged <> in_fact
