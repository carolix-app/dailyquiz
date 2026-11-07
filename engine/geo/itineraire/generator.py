"""Générateur déterministe du jeu geo/itineraire.

La graine est le SHA-256 de ``play_date`` concaténé à ``game_slug``.
Le puzzle reste résolvable : ``correct_option_id`` désigne toujours une option,
et la distance annoncée (arrondie à 10 km) n'est partagée par aucun leurre.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path

from engine.core.exceptions import CityDataError, PuzzleValidationError, UnsolvablePuzzleError
from engine.core.models import (
    GENERATOR_VERSION,
    SCHEMA_VERSION,
    Difficulty,
    GeoOption,
    ItinerairePayload,
    ItinerairePuzzle,
    ItineraireSolution,
    MapBounds,
    PuzzleMetadata,
    TranslatedText,
)
from engine.core.validators import assert_solvable, parse_coordinates

logger = logging.getLogger(__name__)

GAME_SLUG = "itineraire"
CATEGORY = "geo"
MAX_ATTEMPTS = 6
DISTANCE_TOLERANCE_KM = 10.0
ROUNDED_GAP_KM = 20
OPTION_IDS = ("opt_a", "opt_b", "opt_c", "opt_d")
DATA_PATH = Path(__file__).resolve().parent / "data" / "villes.json"
_EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True, slots=True)
class City:
    id: str
    label: TranslatedText
    coordinates: tuple[float, float]


def stable_seed(play_date: date, game_slug: str) -> int:
    """Entier stable entre processus. ``hash()`` n'est pas utilisable : il est salé."""
    material = f"{play_date.isoformat()}{game_slug}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def generate_itineraire(
    play_date: date,
    *,
    cities: tuple[City, ...] | None = None,
) -> ItinerairePuzzle:
    catalog = cities if cities is not None else load_cities()
    if len(catalog) < 5:
        raise UnsolvablePuzzleError("Pas assez de villes pour construire un itinéraire.")
    if len({city.id for city in catalog}) != len(catalog):
        raise UnsolvablePuzzleError("Identifiants de villes en double.")

    rng = random.Random(stable_seed(play_date, GAME_SLUG))
    order = list(catalog)
    rng.shuffle(order)
    selection = _select_route(order)
    if selection is None:
        raise UnsolvablePuzzleError(f"Aucun itinéraire univoque pour {play_date.isoformat()}.")
    origin, correct, distractors, distance_km = selection

    options_cities = [correct, *distractors]
    rng.shuffle(options_cities)
    options = tuple(
        GeoOption(id=option_id, label=city.label, coordinates=city.coordinates)
        for option_id, city in zip(OPTION_IDS, options_cities, strict=True)
    )
    correct_option_id = next(
        option.id
        for option, city in zip(options, options_cities, strict=True)
        if city.id == correct.id
    )
    rounded_km = int(round(distance_km / DISTANCE_TOLERANCE_KM) * DISTANCE_TOLERANCE_KM)
    puzzle = ItinerairePuzzle(
        play_date=play_date,
        category=CATEGORY,
        game_slug=GAME_SLUG,
        schema_version=SCHEMA_VERSION,
        payload=ItinerairePayload(
            prompt={
                "fr": (
                    f"Vous partez de {origin.label['fr']}. "
                    f"Quelle est l'étape du jour, à environ {rounded_km} km ?"
                ),
                "en": (
                    f"You set out from {origin.label['en']}. "
                    f"Which city is today's stop, about {rounded_km} km away?"
                ),
            },
            options=options,
            map_bounds=_bounds([origin.coordinates, *(city.coordinates for city in options_cities)]),
            max_attempts=MAX_ATTEMPTS,
        ),
        solution=ItineraireSolution(
            correct_option_id=correct_option_id,
            explanation={
                "fr": (
                    f"L'étape est {correct.label['fr']}, "
                    f"à {round(distance_km)} km de {origin.label['fr']}."
                ),
                "en": (
                    f"The stop is {correct.label['en']}, "
                    f"{round(distance_km)} km from {origin.label['en']}."
                ),
            },
            distance_tolerance_km=DISTANCE_TOLERANCE_KM,
        ),
        metadata=PuzzleMetadata(
            generator_version=GENERATOR_VERSION,
            generated_at=datetime.combine(play_date, time.min, tzinfo=timezone.utc),
            difficulty=_difficulty(origin, correct, distractors),
            seed=f"{CATEGORY}-{GAME_SLUG}-{play_date.isoformat()}",
        ),
    )
    assert_solvable(puzzle)
    return puzzle


@lru_cache(maxsize=1)
def load_cities() -> tuple[City, ...]:
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Lecture impossible du catalogue %s", DATA_PATH)
        raise CityDataError(str(DATA_PATH)) from exc
    if not isinstance(raw, list) or len(raw) < 5:
        raise CityDataError("Le catalogue doit contenir au moins cinq villes.")

    cities: list[City] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        field = f"villes[{index}]"
        if not isinstance(item, dict):
            raise CityDataError(f"{field} doit être un objet.")
        city_id = item.get("id")
        label = item.get("label")
        if not isinstance(city_id, str) or not city_id or city_id in seen:
            raise CityDataError(f"{field}.id est vide ou déjà utilisé.")
        if not isinstance(label, dict):
            raise CityDataError(f"{field}.label doit être traduit.")
        fr = label.get("fr")
        en = label.get("en")
        if not isinstance(fr, str) or not isinstance(en, str) or not fr.strip() or not en.strip():
            raise CityDataError(f"{field}.label doit fournir fr et en.")
        try:
            coordinates = parse_coordinates(item.get("coordinates"), field=f"{field}.coordinates")
        except PuzzleValidationError as exc:
            logger.error("Coordonnées invalides dans %s : %s", DATA_PATH, exc)
            raise CityDataError(str(exc)) from exc
        seen.add(city_id)
        cities.append(City(id=city_id, label={"fr": fr, "en": en}, coordinates=coordinates))
    return tuple(cities)


def haversine_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    lat1, lon1 = origin
    lat2, lon2 = destination
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(haversine)))


def _select_route(
    order: list[City],
) -> tuple[City, City, tuple[City, City, City], float] | None:
    for origin in order:
        scored = sorted(
            (city for city in order if city.id != origin.id),
            key=lambda city: haversine_km(origin.coordinates, city.coordinates),
        )
        for correct in reversed(scored):
            distance = haversine_km(origin.coordinates, correct.coordinates)
            target = int(round(distance / DISTANCE_TOLERANCE_KM) * DISTANCE_TOLERANCE_KM)
            if target < DISTANCE_TOLERANCE_KM:
                continue
            distractors: list[City] = []
            for candidate in scored:
                if candidate.id == correct.id:
                    continue
                rounded = int(
                    round(
                        haversine_km(origin.coordinates, candidate.coordinates)
                        / DISTANCE_TOLERANCE_KM
                    )
                    * DISTANCE_TOLERANCE_KM
                )
                if abs(rounded - target) >= ROUNDED_GAP_KM:
                    distractors.append(candidate)
                if len(distractors) == 3:
                    return origin, correct, (distractors[0], distractors[1], distractors[2]), distance
    return None


def _bounds(points: list[tuple[float, float]]) -> MapBounds:
    padding = 2.0
    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]
    north = min(90.0, max(latitudes) + padding)
    south = max(-90.0, min(latitudes) - padding)
    east = min(180.0, max(longitudes) + padding)
    west = max(-180.0, min(longitudes) - padding)
    if north <= south or east <= west:
        raise UnsolvablePuzzleError("Emprise de carte dégénérée.")
    return MapBounds(north=north, south=south, east=east, west=west)


def _difficulty(origin: City, correct: City, distractors: tuple[City, City, City]) -> Difficulty:
    correct_distance = haversine_km(origin.coordinates, correct.coordinates)
    nearest_gap = min(
        abs(haversine_km(origin.coordinates, city.coordinates) - correct_distance)
        for city in distractors
    )
    if nearest_gap < 150:
        return "hard"
    if nearest_gap < 400:
        return "medium"
    return "easy"
