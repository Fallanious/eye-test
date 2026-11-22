"""Verify source events and merge score attributes into existing clips on the guarded DB."""
import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from clip_scores import score_attributes
from match_play_timestamps import load_pbp_source
from persist_matcher_clips import assert_persist_ready, direct_database_url, game_clock_interval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    params = assert_persist_ready(direct_database_url(os.environ["DATABASE_URL"]))
    with psycopg.connect(**params) as conn:
        if args.apply:
            migration = Path(__file__).resolve().parents[1] / "migrations/001_clutch.sql"
            conn.execute(migration.read_text())
        for game_id, name in conn.execute(
            "SELECT DISTINCT g.id, g.bbref_id FROM games g JOIN clips c ON c.game_id=g.id ORDER BY 2"
        ).fetchall():
            digest, plays = load_pbp_source(args.source_dir / f"{name}.json")
            updates = []
            rows = conn.execute(
                "SELECT id, play_index, period, game_clock, description, attributes FROM clips WHERE game_id=%s FOR UPDATE",
                (game_id,),
            ).fetchall()
            for clip_id, idx, period, clock, description, attrs in rows:
                play = plays[idx]
                if (idx < 0 or attrs.get("pbp_sha256", digest) != digest
                    or (period, clock, description) != (play["quarter"], game_clock_interval(play["time"]), play["description"])):
                    raise ValueError(f"{name} clip {clip_id} does not match source event {idx}")
                context = score_attributes(plays, idx)
                if "pre_play_score" not in context or "post_play_score" not in context:
                    raise ValueError(f"{name} clip {clip_id} has incomplete source scores")
                if any(attrs.get(k) != v for k, v in context.items()):
                    updates.append((Jsonb(context), clip_id))
            if args.apply and updates:
                with conn.cursor() as cursor:
                    cursor.executemany("UPDATE clips SET attributes=attributes || %s WHERE id=%s", updates)
            print(name, len(rows), "verified,", len(updates), "to update")


if __name__ == "__main__":
    main()
