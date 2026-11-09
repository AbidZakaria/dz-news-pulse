"""Search terms must normalise exactly like the warehouse, or searches silently miss."""

import pytest

from app.search import MAX_TERMS, like_escape, normalize, search_terms


@pytest.mark.parametrize(
    "query, expected",
    [
        ("Économie", ["economie"]),
        ("les EXPORTATIONS de gaz", ["les", "exportation", "de", "gaz"]),
        ("الرئيس تبون", ["رئيس", "تبون"]),             # definite article dropped
        ("أحزاب", ["احزاب"]),                          # alef forms folded
        ("الحكومة", ["حكومه"]),                        # ta marbuta folded, article dropped
        ("مُنتَخَب", ["منتخب"]),                        # diacritics removed
        ("tebboune tebboune", ["tebboune"]),           # duplicates removed
        ("a ! ?", []),                                 # too short / punctuation only
    ],
)
def test_search_terms(query, expected):
    assert search_terms(query) == expected


def test_hamza_letters_are_kept_like_in_sql():
    # Unicode decomposition would turn ئ into ي; the SQL normalisation does not, so neither may we.
    assert normalize("رئيس") == "رئيس"
    assert normalize("مؤتمر") == "مؤتمر"


def test_number_of_terms_is_capped():
    assert len(search_terms(" ".join(f"word{i}" for i in range(20)))) == MAX_TERMS


def test_like_wildcards_are_escaped():
    assert like_escape("50%_off\\") == "50\\%\\_off\\\\"
