select
    row_number() over (order by topic_id)::int as topic_key,
    topic_id,
    topic_name_en,
    topic_name_fr,
    topic_name_ar,
    description
from {{ ref('topics') }}
