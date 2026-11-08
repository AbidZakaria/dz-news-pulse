"""Guard-rails on the dbt seed files: cheap checks that catch typos before dbt runs."""

import csv
from pathlib import Path

import pytest

SEEDS = Path(__file__).resolve().parents[1] / "dbt" / "seeds"


def rows(name: str) -> list[dict]:
    with open(SEEDS / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_every_keyword_points_to_a_known_topic():
    topics = {r["topic_id"] for r in rows("topics.csv")}
    unknown = {r["topic_id"] for r in rows("topic_keywords.csv")} - topics
    assert not unknown, f"keywords reference unknown topics: {unknown}"


def test_every_topic_has_keywords_in_both_languages_except_other():
    keywords = rows("topic_keywords.csv")
    for topic in {r["topic_id"] for r in rows("topics.csv")} - {"other"}:
        langs = {r["language"] for r in keywords if r["topic_id"] == topic}
        assert langs == {"fr", "ar"}, f"{topic} only has {langs}"


def test_keyword_weights_and_languages_are_valid():
    for r in rows("topic_keywords.csv"):
        assert r["language"] in {"fr", "ar"}
        assert int(r["weight"]) in {1, 2}
        assert r["keyword"].strip() == r["keyword"] and r["keyword"]


def test_no_duplicate_keyword_inside_a_topic():
    seen = set()
    for r in rows("topic_keywords.csv"):
        key = (r["topic_id"], r["language"], r["keyword"])
        assert key not in seen, f"duplicate keyword {key}"
        seen.add(key)


def test_stopwords_are_valid():
    for r in rows("stopwords.csv"):
        assert r["language"] in {"fr", "ar"} and r["word"]


@pytest.mark.parametrize("column", ["source_id", "feed_url", "language"])
def test_sources_are_complete_and_unique(column):
    values = [r[column] for r in rows("news_sources.csv")]
    assert all(values)
    if column != "language":
        assert len(values) == len(set(values))


def test_sample_sources_exist_in_sources_seed():
    from dznews.cli import SAMPLE_FILES

    known = {r["source_id"] for r in rows("news_sources.csv")}
    assert set(SAMPLE_FILES) <= known
