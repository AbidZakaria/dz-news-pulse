select
    row_number() over (order by source_id)::int as source_key,
    source_id,
    source_name,
    language,
    focus,
    website
from {{ ref('news_sources') }}
