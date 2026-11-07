"""Le garde-fou CI refuse un lot vide, mal formé ou non résolvable."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from engine.core.exceptions import PuzzleValidationError
from engine.core.models import puzzle_to_dict
from engine.geo.itineraire.generator import generate_itineraire
from scripts.db_client import render_upsert
from scripts.validate_batch import BatchValidationError, main, validate_batch


def _document() -> dict[str, object]:
    return puzzle_to_dict(generate_itineraire(date(2026, 11, 7)))


def test_accepts_a_generated_batch() -> None:
    validate_batch([_document()])


def test_rejects_an_empty_batch() -> None:
    with pytest.raises(BatchValidationError):
        validate_batch([])


def test_rejects_a_missing_correct_option() -> None:
    document = _document()
    solution = document["solution"]
    assert isinstance(solution, dict)
    solution["correct_option_id"] = "opt_missing"
    with pytest.raises(BatchValidationError, match="absent des options"):
        validate_batch([document])


def test_rejects_a_partial_translation() -> None:
    document = _document()
    payload = document["payload"]
    assert isinstance(payload, dict)
    payload["prompt"] = {"fr": "Seulement le français"}
    with pytest.raises(PuzzleValidationError):
        from engine.core.validators import parse_puzzle_document

        parse_puzzle_document(document)


def test_cli_accepts_and_rejects(tmp_path: Path) -> None:
    ok_path = tmp_path / "ok.json"
    ok_path.write_text(json.dumps([_document()], ensure_ascii=False), encoding="utf-8")
    assert main([str(ok_path)]) == 0

    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{}", encoding="utf-8")
    assert main([str(bad_path)]) == 1


def test_upsert_targets_the_public_key() -> None:
    sql = render_upsert(_document(), published=True)
    assert "ON CONFLICT (play_date, category, game_slug)" in sql
    assert sql.rstrip().endswith("published = excluded.published;")
    assert ", 1)" in sql
