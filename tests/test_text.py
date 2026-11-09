import pytest

from dznews import text


@pytest.mark.parametrize(
    "sample, expected",
    [
        ("الحكومة تصادق على مشروع قانون جديد أمام البرلمان", "ar"),
        ("Le ministre des Finances annonce une hausse du budget d'investissement", "fr"),
        ("Surge in Algerian Gas Exports as Production Set to Rise", "en"),
        ("GNL : les exportations algériennes en hausse de 51 % en octobre", "fr"),
        ("Mobilis lance MU Champions مع موبيليس تطلق تحدي ريفولوشن للمشتركين الجدد", "ar"),
        ("", "fr"),  # nothing to detect -> a safe default
    ],
)
def test_detect_language(sample, expected):
    assert text.detect_language(sample) == expected


def test_normalize_removes_french_accents_and_case():
    assert text.normalize_text("Économie DÉVELOPPÉE à Alger") == "economie developpee a alger"


def test_normalize_folds_arabic_variants_and_diacritics():
    # alef variants -> alef, ta marbuta -> ha, alef maqsura -> ya, harakat and tatweel removed
    assert text.normalize_text("أَحْزَابٌ") == text.normalize_text("احزاب")
    assert text.normalize_text("حكومة") == "حكومه"
    assert text.normalize_text("مـــصر") == "مصر"


def test_arabic_article_is_stripped_only_when_enough_letters_remain():
    assert text.normalize_token("الرئيس", "ar") == "رئيس"
    assert text.normalize_token("الله", "ar") == "الله"  # "al" + 2 letters: not an article here


def test_french_plural_is_stripped_but_short_words_are_not():
    assert text.normalize_token("exportations", "fr") == "exportation"
    assert text.normalize_token("gaz", "fr") == "gaz"
    assert text.normalize_token("dans", "fr") == "dans"


def test_key_terms_drop_stopwords_numbers_and_short_words():
    terms = text.key_terms("Les exportations de GNL en hausse de 51 % en octobre", "fr")
    assert "exportation" in terms and "hausse" in terms and "octobre" not in terms  # month = stopword
    assert "51" not in terms and "les" not in terms


def test_key_terms_match_across_spelling_variants_in_arabic():
    assert text.key_terms("الرئيس تبون", "ar") & text.key_terms("رئيسُ الجمهورية تبون", "ar")


def test_embedding_text_prefers_content_and_truncates():
    body = "x" * 2000
    assert len(text.embedding_text("Titre", "résumé court", body)) <= len("Titre. ") + 500
    assert "résumé court" in text.embedding_text("Titre", "résumé court", None)
    assert text.embedding_text("Titre", None, None) == "Titre."
