"""Measure story-clustering quality against the hand-labelled evaluation set.

    python -m dznews.cli evaluate          # report with the current config/intelligence.yml
    python -m dznews.cli evaluate --grid   # sweep the two similarity thresholds

Metric: pairwise precision / recall / F1 over all pairs of labelled articles.
  * positive pair  = two articles of the same labelled event
  * negative pair  = everything else (articles not in any event are their own event)
  * ambiguous articles are left out entirely (they are neither right nor wrong)
Precision answers "when we group two articles, are they really the same event?",
recall answers "of the pairs that really belong together, how many did we group?".
"""

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np

from dznews import config, embeddings, text
from dznews.settings import ClusterSettings, cluster_settings
from dznews.stories import ArticleVec, assign_articles

GOLD_PATH = config.ROOT / "evaluation" / "gold_stories.json"
CACHE_PATH = config.ROOT / "evaluation" / ".cache" / "embeddings.npz"


@dataclass
class Report:
    precision: float
    recall: float
    f1: float
    true_positive: int
    false_positive: int
    false_negative: int
    false_merges: list[tuple[str, str, float | None]]
    missed: list[tuple[str, str, float]]

    def line(self) -> str:
        return (f"precision={self.precision:.3f} recall={self.recall:.3f} f1={self.f1:.3f} "
                f"(TP={self.true_positive} FP={self.false_positive} FN={self.false_negative})")


def load_gold(path: Path = GOLD_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _gold_vectors(gold: dict) -> dict[str, np.ndarray]:
    """Embeddings of the gold articles, cached on disk (the model is the slow part)."""
    cache: dict[str, np.ndarray] = {}
    if CACHE_PATH.exists():
        with np.load(CACHE_PATH, allow_pickle=False) as data:
            cache = {k: data[k] for k in data.files}
    missing, keys = [], {}
    for art in gold["articles"]:
        body = art["content_head"] or art["summary"]
        input_text = text.embedding_text(art["title"], art["summary"], body)
        key = hashlib.sha1(f"{embeddings.MODEL_NAME}|{input_text}".encode()).hexdigest()
        keys[art["article_id"]] = key
        if key not in cache:
            missing.append((key, input_text))
    if missing:
        vectors = embeddings.embed([t for _, t in missing])
        cache.update({k: v for (k, _), v in zip(missing, vectors, strict=True)})
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(CACHE_PATH, **cache)
    return {aid: cache[key] for aid, key in keys.items()}


def build_articles(gold: dict) -> list[ArticleVec]:
    vectors = _gold_vectors(gold)
    out = []
    for art in gold["articles"]:
        lang = art["language"] or "fr"
        out.append(ArticleVec(
            article_id=art["article_id"], source_id=art["source_id"], language=lang,
            published_at=datetime.fromisoformat(art["published_at"]), vector=vectors[art["article_id"]],
            terms=text.key_terms(f"{art['title']} {art['summary']}", lang),
            title_terms=text.key_terms(art["title"], lang), title=art["title"],
        ))
    return out


def evaluate(gold: dict, articles: list[ArticleVec], cfg: ClusterSettings) -> Report:
    stories = []
    assign_articles(stories, [_copy(a) for a in articles], cfg)
    predicted = {m.article_id: s.story_id for s in stories if s.merged_into is None for m in s.members}
    scores = {m.article_id: m.story_score for s in stories for m in s.members}

    truth = {}
    for name, members in gold["events"].items():
        for aid in members:
            truth[aid] = name
    ambiguous = set(gold["ambiguous"])
    ids = [a.article_id for a in articles if a.article_id not in ambiguous]
    titles = {a.article_id: a.title for a in articles}
    vec = {a.article_id: a.vector for a in articles}

    tp = fp = fn = 0
    false_merges, missed = [], []
    for a, b in combinations(ids, 2):
        same_truth = a in truth and truth.get(a) == truth.get(b)
        same_pred = predicted[a] == predicted[b]
        if same_truth and same_pred:
            tp += 1
        elif same_pred:
            fp += 1
            false_merges.append((titles[a], titles[b], scores.get(a) or scores.get(b)))
        elif same_truth:
            fn += 1
            missed.append((titles[a], titles[b], float(vec[a] @ vec[b])))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return Report(precision, recall, f1, tp, fp, fn, false_merges, sorted(missed, key=lambda m: -m[2]))


def _copy(a: ArticleVec) -> ArticleVec:
    return replace(a, duplicate_of=None, story_score=None, story_confidence=None, reason=None)


def _candidate_thresholds(articles: list[ArticleVec]) -> list[float]:
    """Thresholds worth trying, taken from this model's own similarity distribution.

    Models differ wildly in how spread out their cosine scores are (e5 puts unrelated texts
    above 0.85, MiniLM below 0.5), so a fixed 0.74-0.84 grid would be meaningless for some.
    """
    vectors = np.array([a.vector for a in articles])
    sims = (vectors @ vectors.T)[np.triu_indices(len(articles), k=1)]
    quantiles = (0.994, 0.996, 0.997, 0.998, 0.9985, 0.999, 0.9995)
    return [round(float(np.quantile(sims, q)), 3) for q in quantiles]


def grid(
    gold: dict, articles: list[ArticleVec], base: ClusterSettings
) -> list[tuple[ClusterSettings, Report]]:
    results = []
    for same in _candidate_thresholds(articles):
        for gap in (0.0, 0.02, 0.04, 0.06):  # cross-language bar sits this far below same-language
            cfg = replace(base, threshold_same_language=same, threshold_cross_language=same - gap)
            results.append((cfg, evaluate(gold, articles, cfg)))
    return sorted(results, key=lambda r: -r[1].f1)


def main(run_grid: bool = False) -> int:
    gold = load_gold()
    articles = build_articles(gold)
    base = cluster_settings()
    report = evaluate(gold, articles, base)
    n_labelled = sum(len(v) for v in gold["events"].values())
    print(f"Gold set: {len(articles)} real articles, {n_labelled} labelled in "
          f"{len(gold['events'])} events, {len(gold['ambiguous'])} ambiguous (ignored)")
    print(f"Current config (same={base.threshold_same_language}, cross={base.threshold_cross_language}):")
    print("  " + report.line())
    if report.false_merges:
        print("\nWrongly grouped pairs:")
        for a, b, s in report.false_merges[:12]:
            print(f"  [{s if s is None else round(s, 3)}] {a[:60]}  <->  {b[:60]}")
    if report.missed:
        print("\nMissed pairs (same event, not grouped):")
        for a, b, s in report.missed[:12]:
            print(f"  [cos {s:.3f}] {a[:60]}  <->  {b[:60]}")
    if run_grid:
        print("\nThreshold sweep (best first):")
        for cfg, rep in grid(gold, articles, base)[:10]:
            print(
                f"  same={cfg.threshold_same_language:.2f} "
                f"cross={cfg.threshold_cross_language:.2f}  {rep.line()}"
            )
    return 0
