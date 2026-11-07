"""Contrat JSON des puzzles (schéma Draft 2020-12, version 1.0.0).

Les champs texte sont soit une chaîne simple, soit un objet ``{"fr", "en"}``.
La sérialisation produit exactement les clés obligatoires du document.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

SCHEMA_VERSION: str = "1.0.0"
GENERATOR_VERSION: str = "1.0.0"

type Category = Literal["geo", "foot", "movies"]
type Difficulty = Literal["easy", "medium", "hard"]
type TranslatedText = dict[Literal["fr", "en"], str]
type LocalizedText = str | TranslatedText


@dataclass(frozen=True, slots=True)
class MapBounds:
    north: float
    south: float
    east: float
    west: float


@dataclass(frozen=True, slots=True)
class GeoOption:
    id: str
    label: LocalizedText
    coordinates: tuple[float, float]


@dataclass(frozen=True, slots=True)
class ItinerairePayload:
    prompt: LocalizedText
    options: tuple[GeoOption, ...]
    map_bounds: MapBounds
    max_attempts: int


@dataclass(frozen=True, slots=True)
class ItineraireSolution:
    correct_option_id: str
    explanation: LocalizedText
    distance_tolerance_km: float


@dataclass(frozen=True, slots=True)
class PuzzleMetadata:
    generator_version: str
    generated_at: datetime
    difficulty: Difficulty
    seed: str


@dataclass(frozen=True, slots=True)
class Puzzle[PayloadT, SolutionT]:
    play_date: date
    category: Category
    game_slug: str
    schema_version: str
    payload: PayloadT
    solution: SolutionT
    metadata: PuzzleMetadata


type ItinerairePuzzle = Puzzle[ItinerairePayload, ItineraireSolution]


def _dump_localized(value: LocalizedText) -> str | dict[str, str]:
    if isinstance(value, str):
        return value
    return {"fr": value["fr"], "en": value["en"]}


def puzzle_to_dict(puzzle: ItinerairePuzzle) -> dict[str, object]:
    """Sérialise un itinéraire vers le document JSON public et privé."""
    return {
        "play_date": puzzle.play_date.isoformat(),
        "category": puzzle.category,
        "game_slug": puzzle.game_slug,
        "schema_version": puzzle.schema_version,
        "payload": {
            "prompt": _dump_localized(puzzle.payload.prompt),
            "options": [
                {
                    "id": option.id,
                    "label": _dump_localized(option.label),
                    "coordinates": [option.coordinates[0], option.coordinates[1]],
                }
                for option in puzzle.payload.options
            ],
            "map_bounds": {
                "north": puzzle.payload.map_bounds.north,
                "south": puzzle.payload.map_bounds.south,
                "east": puzzle.payload.map_bounds.east,
                "west": puzzle.payload.map_bounds.west,
            },
            "max_attempts": puzzle.payload.max_attempts,
        },
        "solution": {
            "correct_option_id": puzzle.solution.correct_option_id,
            "explanation": _dump_localized(puzzle.solution.explanation),
            "distance_tolerance_km": puzzle.solution.distance_tolerance_km,
        },
        "metadata": {
            "generator_version": puzzle.metadata.generator_version,
            "generated_at": puzzle.metadata.generated_at.isoformat(timespec="seconds"),
            "difficulty": puzzle.metadata.difficulty,
            "seed": puzzle.metadata.seed,
        },
    }
