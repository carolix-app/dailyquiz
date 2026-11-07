"""Répartiteur des jeux de la catégorie géographie."""

from __future__ import annotations

from datetime import date

from engine.core.exceptions import UnknownGameError
from engine.core.models import ItinerairePuzzle
from engine.geo.itineraire.generator import generate_itineraire


def generate_geo(play_date: date, game_slug: str) -> ItinerairePuzzle:
    if game_slug == "itineraire":
        return generate_itineraire(play_date)
    raise UnknownGameError(f"Jeu géo inconnu : {game_slug}")
