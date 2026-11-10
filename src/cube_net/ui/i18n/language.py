"""`Language`: the languages the application speaks."""

from enum import Enum


class Language(Enum):
    ENGLISH = "en"
    RUSSIAN = "ru"

    @property
    def native_name(self) -> str:
        """The language's name in that language (how it's listed: the same in every language)."""
        return {Language.ENGLISH: "English", Language.RUSSIAN: "Русский"}[self]
