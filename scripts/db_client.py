"""Rend le SQL d'upsert D1. Aucun appel réseau : l'exécution reste dans la CI."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from engine.core.models import GENERATOR_VERSION
from engine.core.validators import validate_puzzle_document


def render_daily_sql(documents: Sequence[Mapping[str, object]], *, published: bool = True) -> str:
    """Transaction idempotente : un run de génération puis les upserts du lot."""
    if not documents:
        raise ValueError("Aucun puzzle à écrire.")
    play_dates = {str(document["play_date"]) for document in documents}
    if len(play_dates) != 1:
        raise ValueError("Un fichier SQL quotidien ne couvre qu'une play_date.")
    play_date = play_dates.pop()
    stamped = f"{play_date}T00:05:00+00:00"
    detail = ", ".join(f"{document['category']}/{document['game_slug']}" for document in documents)
    statements = [
        "BEGIN TRANSACTION;",
        (
            "INSERT INTO generation_runs "
            "(play_date, started_at, finished_at, status, generator_version, puzzles_written, detail) "
            f"VALUES ({_quote(play_date)}, {_quote(stamped)}, {_quote(stamped)}, 'success', "
            f"{_quote(GENERATOR_VERSION)}, {len(documents)}, {_quote(detail)});"
        ),
        *[render_upsert(document, published=published) for document in documents],
        "COMMIT;",
        "",
    ]
    return "\n".join(statements)


def render_seed_sql(documents: Sequence[Mapping[str, object]]) -> str:
    body = "\n".join(render_upsert(document, published=True) for document in documents)
    return (
        "-- Seed local. Ne pas appliquer en production : le lot quotidien passe par GitHub Actions.\n"
        "BEGIN TRANSACTION;\n"
        f"{body}\n"
        "COMMIT;\n"
    )


def render_upsert(document: Mapping[str, object], *, published: bool) -> str:
    validate_puzzle_document(document)
    payload = _json(document["payload"])
    solution = _json(document["solution"])
    metadata = _json(document["metadata"])
    flag = 1 if published else 0
    return (
        "INSERT INTO puzzles ("
        "play_date, category, game_slug, schema_version, payload, solution, metadata, published"
        ") VALUES ("
        f"{_quote(str(document['play_date']))}, {_quote(str(document['category']))}, "
        f"{_quote(str(document['game_slug']))}, {_quote(str(document['schema_version']))}, "
        f"{_quote(payload)}, {_quote(solution)}, {_quote(metadata)}, {flag}"
        ") ON CONFLICT (play_date, category, game_slug) DO UPDATE SET "
        "schema_version = excluded.schema_version, "
        "payload = excluded.payload, "
        "solution = excluded.solution, "
        "metadata = excluded.metadata, "
        "published = excluded.published;"
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
