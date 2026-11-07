"""Erreurs métier. Aucune n'est levée pour masquer un échec silencieux."""

from __future__ import annotations


class DailyQuizError(Exception):
    """Erreur métier DailyQuiz."""


class PuzzleValidationError(DailyQuizError):
    """Document ou instance qui ne respecte pas le contrat du puzzle."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}" if field else message)


class UnsolvablePuzzleError(DailyQuizError):
    """Le puzzle n'a pas de solution présente dans ses options."""


class CityDataError(DailyQuizError):
    """Le catalogue de villes est illisible ou incohérent."""


class UnknownGameError(DailyQuizError):
    """Aucun générateur n'est enregistré pour ce couple catégorie / jeu."""
