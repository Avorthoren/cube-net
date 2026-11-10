# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Language`: the languages the application speaks."""

from enum import Enum


class Language(Enum):
    ENGLISH = "en"
    RUSSIAN = "ru"

    @property
    def native_name(self) -> str:
        """The language's name in that language (how it's listed: the same in every language)."""
        return {Language.ENGLISH: "English", Language.RUSSIAN: "Русский"}[self]
