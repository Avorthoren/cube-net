# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Iterator

import pytest
from pytestqt.qtbot import QtBot

from cube_net.ui.i18n import TRANSLATIONS, Language
from cube_net.ui.language_box import LanguageBox


@pytest.fixture(autouse=True)
def english() -> Iterator[None]:
    yield
    TRANSLATIONS.set_language(Language.ENGLISH)


def make(qtbot: QtBot, language: Language = Language.ENGLISH) -> LanguageBox:
    box = LanguageBox(language)
    qtbot.addWidget(box)
    return box


def test_every_language_in_its_own_words(qtbot: QtBot) -> None:
    box = make(qtbot, Language.RUSSIAN)
    assert [box.itemText(i) for i in range(box.count())] == [known.native_name for known in Language]
    assert box.currentData() is Language.RUSSIAN


def test_the_users_choice_is_told(qtbot: QtBot) -> None:
    box = make(qtbot)
    chosen: list[Language] = []
    box.chosen.connect(chosen.append)
    box.setCurrentIndex(list(Language).index(Language.RUSSIAN))
    assert chosen == [Language.RUSSIAN]


def test_follows_a_change_made_elsewhere_without_telling_it(qtbot: QtBot) -> None:
    box, other = make(qtbot), make(qtbot)
    chosen: list[Language] = []
    box.chosen.connect(chosen.append)
    TRANSLATIONS.set_language(Language.RUSSIAN)  # as the other list would, through the window
    assert box.currentData() is Language.RUSSIAN and other.currentData() is Language.RUSSIAN
    assert chosen == []
