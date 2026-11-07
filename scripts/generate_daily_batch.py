"""Écrit le lot du jour et le SQL D1 correspondant."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from engine.core.models import ItinerairePuzzle, puzzle_to_dict
from engine.geo.generator import generate_geo
from scripts.db_client import render_daily_sql

logger = logging.getLogger(__name__)

GAMES: tuple[tuple[str, str], ...] = (("geo", "itineraire"),)


def build_batch(play_date: date) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    for category, game_slug in GAMES:
        puzzle: ItinerairePuzzle = generate_geo(play_date, game_slug)
        documents.append(puzzle_to_dict(puzzle))
        logger.info("Puzzle %s/%s prêt pour %s", category, game_slug, play_date.isoformat())
    return documents


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Génère le lot de puzzles d'une date UTC.")
    parser.add_argument("--date", help="Date UTC AAAA-MM-JJ. Défaut : aujourd'hui.")
    parser.add_argument("--output", type=Path, required=True, help="Fichier JSON du lot.")
    parser.add_argument("--sql-output", type=Path, help="Fichier SQL d'upsert D1.")
    parser.add_argument(
        "--seed-output",
        type=Path,
        help="Fichier SQL de seed local, sans ligne generation_runs.",
    )
    args = parser.parse_args(argv)
    play_date = _parse_cli_date(args.date)

    documents = build_batch(play_date)
    _write_json(args.output, documents)
    if args.sql_output is not None:
        args.sql_output.parent.mkdir(parents=True, exist_ok=True)
        args.sql_output.write_text(render_daily_sql(documents), encoding="utf-8")
        logger.info("SQL écrit dans %s", args.sql_output)
    if args.seed_output is not None:
        from scripts.db_client import render_seed_sql

        args.seed_output.parent.mkdir(parents=True, exist_ok=True)
        args.seed_output.write_text(render_seed_sql(documents), encoding="utf-8")
        logger.info("Seed écrit dans %s", args.seed_output)
    return 0


def _parse_cli_date(value: str | None) -> date:
    if value is None or not value.strip():
        return datetime.now(timezone.utc).date()
    return date.fromisoformat(value)


def _write_json(path: Path, documents: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("Lot JSON écrit dans %s", path)


if __name__ == "__main__":
    raise SystemExit(main())
