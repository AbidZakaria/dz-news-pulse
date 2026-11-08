{#
  Staging = 1:1 with the raw table, only light, safe cleaning:
  consistent names/types, one row per article, a trustworthy publication date.
#}
with source as (

    select * from {{ source('raw', 'articles') }}

),

deduplicated as (

    select
        *,
        row_number() over (partition by article_id order by fetched_at) as row_num
    from source

),

cleaned as (

    select
        article_id,
        source_id,
        url,
        trim(title)                                    as title,
        nullif(trim(summary), '')                      as summary,
        language,
        nullif(trim(author), '')                       as author,
        nullif(trim(category_raw), '')                 as category_raw,
        fetched_at,
        -- Missing or future dates (clock skew, bad feeds) fall back to the fetch time.
        case
            when published_at is null or published_at > fetched_at then fetched_at
            else published_at
        end                                            as published_at,
        published_at is null or published_at > fetched_at as published_at_was_imputed
    from deduplicated
    where row_num = 1
      and nullif(trim(title), '') is not null

)

select
    *,
    -- Algeria is UTC+1 all year (no daylight saving), so a fixed offset is exact.
    (published_at at time zone interval '1 hour')::date as published_date
from cleaned
