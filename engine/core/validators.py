"""Validation stricte du document puzzle. Rejette toute forme non conforme."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Literal, cast

from engine.core.exceptions import PuzzleValidationError, UnsolvablePuzzleError
from engine.core.models import (
    SCHEMA_VERSION,
    Category,
    Difficulty,
    GeoOption,
    ItinerairePayload,
    ItinerairePuzzle,
    ItineraireSolution,
    LocalizedText,
    MapBounds,
    PuzzleMetadata,
)

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_OPTION_ID = re.compile(r"opt_[a-z0-9]+")
_CATEGORIES = frozenset({"geo", "foot", "movies"})
_DIFFICULTIES = frozenset({"easy", "medium", "hard"})

_DOCUMENT_KEYS = frozenset(
    {"play_date", "category", "game_slug", "schema_version", "payload", "solution", "metadata"}
)
_PAYLOAD_KEYS = frozenset({"prompt", "options", "map_bounds", "max_attempts"})
_OPTION_KEYS = frozenset({"id", "label", "coordinates"})
_BOUNDS_KEYS = frozenset({"north", "south", "east", "west"})
_SOLUTION_KEYS = frozenset({"correct_option_id", "explanation", "distance_tolerance_km"})
_METADATA_KEYS = frozenset({"generator_version", "generated_at", "difficulty", "seed"})
_LOCALE_KEYS = frozenset({"fr", "en"})


def validate_puzzle_document(document: Mapping[str, object]) -> ItinerairePuzzle:
    """Parse le document puis vérifie qu'il est résolvable."""
    puzzle = parse_puzzle_document(document)
    assert_solvable(puzzle)
    return puzzle


def parse_puzzle_document(document: Mapping[str, object]) -> ItinerairePuzzle:
    """Construit un puzzle typé ou lève PuzzleValidationError."""
    if not isinstance(document, Mapping):
        raise PuzzleValidationError("objet JSON attendu", field="document")
    _expect_exact_keys(document, _DOCUMENT_KEYS, "document")

    play_date = _parse_play_date(document["play_date"])
    category = _parse_category(document["category"])
    game_slug = _parse_slug(document["game_slug"], field="game_slug")
    schema_version = _parse_semver(document["schema_version"], field="schema_version")
    if schema_version != SCHEMA_VERSION:
        raise PuzzleValidationError(
            f"version {SCHEMA_VERSION} attendue",
            field="schema_version",
        )

    if category != "geo" or game_slug != "itineraire":
        raise PuzzleValidationError(
            "seul geo/itineraire est pris en charge",
            field="game_slug",
        )

    payload_raw = _expect_mapping(document["payload"], "payload")
    solution_raw = _expect_mapping(document["solution"], "solution")
    metadata_raw = _expect_mapping(document["metadata"], "metadata")
    return ItinerairePuzzle(
        play_date=play_date,
        category=category,
        game_slug=game_slug,
        schema_version=schema_version,
        payload=_parse_payload(payload_raw),
        solution=_parse_solution(solution_raw),
        metadata=_parse_metadata(metadata_raw),
    )


def assert_solvable(puzzle: ItinerairePuzzle) -> None:
    """La bonne réponse doit être une des options proposées."""
    option_ids = [option.id for option in puzzle.payload.options]
    if len(option_ids) < 2:
        raise UnsolvablePuzzleError("il faut au moins deux options")
    if len(option_ids) != len(set(option_ids)):
        raise UnsolvablePuzzleError("identifiants d'options en double")
    if puzzle.solution.correct_option_id not in option_ids:
        raise UnsolvablePuzzleError(
            f"{puzzle.solution.correct_option_id} absent des options"
        )


def parse_coordinates(value: object, *, field: str) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)) or len(value) != 2:
        raise PuzzleValidationError("paire [latitude, longitude] attendue", field=field)
    latitude = _parse_float(value[0], field=f"{field}[0]")
    longitude = _parse_float(value[1], field=f"{field}[1]")
    if not -90.0 <= latitude <= 90.0:
        raise PuzzleValidationError("latitude hors de [-90, 90]", field=f"{field}[0]")
    if not -180.0 <= longitude <= 180.0:
        raise PuzzleValidationError("longitude hors de [-180, 180]", field=f"{field}[1]")
    return (latitude, longitude)


def _parse_payload(raw: Mapping[str, object]) -> ItinerairePayload:
    _expect_exact_keys(raw, _PAYLOAD_KEYS, "payload")
    options_raw = raw["options"]
    if not isinstance(options_raw, list) or not options_raw:
        raise PuzzleValidationError("liste d'options non vide attendue", field="payload.options")
    options = tuple(
        _parse_option(item, field=f"payload.options[{index}]")
        for index, item in enumerate(options_raw)
    )
    bounds_raw = _expect_mapping(raw["map_bounds"], "payload.map_bounds")
    max_attempts = _parse_int(raw["max_attempts"], field="payload.max_attempts")
    if not 1 <= max_attempts <= 20:
        raise PuzzleValidationError("entier entre 1 et 20 attendu", field="payload.max_attempts")
    return ItinerairePayload(
        prompt=_parse_localized(raw["prompt"], field="payload.prompt"),
        options=options,
        map_bounds=_parse_bounds(bounds_raw),
        max_attempts=max_attempts,
    )


def _parse_option(value: object, *, field: str) -> GeoOption:
    raw = _expect_mapping(value, field)
    _expect_exact_keys(raw, _OPTION_KEYS, field)
    option_id = raw["id"]
    if not isinstance(option_id, str) or _OPTION_ID.fullmatch(option_id) is None:
        raise PuzzleValidationError("identifiant d'option invalide", field=f"{field}.id")
    return GeoOption(
        id=option_id,
        label=_parse_localized(raw["label"], field=f"{field}.label"),
        coordinates=parse_coordinates(raw["coordinates"], field=f"{field}.coordinates"),
    )


def _parse_bounds(raw: Mapping[str, object]) -> MapBounds:
    _expect_exact_keys(raw, _BOUNDS_KEYS, "payload.map_bounds")
    bounds = MapBounds(
        north=_parse_float(raw["north"], field="payload.map_bounds.north"),
        south=_parse_float(raw["south"], field="payload.map_bounds.south"),
        east=_parse_float(raw["east"], field="payload.map_bounds.east"),
        west=_parse_float(raw["west"], field="payload.map_bounds.west"),
    )
    if bounds.north <= bounds.south:
        raise PuzzleValidationError("north doit être > south", field="payload.map_bounds")
    if bounds.east <= bounds.west:
        raise PuzzleValidationError("east doit être > west", field="payload.map_bounds")
    return bounds


def _parse_solution(raw: Mapping[str, object]) -> ItineraireSolution:
    _expect_exact_keys(raw, _SOLUTION_KEYS, "solution")
    correct = raw["correct_option_id"]
    if not isinstance(correct, str) or _OPTION_ID.fullmatch(correct) is None:
        raise PuzzleValidationError("identifiant invalide", field="solution.correct_option_id")
    tolerance = _parse_float(raw["distance_tolerance_km"], field="solution.distance_tolerance_km")
    if tolerance <= 0:
        raise PuzzleValidationError("tolérance positive attendue", field="solution.distance_tolerance_km")
    return ItineraireSolution(
        correct_option_id=correct,
        explanation=_parse_localized(raw["explanation"], field="solution.explanation"),
        distance_tolerance_km=tolerance,
    )


def _parse_metadata(raw: Mapping[str, object]) -> PuzzleMetadata:
    _expect_exact_keys(raw, _METADATA_KEYS, "metadata")
    difficulty = raw["difficulty"]
    if not isinstance(difficulty, str) or difficulty not in _DIFFICULTIES:
        raise PuzzleValidationError(
            "easy, medium ou hard attendu",
            field="metadata.difficulty",
        )
    seed = raw["seed"]
    if not isinstance(seed, str) or not seed.strip():
        raise PuzzleValidationError("graine non vide attendue", field="metadata.seed")
    return PuzzleMetadata(
        generator_version=_parse_semver(raw["generator_version"], field="metadata.generator_version"),
        generated_at=_parse_datetime(raw["generated_at"]),
        difficulty=cast(Difficulty, difficulty),
        seed=seed,
    )


def _parse_localized(value: object, *, field: str) -> LocalizedText:
    if isinstance(value, str):
        if not value.strip():
            raise PuzzleValidationError("texte vide", field=field)
        return value
    raw = _expect_mapping(value, field)
    _expect_exact_keys(raw, _LOCALE_KEYS, field)
    translated: dict[Literal["fr", "en"], str] = {"fr": "", "en": ""}
    for locale in ("fr", "en"):
        text = raw[locale]
        if not isinstance(text, str) or not text.strip():
            raise PuzzleValidationError("traduction non vide attendue", field=f"{field}.{locale}")
        translated[locale] = text
    return translated


def _parse_play_date(value: object) -> date:
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise PuzzleValidationError("date AAAA-MM-JJ attendue", field="play_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise PuzzleValidationError("date calendaire invalide", field="play_date") from exc
    return parsed


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PuzzleValidationError("horodatage ISO attendu", field="metadata.generated_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PuzzleValidationError("horodatage ISO invalide", field="metadata.generated_at") from exc
    if parsed.tzinfo is None:
        raise PuzzleValidationError("fuseau horaire attendu", field="metadata.generated_at")
    return parsed


def _parse_category(value: object) -> Category:
    if not isinstance(value, str) or value not in _CATEGORIES:
        raise PuzzleValidationError("geo, foot ou movies attendu", field="category")
    return cast(Category, value)


def _parse_slug(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise PuzzleValidationError("slug minuscule attendu", field=field)
    return value


def _parse_semver(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SEMVER.fullmatch(value) is None:
        raise PuzzleValidationError("semver attendu", field=field)
    return value


def _parse_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PuzzleValidationError("entier attendu", field=field)
    return value


def _parse_float(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PuzzleValidationError("nombre attendu", field=field)
    return float(value)


def _expect_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PuzzleValidationError("objet JSON attendu", field=field)
    return cast(Mapping[str, object], value)


def _expect_exact_keys(raw: Mapping[str, object], expected: frozenset[str], field: str) -> None:
    missing = expected - raw.keys()
    extra = set(raw.keys()) - expected
    if missing or extra:
        raise PuzzleValidationError(
            f"clés manquantes={sorted(missing)} en trop={sorted(extra)}",
            field=field,
        )
