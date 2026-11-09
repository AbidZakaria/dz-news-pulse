{#
  Which article belongs to which story, and why. Grain: one row per assigned article.
  is_copy flags a near-identical copy of another outlet's article.
#}
select
    n.story_id                      as story_key,
    n.article_id,
    n.story_score                   as similarity,
    n.story_confidence              as confidence,
    n.duplicate_of is not null      as is_copy,
    n.duplicate_of,
    n.detected_language,
    n.assignment_reason
from {{ source('intel', 'article_nlp') }} n
join {{ ref('dim_story') }} d on d.story_key = n.story_id
where n.status = 'assigned'
