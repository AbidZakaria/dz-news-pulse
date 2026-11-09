"""Incremental event clustering: group articles that report the same real-world event.

Why not DBSCAN/HDBSCAN? Those are batch algorithms: they need all points at once and give
different clusters every time data is added. News arrives continuously and a story must
keep its identity (and its URL) while new coverage joins it. So each new article is
compared with the stories that are still "live" and either joins the best match or starts a
new story. Pure functions on in-memory objects: no database, easy to test and to evaluate.

Signals used to decide (all explained in `Assignment.reason`):
  * embedding similarity to the closest member and to the story centroid
  * a small bonus for distinctive words shared with the closest member
  * a time window (an article cannot join a story that went quiet days ago)
  * a lower bar for French <-> Arabic pairs, which are less similar by nature
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import count

import numpy as np

from dznews.settings import ClusterSettings


@dataclass
class ArticleVec:
    article_id: str
    source_id: str
    language: str                      # detected language: ar / fr / en
    published_at: datetime
    vector: np.ndarray                 # L2-normalised
    terms: set[str] = field(default_factory=set)        # distinctive words (title + summary)
    title_terms: set[str] = field(default_factory=set)  # distinctive words (title only)
    title: str = ""
    duplicate_of: str | None = None
    persisted_story_id: int | None = None  # story it already belongs to in the database
    story_score: float | None = None
    story_confidence: str | None = None
    reason: dict | None = None


@dataclass
class Story:
    story_id: int
    members: list[ArticleVec] = field(default_factory=list)
    centroid: np.ndarray | None = None
    is_new: bool = True
    touched: bool = True
    merged_into: int | None = None

    @property
    def last_published_at(self) -> datetime:
        return max(m.published_at for m in self.members)

    @property
    def first_published_at(self) -> datetime:
        return min(m.published_at for m in self.members)

    @property
    def languages(self) -> list[str]:
        return sorted({m.language for m in self.members})

    @property
    def independent_sources(self) -> set[str]:
        """Sources whose coverage is not just a copy of another outlet's article."""
        return {m.source_id for m in self.members if m.duplicate_of is None}

    def add(self, article: ArticleVec) -> None:
        self.members.append(article)
        self.centroid = _unit(np.mean([m.vector for m in self.members], axis=0))
        self.touched = True

    def representative(self) -> ArticleVec:
        """The member closest to the centroid: a real headline, never an invented one."""
        pool = [m for m in self.members if m.duplicate_of is None] or self.members
        return max(pool, key=lambda m: float(m.vector @ self.centroid))


@dataclass
class Assignment:
    story: Story
    score: float | None
    confidence: str
    reason: dict


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def _overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def _score(article: ArticleVec, story: Story, cfg: ClusterSettings) -> dict | None:
    """Similarity of an article to a story, or None if the time window rules it out."""
    gap = abs(article.published_at - story.last_published_at)
    gap_first = abs(article.published_at - story.first_published_at)
    if min(gap, gap_first) > timedelta(hours=cfg.window_hours):
        return None

    sims = np.array([float(article.vector @ m.vector) for m in story.members])
    closest_idx = int(sims.argmax())
    closest = story.members[closest_idx]
    centroid_sim = float(article.vector @ story.centroid)
    shared = sorted(article.terms & closest.terms)
    bonus = cfg.shared_term_bonus * min(len(shared), 3)
    score = cfg.link_weight * float(sims[closest_idx]) + (1 - cfg.link_weight) * centroid_sim + bonus

    cross_language = article.language != closest.language
    return {
        "score": score,
        "cosine_closest": round(float(sims[closest_idx]), 4),
        "cosine_centroid": round(centroid_sim, 4),
        "shared_terms": shared[:6],
        "closest_article_id": closest.article_id,
        "cross_language": cross_language,
        "threshold": cfg.threshold_cross_language if cross_language else cfg.threshold_same_language,
    }


def _mark_duplicate(article: ArticleVec, story: Story, cfg: ClusterSettings) -> None:
    """Flag a near-identical copy of another outlet's article (syndication)."""
    for member in sorted(story.members, key=lambda m: m.published_at):
        if member.source_id == article.source_id or member.duplicate_of is not None:
            continue
        if float(article.vector @ member.vector) < cfg.duplicate_similarity:
            continue
        if _overlap(article.title_terms, member.title_terms) >= cfg.duplicate_title_overlap:
            article.duplicate_of = member.article_id
            return


def assign_articles(
    stories: list[Story], articles: list[ArticleVec], cfg: ClusterSettings, id_counter=None
) -> list[Story]:
    """Place each new article into the best live story or into a new one.

    `stories` is mutated and extended; the list of stories that changed is returned.
    Articles are processed oldest-first so that stories form in chronological order.
    """
    ids = id_counter or count(-1, -1)  # provisional ids; the database assigns real ones
    for article in sorted(articles, key=lambda a: a.published_at):
        best, best_info = None, None
        for story in stories:
            if story.merged_into is not None:
                continue
            info = _score(article, story, cfg)
            if info and info["score"] >= info["threshold"] and (
                best_info is None or info["score"] > best_info["score"]
            ):
                best, best_info = story, info

        if best is None:
            story = Story(story_id=next(ids))
            article.story_score, article.story_confidence = None, "seed"
            article.reason = {"note": "no live story was similar enough; started a new one"}
            story.add(article)
            stories.append(story)
            continue

        margin = best_info["score"] - best_info["threshold"]
        article.story_score = round(best_info["score"], 4)
        article.story_confidence = "high" if margin >= cfg.high_confidence_margin else "medium"
        article.reason = {k: v for k, v in best_info.items() if k != "score"}
        _mark_duplicate(article, best, cfg)
        best.add(article)

    merge_stories(stories, cfg)
    return [s for s in stories if s.touched]


def _choose_keep(a: Story, b: Story) -> tuple[Story, Story]:
    """Keep the story that already exists in the database; otherwise the larger one."""
    a_saved, b_saved = a.story_id > 0, b.story_id > 0
    if a_saved != b_saved:
        return (a, b) if a_saved else (b, a)
    a_key, b_key = (len(a.members), -abs(a.story_id)), (len(b.members), -abs(b.story_id))
    return (a, b) if a_key >= b_key else (b, a)


def merge_stories(stories: list[Story], cfg: ClusterSettings) -> int:
    """Merge stories that turned out to be the same event (e.g. two early seeds)."""
    live = [s for s in stories if s.merged_into is None]
    merged = 0
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                if a.merged_into is not None or b.merged_into is not None:
                    continue
                if float(a.centroid @ b.centroid) < cfg.merge_threshold:
                    continue
                if min(abs(a.last_published_at - b.first_published_at),
                       abs(b.last_published_at - a.first_published_at)) > timedelta(hours=cfg.window_hours):
                    continue
                keep, drop = _choose_keep(a, b)
                for m in drop.members:
                    m.reason = {**(m.reason or {}), "merged_from_story": drop.story_id}
                    keep.add(m)
                drop.merged_into = keep.story_id
                drop.touched = True
                merged += 1
                changed = True
        live = [s for s in live if s.merged_into is None]
    return merged
