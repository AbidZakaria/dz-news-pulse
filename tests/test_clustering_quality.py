"""Regression guard: clustering quality on the hand-labelled real articles.

Marked `slow` because the first run downloads the embedding model (~1 GB); the vectors are
then cached in evaluation/.cache. Run explicitly with:  pytest -m slow
"""

import pytest

from dznews import evaluate
from dznews.settings import cluster_settings


@pytest.mark.slow
def test_clustering_quality_does_not_regress():
    gold = evaluate.load_gold()
    report = evaluate.evaluate(gold, evaluate.build_articles(gold), cluster_settings())
    # Measured 2026-11-09: precision 0.93, recall 0.77. Floors leave a little room for noise.
    assert report.precision >= 0.88, report.line()
    assert report.recall >= 0.70, report.line()
