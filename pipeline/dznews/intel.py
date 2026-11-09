"""Database side of the intelligence layer: embed new articles, then group them into stories.

Both stages are incremental: they only touch articles that still need work, tracked in
intel.article_nlp (status, model, version). A failure on one article is recorded on that
row and never stops the rest.
"""

import json
import logging
import time
from datetime import timedelta

import numpy as np
from psycopg2.extras import execute_values

from dznews import embeddings, settings, text
from dznews.stories import ArticleVec, Story, assign_articles

log = logging.getLogger(__name__)
PIPELINE_VERSION = 1


# --------------------------------------------------------------------------- embedding
def embed_pending(conn, batch_size: int = 16, limit: int | None = None) -> dict:
    """Detect language and compute an embedding for every article that has none yet."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.article_id, a.title, a.summary, a.content
            FROM raw.articles a
            LEFT JOIN intel.article_nlp n USING (article_id)
            WHERE n.article_id IS NULL OR n.status IN ('pending', 'failed')
            ORDER BY a.published_at DESC NULLS LAST
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()

    stats = {"embedded": 0, "failed": 0, "seconds": 0.0}
    started = time.time()
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        inputs = [text.embedding_text(t, s, c) for _, t, s, c in batch]
        try:
            vectors = embeddings.embed(inputs, batch_size=batch_size)
            results = [(row, vec, None) for row, vec in zip(batch, vectors, strict=True)]
        except Exception:  # isolate the bad article instead of losing the whole batch
            log.exception("Batch embedding failed, retrying articles one by one")
            results = []
            for row, one in zip(batch, inputs, strict=True):
                try:
                    results.append((row, embeddings.embed([one])[0], None))
                except Exception as exc:
                    results.append((row, None, str(exc)[:300]))

        with conn.cursor() as cur:
            for (article_id, title, summary, content), vec, error in results:
                language = text.detect_language(f"{title} {summary or ''} {content or ''}")
                if vec is None:
                    stats["failed"] += 1
                    cur.execute(
                        """
                        INSERT INTO intel.article_nlp (article_id, detected_language, status, error)
                        VALUES (%s, %s, 'failed', %s)
                        ON CONFLICT (article_id) DO UPDATE SET status = 'failed', error = EXCLUDED.error
                        """,
                        (article_id, language, error),
                    )
                    continue
                stats["embedded"] += 1
                cur.execute(
                    """
                    INSERT INTO intel.article_nlp
                        (article_id, detected_language, embedding_model, embedding, embedded_at,
                         pipeline_version, status, error)
                    VALUES (%s, %s, %s, %s::vector, now(), %s, 'embedded', NULL)
                    ON CONFLICT (article_id) DO UPDATE SET
                        detected_language = EXCLUDED.detected_language,
                        embedding_model   = EXCLUDED.embedding_model,
                        embedding         = EXCLUDED.embedding,
                        embedded_at       = EXCLUDED.embedded_at,
                        pipeline_version  = EXCLUDED.pipeline_version,
                        status            = 'embedded',
                        error             = NULL
                    """,
                    (article_id, language, embeddings.MODEL_NAME,
                     embeddings.to_pgvector(vec), PIPELINE_VERSION),
                )
        conn.commit()
    stats["seconds"] = round(time.time() - started, 2)
    log.info("Embedding done: %s", stats)
    return stats


# --------------------------------------------------------------------------- stories
def _article_vec(row) -> ArticleVec:
    article_id, source_id, language, published_at, vector, title, summary = row
    return ArticleVec(
        article_id=article_id,
        source_id=source_id,
        language=language or "fr",
        published_at=published_at,
        vector=embeddings.from_pgvector(vector),
        terms=text.key_terms(f"{title} {summary or ''}", language or "fr"),
        title_terms=text.key_terms(title, language or "fr"),
        title=title,
    )


_ARTICLE_COLUMNS = """
    n.article_id, a.source_id, n.detected_language, COALESCE(a.published_at, a.fetched_at),
    n.embedding::text, a.title, a.summary
"""


def assign_pending(conn) -> dict:
    """Group every embedded-but-unassigned article into a (new or existing) story."""
    cfg = settings.cluster_settings()
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_ARTICLE_COLUMNS}
            FROM intel.article_nlp n JOIN raw.articles a USING (article_id)
            WHERE n.status = 'embedded'
            ORDER BY 4
            """
        )
        pending = [_article_vec(r) for r in cur.fetchall()]
        if not pending:
            return {"assigned": 0, "new_stories": 0, "updated_stories": 0, "merged": 0}

        horizon = min(a.published_at for a in pending) - timedelta(hours=cfg.window_hours)
        cur.execute(
            "SELECT story_id FROM intel.stories WHERE status = 'active' AND last_published_at >= %s",
            (horizon,),
        )
        live_ids = [r[0] for r in cur.fetchall()]

        stories: dict[int, Story] = {
            sid: Story(story_id=sid, is_new=False, touched=False) for sid in live_ids
        }
        if live_ids:
            cur.execute(
                f"""
                SELECT n.story_id, {_ARTICLE_COLUMNS}, n.duplicate_of
                FROM intel.article_nlp n JOIN raw.articles a USING (article_id)
                WHERE n.story_id = ANY(%s) AND n.status = 'assigned'
                """,
                (live_ids,),
            )
            for row in cur.fetchall():
                member = _article_vec(row[1:8])
                member.duplicate_of = row[8]
                member.persisted_story_id = row[0]
                story = stories[row[0]]
                story.members.append(member)
            for story in list(stories.values()):
                if story.members:
                    story.centroid = _unit([m.vector for m in story.members])
                else:
                    del stories[story.story_id]

    story_list = list(stories.values())
    before = {s.story_id for s in story_list}
    assign_articles(story_list, pending, cfg)
    result = _persist(conn, story_list, pending, before)
    log.info("Story assignment done: %s", result)
    return result


def _unit(vectors: list[np.ndarray]) -> np.ndarray:
    mean = np.mean(vectors, axis=0)
    norm = np.linalg.norm(mean)
    return mean / norm if norm else mean


def _persist(conn, stories: list[Story], pending: list[ArticleVec], existing_ids: set[int]) -> dict:
    new_stories = merged = updated = 0
    id_map: dict[int, int] = {sid: sid for sid in existing_ids}
    touched = [s for s in stories if s.touched]

    with conn.cursor() as cur:
        # 1. surviving stories first (so merged stories can point at real ids)
        for story in sorted((s for s in touched if s.merged_into is None), key=lambda s: -s.story_id):
            rep = story.representative()
            values = (
                rep.article_id, rep.title, embeddings.to_pgvector(story.centroid),
                len(story.members), len(story.independent_sources), story.languages,
                story.first_published_at, story.last_published_at,
            )
            if story.story_id < 0:
                cur.execute(
                    """
                    INSERT INTO intel.stories
                        (representative_article_id, headline, centroid, article_count, source_count,
                         languages, first_published_at, last_published_at)
                    VALUES (%s, %s, %s::vector, %s, %s, %s, %s, %s) RETURNING story_id
                    """,
                    values,
                )
                id_map[story.story_id] = cur.fetchone()[0]
                new_stories += 1
            else:
                cur.execute(
                    """
                    UPDATE intel.stories SET
                        representative_article_id = %s, headline = %s, centroid = %s::vector,
                        article_count = %s, source_count = %s, languages = %s,
                        first_published_at = %s, last_published_at = %s, updated_at = now()
                    WHERE story_id = %s
                    """,
                    (*values, story.story_id),
                )
                updated += 1

        # 2. merged stories
        for story in (s for s in touched if s.merged_into is not None):
            if story.story_id > 0:
                cur.execute(
                    "UPDATE intel.stories SET status = 'merged', merged_into = %s, updated_at = now() "
                    "WHERE story_id = %s",
                    (id_map.get(story.merged_into, story.merged_into), story.story_id),
                )
            merged += 1

        # 3. article -> story assignments (new articles and members moved by a merge)
        rows = []
        for story in touched:
            if story.merged_into is not None:
                continue
            for member in story.members:
                if member.persisted_story_id == id_map[story.story_id]:
                    continue  # unchanged member of an existing story: keep what is stored
                rows.append((
                    member.article_id, id_map[story.story_id], member.story_score,
                    member.story_confidence, json.dumps(member.reason or {}), member.duplicate_of,
                ))
        if rows:
            execute_values(
                cur,
                """
                UPDATE intel.article_nlp AS n SET
                    story_id = v.story_id::bigint,
                    story_score = COALESCE(v.score::real, n.story_score),
                    story_confidence = COALESCE(v.confidence, n.story_confidence),
                    assignment_reason = COALESCE(n.assignment_reason, '{}'::jsonb) || v.reason::jsonb,
                    duplicate_of = COALESCE(v.dup, n.duplicate_of),
                    status = 'assigned', assigned_at = COALESCE(n.assigned_at, now())
                FROM (VALUES %s) AS v (article_id, story_id, score, confidence, reason, dup)
                WHERE n.article_id = v.article_id
                """,
                rows,
            )
    conn.commit()
    return {
        "assigned": len(pending),
        "new_stories": new_stories,
        "updated_stories": updated,
        "merged": merged,
    }


def reassign_all(conn) -> dict:
    """Throw away all stories and rebuild them from stored embeddings (after retuning)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE intel.article_nlp SET story_id = NULL, story_score = NULL, story_confidence = NULL,
                   assignment_reason = NULL, duplicate_of = NULL, assigned_at = NULL, status = 'embedded'
            WHERE status = 'assigned'
            """
        )
        cur.execute("DELETE FROM intel.stories")
    conn.commit()
    return assign_pending(conn)


def enrich(conn) -> dict:
    """Embedding followed by story assignment: the whole intelligence step."""
    return {"embedding": embed_pending(conn), "stories": assign_pending(conn)}
