"""Valide un lot JSON avant insertion. Échoue si un puzzle est non conforme ou non résolvable."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from engine.core.exceptions import DailyQuizError, PuzzleValidationError, UnsolvablePuzzleError
from engine.core.validators import validate_puzzle_document

logger = logging.getLogger(__name__)


class BatchValidationError(DailyQuizError):
    """Un ou plusieurs puzzles du lot sont refusés."""

    def __init__(self, errors: tuple[str, ...]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_batch(documents: Sequence[object]) -> None:
    if isinstance(documents, (str, bytes)) or not isinstance(documents, Sequence):
        raise BatchValidationError(("le lot doit être une liste",))
    if len(documents) == 0:
        raise BatchValidationError(("le lot est vide",))

    errors: list[str] = []
    for index, document in enumerate(documents):
        if not isinstance(document, Mapping):
            logger.error("puzzle %s : objet JSON attendu", index)
            errors.append(f"[{index}] objet JSON attendu")
            continue
        try:
            validate_puzzle_document(document)
        except (PuzzleValidationError, UnsolvablePuzzleError) as exc:
            logger.error("puzzle %s invalide : %s", index, exc)
            errors.append(f"[{index}] {exc}")
    if errors:
        raise BatchValidationError(tuple(errors))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Valide un fichier JSON de puzzles.")
    parser.add_argument("batch", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.batch.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("lecture du lot impossible : %s", args.batch)
        return 1
    try:
        validate_batch(raw)
    except BatchValidationError as exc:
        logger.error("lot rejeté\n%s", exc)
        return 1
    logger.info("lot valide (%s puzzles) : %s", len(raw), args.batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
