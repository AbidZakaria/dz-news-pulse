# Intelligence layer: how stories are detected

DZ News Pulse does not just list headlines. Articles about the **same real-world event**,
from different outlets and in different languages, are grouped into one *story*.

Everything runs **locally on the CPU**. There are no paid APIs and no calls to any external
AI service. The only network traffic is downloading the public RSS feeds and, once, the
open-source embedding model.

## Pipeline

```
RSS feeds ──► raw.articles ──► embed (local model) ──► assign to stories ──► dbt marts ──► API
              full text,        intel.article_nlp        intel.stories        dim_story
              tags, dates       (768-d vector)                                bridge_story_article
```

| Step | Code | What it does |
|---|---|---|
| Collect | `pipeline/dznews/extract.py` | Reads each feed, keeps the publisher's **full text** (when the feed has it) and all tags |
| Embed | `embeddings.py`, `intel.embed_pending` | Turns *title + opening of the text* into a 768-number vector with `paraphrase-multilingual-mpnet-base-v2` |
| Cluster | `stories.py`, `intel.assign_pending` | Joins each new article to the best live story or starts a new one |
| Model | `dbt/models/marts/dim_story.sql` | Adds topic and coverage statistics, with tests |
| Serve | `api/app/main.py` | `/stories`, `/stories/{id}` |

Processing is **incremental**: `intel.article_nlp` records the status, model and version of
every article, so only new articles are processed. A failure on one article is stored on
that row and never stops the others.

## Why this embedding model

I compared two multilingual models on the real collected articles (4-core desktop CPU from
2014, no GPU) before choosing:

| Model | Size | Speed | Result |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 0.22 GB | 38 ms/article | Some unrelated short texts scored as high as true duplicates |
| **`paraphrase-multilingual-mpnet-base-v2`** (used) | 1 GB | ~100 ms/article | Top pairs were true same-event pairs, including French↔Arabic |
| `multilingual-e5-large` | 2.2 GB | several times slower | Scores of unrelated pairs are compressed above 0.85; stories collapse into one giant cluster unless embeddings are centred first. Not worth the cost here |

It runs through ONNX Runtime (via `fastembed`), so PyTorch is not needed.

## Clustering rules

HDBSCAN/DBSCAN are batch algorithms: they need every point at once and reshuffle clusters
as data arrives. A news story must keep its identity while new coverage joins it, so each
article is compared with the stories that are still "live":

* **Similarity** of the article to the *closest article already in the story*.
* A small **bonus** for distinctive words shared with that article (up to 3).
* **Time window:** an article cannot join a story that went quiet more than 72 h ago.
* **Language-aware threshold:** French↔Arabic pairs are naturally less similar in the
  embedding space, so they get a lower bar (0.71 vs 0.76).
* **Merge pass:** two stories that turn out to be the same event are merged.
* **Syndicated copies** (near-identical text *and* headline from another outlet) are flagged
  and **not counted as independent coverage**.
* Every assignment stores **why** it was made (`assignment_reason`: the similarities, the
  shared words, the closest article, the threshold) and a confidence label
  (`high` / `medium` / `seed`).

All thresholds live in [`config/intelligence.yml`](../config/intelligence.yml).

## How good is it? (measured, with caveats)

`python -m dznews.cli evaluate` scores the clustering on
[`evaluation/gold_stories.json`](../evaluation/gold_stories.json): 181 **real** articles, of
which 58 were hand-labelled into 24 events (19 loosely related ones are excluded as
ambiguous). Pairwise metrics:

| Setting | Precision | Recall | F1 |
|---|---|---|---|
| First version (centroid blend, same 0.78 / cross 0.72) | 0.97 | 0.58 | 0.73 |
| **Current** (closest-member, same 0.76 / cross 0.71) | **0.93** | **0.77** | **0.84** |

**Read these numbers with care:**

* The labels were made by reading headlines and are **not yet verified by a second human**.
* The thresholds were tuned on this same small set, so the scores are optimistic.
* Remaining errors are informative: French↔Arabic *nicknames* that no embedding links
  ("Fennecs" = "الخضر", "USMA" = "سوسطارة") and two unrelated fraud cases that look similar.
  Entity aliases (planned) are the right fix for the first kind.

A slow regression test (`pytest -m slow`) fails if quality drops below the measured floor.

## Known limits

* RSS gives only recent articles; history builds up from the first run.
* Three of the seven feeds provide full text. For the others the summary is short, which
  limits what the embedding can see.
* No English-language feed was available; the model supports English, and an English item
  published inside Echorouk's feed was correctly matched to a French article.
* Stories are **detected, not guaranteed**: they are algorithmic groupings and are shown with
  their confidence and the evidence behind them.
