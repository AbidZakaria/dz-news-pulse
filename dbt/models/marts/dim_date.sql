{#
  Calendar dimension covering every day with at least one article.
  Algeria's weekend is Friday + Saturday, so is_weekend follows that.
#}
with bounds as (

    select min(published_date) as first_day, max(published_date) as last_day
    from {{ ref('stg_articles') }}

),

days as (

    select generate_series(first_day, last_day, interval '1 day')::date as date
    from bounds
    where first_day is not null

)

select
    to_char(date, 'YYYYMMDD')::int          as date_key,
    date,
    extract(year  from date)::int           as year,
    extract(month from date)::int           as month,
    extract(day   from date)::int           as day,
    to_char(date, 'FMDay')                  as day_name,
    extract(isodow from date) in (5, 6)     as is_weekend
from days
