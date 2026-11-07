"""Cent puzzles, cent dates : chacun reste résolvable et conforme au contrat."""

from __future__ import annotations

from datetime import date, timedelta

from engine.core.models import puzzle_to_dict
from engine.core.validators import assert_solvable, validate_puzzle_document
from engine.geo.itineraire.generator import generate_itineraire


def test_hundred_dates_keep_the_correct_option() -> None:
    start = date(2026, 1, 1)
    seeds: set[str] = set()
    for offset in range(100):
        play_date = start + timedelta(days=offset)
        puzzle = generate_itineraire(play_date)
        option_ids = [option.id for option in puzzle.payload.options]
        assert puzzle.solution.correct_option_id in option_ids
        assert len(option_ids) == len(set(option_ids)) == 4
        assert puzzle.payload.map_bounds.north > puzzle.payload.map_bounds.south
        assert puzzle.payload.map_bounds.east > puzzle.payload.map_bounds.west
        assert puzzle.metadata.seed == f"geo-itineraire-{play_date.isoformat()}"
        assert_solvable(puzzle)
        restored = validate_puzzle_document(puzzle_to_dict(puzzle))
        assert restored == puzzle
        seeds.add(puzzle.metadata.seed)
    assert len(seeds) == 100


def test_same_date_is_deterministic() -> None:
    play_date = date(2026, 11, 7)
    assert puzzle_to_dict(generate_itineraire(play_date)) == puzzle_to_dict(
        generate_itineraire(play_date)
    )


def test_plain_string_prompt_is_accepted() -> None:
    document = puzzle_to_dict(generate_itineraire(date(2026, 3, 1)))
    payload = document["payload"]
    assert isinstance(payload, dict)
    payload["prompt"] = "Étape du jour"
    puzzle = validate_puzzle_document(document)
    assert puzzle.payload.prompt == "Étape du jour"
