"""Clustering logic on synthetic unit vectors (cosine similarity is set exactly)."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from dznews.settings import ClusterSettings
from dznews.stories import ArticleVec, Story, assign_articles, merge_stories

T0 = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
DIM = 8
CFG = ClusterSettings(shared_term_bonus=0.0)


def unit(i: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    v[i] = 1.0
    return v


def at_similarity(base: np.ndarray, cosine: float, other_axis: int) -> np.ndarray:
    """A unit vector whose cosine similarity with `base` is exactly `cosine`."""
    return (cosine * base + np.sqrt(1 - cosine**2) * unit(other_axis)).astype(np.float32)


def art(aid, vector, source="src_a", lang="fr", hours=0, title_terms=(), terms=()):
    return ArticleVec(
        article_id=aid, source_id=source, language=lang, published_at=T0 + timedelta(hours=hours),
        vector=vector, terms=set(terms), title_terms=set(title_terms), title=aid,
    )


def story_of(stories, article_id):
    return next(s for s in stories if any(m.article_id == article_id for m in s.members))


def test_similar_articles_share_a_story_and_unrelated_ones_do_not():
    base = unit(0)
    articles = [
        art("a", base),
        art("b", at_similarity(base, 0.90, 1), source="src_b"),
        art("c", unit(5), source="src_c"),
    ]
    stories: list[Story] = []
    assign_articles(stories, articles, CFG)
    assert story_of(stories, "a") is story_of(stories, "b")
    assert story_of(stories, "c") is not story_of(stories, "a")
    assert len(stories) == 2


def test_threshold_is_respected():
    base = unit(0)
    below = [art("a", base), art("b", at_similarity(base, 0.70, 1), source="src_b")]
    above = [art("a", base), art("b", at_similarity(base, 0.86, 1), source="src_b")]
    s1: list[Story] = []
    s2: list[Story] = []
    assign_articles(s1, below, CFG)
    assign_articles(s2, above, CFG)
    assert len(s1) == 2 and len(s2) == 1


def test_cross_language_pairs_get_a_lower_threshold():
    base = unit(0)
    similar = at_similarity(base, 0.74, 1)  # between the cross (0.71) and same (0.76) thresholds
    same_lang: list[Story] = []
    cross_lang: list[Story] = []
    assign_articles(same_lang, [art("a", base, lang="fr"), art("b", similar, lang="fr", source="b")], CFG)
    assign_articles(cross_lang, [art("a", base, lang="fr"), art("b", similar, lang="ar", source="b")], CFG)
    assert len(same_lang) == 2
    assert len(cross_lang) == 1
    assert cross_lang[0].members[1].reason["cross_language"] is True


def test_time_window_prevents_joining_an_old_story():
    base = unit(0)
    near = [art("a", base), art("b", at_similarity(base, 0.95, 1), hours=10, source="b")]
    far = [art("a", base), art("b", at_similarity(base, 0.95, 1), hours=24 * 10, source="b")]
    s_near: list[Story] = []
    s_far: list[Story] = []
    assign_articles(s_near, near, CFG)
    assign_articles(s_far, far, CFG)
    assert len(s_near) == 1 and len(s_far) == 2


def test_incremental_assignment_joins_an_existing_story():
    base = unit(0)
    stories: list[Story] = []
    assign_articles(stories, [art("a", base)], CFG)
    persisted = stories[0]
    persisted.story_id, persisted.is_new, persisted.touched = 42, False, False  # as if loaded from the DB

    assign_articles(stories, [art("b", at_similarity(base, 0.9, 1), hours=3, source="b")], CFG)
    assert len(stories) == 1 and persisted.story_id == 42 and len(persisted.members) == 2
    assert persisted.touched


def test_first_article_is_a_seed_and_later_ones_record_why_they_joined():
    base = unit(0)
    stories: list[Story] = []
    assign_articles(stories, [art("a", base), art("b", at_similarity(base, 0.92, 1), source="b")], CFG)
    first, second = stories[0].members
    assert first.story_confidence == "seed"
    assert second.story_confidence == "high"
    assert second.reason["closest_article_id"] == "a"
    assert second.reason["cosine_closest"] == pytest.approx(0.92, abs=1e-3)


def test_shared_terms_can_tip_a_borderline_pair_over_the_threshold():
    base = unit(0)
    borderline = at_similarity(base, 0.75, 1)  # just under 0.76
    cfg = ClusterSettings(shared_term_bonus=0.02)
    without: list[Story] = []
    with_terms: list[Story] = []
    assign_articles(without, [art("a", base), art("b", borderline, source="b")], cfg)
    assign_articles(
        with_terms,
        [art("a", base, terms={"gnl", "exportation", "france"}),
         art("b", borderline, source="b", terms={"gnl", "exportation", "france"})],
        cfg,
    )
    assert len(without) == 2 and len(with_terms) == 1


def test_syndicated_copy_is_flagged_and_not_counted_as_independent_source():
    base = unit(0)
    title = {"gnl", "exportations", "hausse", "octobre"}
    stories: list[Story] = []
    assign_articles(
        stories,
        [art("orig", base, source="a", title_terms=title),
         art("copy", at_similarity(base, 0.99, 1), source="b", title_terms=title, hours=1),
         art("other", at_similarity(base, 0.90, 2), source="c", title_terms={"autre", "angle"}, hours=2)],
        CFG,
    )
    assert len(stories) == 1
    story = stories[0]
    copy = next(m for m in story.members if m.article_id == "copy")
    assert copy.duplicate_of == "orig"
    assert story.independent_sources == {"a", "c"}


def test_same_source_updates_are_never_duplicates():
    base = unit(0)
    title = {"match", "togo", "forfait"}
    stories: list[Story] = []
    assign_articles(stories, [art("1", base, title_terms=title),
                              art("2", at_similarity(base, 0.99, 1), title_terms=title, hours=1)], CFG)
    assert all(m.duplicate_of is None for m in stories[0].members)


def test_stories_that_turn_out_to_be_the_same_event_are_merged():
    base = unit(0)
    s1, s2 = Story(story_id=-1), Story(story_id=-2)
    s1.add(art("a", base))
    s2.add(art("b", at_similarity(base, 0.95, 1), source="b", hours=2))
    merged = merge_stories([s1, s2], CFG)
    assert merged == 1
    survivors = [s for s in (s1, s2) if s.merged_into is None]
    assert len(survivors) == 1 and len(survivors[0].members) == 2


def test_merge_prefers_keeping_the_story_already_stored_in_the_database():
    base = unit(0)
    saved, fresh = Story(story_id=7, is_new=False), Story(story_id=-1)
    saved.add(art("a", base))
    fresh.add(art("b", at_similarity(base, 0.95, 1), source="b"))
    fresh.add(art("c", at_similarity(base, 0.96, 2), source="c"))  # the new one is bigger
    merge_stories([saved, fresh], CFG)
    assert fresh.merged_into == 7 and saved.merged_into is None


def test_representative_is_a_real_member_closest_to_the_centroid():
    base = unit(0)
    stories: list[Story] = []
    assign_articles(
        stories,
        [art("edge1", at_similarity(base, 0.9, 1), source="a"),
         art("middle", base, source="b", hours=1),
         art("edge2", at_similarity(base, 0.9, 2), source="c", hours=2)],
        CFG,
    )
    assert stories[0].representative().article_id == "middle"


def test_processing_order_does_not_depend_on_input_order():
    base = unit(0)
    items = [
        art("a", base),
        art("b", at_similarity(base, 0.9, 1), hours=1, source="b"),
        art("c", unit(4), hours=2),
    ]
    forward: list[Story] = []
    backward: list[Story] = []
    assign_articles(forward, list(items), CFG)
    assign_articles(backward, list(reversed(items)), CFG)
    groups = lambda ss: sorted(sorted(m.article_id for m in s.members) for s in ss)  # noqa: E731
    assert groups(forward) == groups(backward)
