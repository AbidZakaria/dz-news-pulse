import json

import pytest

from dznews import config, migrate, settings

GOLD = config.ROOT / "evaluation" / "gold_stories.json"


def test_default_config_file_loads_and_matches_dataclass_fields():
    cfg = settings.load_cluster_settings()
    assert 0 < cfg.threshold_cross_language <= cfg.threshold_same_language < 1
    assert 0 <= cfg.link_weight <= 1


def test_unknown_setting_is_rejected_instead_of_silently_ignored(tmp_path):
    path = tmp_path / "bad.yml"
    path.write_text("clustering:\n  threshold_sam_language: 0.8\n", encoding="utf-8")
    with pytest.raises(ValueError, match="threshold_sam_language"):
        settings.load_cluster_settings(path)


def test_missing_config_falls_back_to_defaults(tmp_path):
    assert settings.load_cluster_settings(tmp_path / "nope.yml") == settings.ClusterSettings()


def test_migrations_are_numbered_without_gaps_or_duplicates():
    versions = [v for v, _ in migrate.available()]
    assert versions == list(range(1, len(versions) + 1))


def test_gold_set_is_internally_consistent():
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    ids = [a["article_id"] for a in gold["articles"]]
    assert len(ids) == len(set(ids))

    labelled = [aid for members in gold["events"].values() for aid in members]
    assert len(labelled) == len(set(labelled)), "an article is in two events"
    assert all(len(members) >= 2 for members in gold["events"].values())
    assert set(labelled) <= set(ids) and set(gold["ambiguous"]) <= set(ids)
    assert not set(labelled) & set(gold["ambiguous"])
    assert "pending human review" in gold["labelled_by"]  # honest about who checked the labels
