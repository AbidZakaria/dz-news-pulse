{#
  Grain: day x language x keyword. "In how many articles did this word appear today?"
  Stop-words and very short words are removed; the keyword is shown in its normalised
  form (no accents, no Arabic "al-", singular French).
#}
select
    to_char(a.published_date, 'YYYYMMDD')::int as date_key,
    t.language,
    t.token                                    as keyword,
    count(distinct t.article_id)               as articles
from {{ ref('int_article_tokens') }} t
join {{ ref('stg_articles') }}       a on a.article_id = t.article_id
where not t.is_stopword
  and length(t.token) >= case when t.language = 'ar' then 3 else 4 end
group by 1, 2, 3
