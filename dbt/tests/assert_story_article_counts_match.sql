{# Singular test: a story's article_count must equal the articles actually linked to it. #}
select d.story_key, d.article_count, count(b.article_id) as linked
from {{ ref('dim_story') }} d
left join {{ ref('bridge_story_article') }} b on b.story_key = d.story_key
group by d.story_key, d.article_count
having d.article_count <> count(b.article_id)
