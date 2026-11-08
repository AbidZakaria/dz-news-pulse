{#
  Text normalisation shared by tokens, keywords and stop-words, so that they always
  compare equal. Works for French AND Arabic, and does not depend on the database locale:

    - lower-cases (also accented capitals) and removes French accents  (é -> e, ç -> c)
    - Arabic: removes diacritics + tatweel, unifies alef forms, alef maqsura and ta marbuta
#}
{% macro normalize_text(expr) %}
regexp_replace(
    translate(
        lower(translate({{ expr }}, 'ÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ', 'aaaeeeeiioouuuc')),
        'àâäéèêëîïôöùûüçœأإآىة',
        'aaaeeeeiioouuucoااايه'
    ),
    '[ً-ْـ]', '', 'g'
)
{% endmacro %}


{#
  Light "stemming" on an already-normalised token:
    - Arabic: drop the definite article (al-) when at least 3 letters remain
    - French: drop a trailing plural "s" on words longer than 4 letters
  Applied identically to tokens and to keyword/stop-word lists.
#}
{% macro normalize_token(token, language) %}
case
    when {{ language }} = 'ar'
        then regexp_replace({{ token }}, '^ال(?=.{3,})', '')
    when {{ language }} = 'fr' and length({{ token }}) > 4
        then regexp_replace({{ token }}, 's$', '')
    else {{ token }}
end
{% endmacro %}
