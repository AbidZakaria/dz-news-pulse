"""Command line helpers:  python -m dznews.cli <command>

  ingest [SOURCE_ID ...]   fetch live feeds (all sources by default)
  load-sample              load the synthetic fixtures in sample_data/ (offline demo + CI)
  check                    run the data-quality checks
  migrate                  apply pending database migrations
  embed                    compute embeddings for new articles
  stories                  group embedded articles into stories
  enrich                   embed + stories (what the DAG runs)
  rebuild-stories          rebuild all stories from stored embeddings (after retuning)
  evaluate [--grid]        score story clustering against the hand-labelled evaluation set
"""

import argparse
import logging
import sys
import uuid
from datetime import UTC, datetime

from dznews import config, extract, ingest, intel, load, quality, sources, transform

# Which fixture feeds which (fake) source when loading the offline sample.
SAMPLE_FILES = {
    "algerie360": "sample_fr.xml",
    "echorouk": "sample_ar.xml",
    "elkhabar": "sample_elkhabar.xml",
}


def load_sample() -> int:
    batch_id = f"sample-{uuid.uuid4().hex[:6]}"
    total = 0
    conn = load.get_connection()
    try:
        load.ensure_schema(conn)
        for source_id, filename in SAMPLE_FILES.items():
            source = sources.get_source(source_id)
            content = (config.SAMPLE_DIR / filename).read_bytes()
            records = extract.parse_feed(content)
            df, rejected = transform.build_articles_frame(
                records, source, batch_id, datetime.now(UTC)
            )
            inserted = load.insert_articles(conn, df)
            load.log_run(conn, batch_id, source_id, "success", len(records), rejected, inserted)
            print(f"{source_id}: {inserted} inserted, {rejected} rejected")
            total += inserted
    finally:
        conn.close()
    return total


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="dznews")
    sub = parser.add_subparsers(dest="command", required=True)
    p_ingest = sub.add_parser("ingest", help="fetch live feeds")
    p_ingest.add_argument("source_ids", nargs="*")
    sub.add_parser("load-sample", help="load offline fixtures")
    sub.add_parser("check", help="run data-quality checks")
    p_eval = sub.add_parser("evaluate", help="score clustering on the labelled evaluation set")
    p_eval.add_argument("--grid", action="store_true", help="sweep the similarity thresholds")
    for name, helptext in [
        ("migrate", "apply pending database migrations"),
        ("embed", "compute embeddings for new articles"),
        ("stories", "group embedded articles into stories"),
        ("enrich", "embed + stories"),
        ("rebuild-stories", "rebuild all stories from stored embeddings"),
    ]:
        sub.add_parser(name, help=helptext)
    args = parser.parse_args(argv)

    if args.command == "ingest":
        ids = args.source_ids or [s.source_id for s in sources.load_sources()]
        failures = 0
        for source_id in ids:
            try:
                print(ingest.ingest_source(source_id))
            except Exception as exc:  # keep going: one broken source must not stop the others
                failures += 1
                print(f"{source_id}: FAILED - {exc}", file=sys.stderr)
        return 1 if failures == len(ids) else 0

    if args.command == "load-sample":
        load_sample()
        return 0

    if args.command == "evaluate":
        from dznews import evaluate

        return evaluate.main(run_grid=args.grid)

    if args.command in {"migrate", "embed", "stories", "enrich", "rebuild-stories"}:
        conn = load.get_connection()
        try:
            load.ensure_schema(conn)
            action = {
                "migrate": lambda c: [],
                "embed": intel.embed_pending,
                "stories": intel.assign_pending,
                "enrich": intel.enrich,
                "rebuild-stories": intel.reassign_all,
            }[args.command]
            print(action(conn))
        finally:
            conn.close()
        return 0

    conn = load.get_connection()
    try:
        problems = quality.run_checks(conn)
    finally:
        conn.close()
    for problem in problems:
        print("PROBLEM:", problem)
    print("OK" if not problems else "FAILED")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
