{#
  Splits every article into normalised words ("tokens"), pure SQL.
  Title words are tagged 'title' so the topic model can weigh them double.
  Tokens that are stop-words ("the", "de", "في" ...) are flagged, not deleted,
  so the keyword mart can drop them while the topic model still sees everything.
#}
with articles as (

    select
        article_id,
        language,
        {{ normalize_text('title') }}                      as title_text,
        {{ normalize_text("coalesce(summary, '')") }}      as summary_text
    from {{ ref('stg_articles') }}

),

raw_tokens as (

    select article_id, language, 'title' as field,
           regexp_split_to_table(title_text, '[^a-z0-9ء-ي]+') as token
    from articles

    union all

    select article_id, language, 'summary' as field,
           regexp_split_to_table(summary_text, '[^a-z0-9ء-ي]+') as token
    from articles

),

normalised as (

    select
        article_id,
        language,
        field,
        {{ normalize_token('token', 'language') }} as token
    from raw_tokens
    where length(token) >= 3
      and token !~ '^[0-9]+$'

),

stopwords as (

    select distinct
        language,
        {{ normalize_token(normalize_text('word'), 'language') }} as token
    from {{ ref('stopwords') }}

)

select
    n.article_id,
    n.language,
    n.field,
    n.token,
    s.token is not null as is_stopword
from normalised n
left join stopwords s
       on s.language = n.language
      and s.token = n.token
