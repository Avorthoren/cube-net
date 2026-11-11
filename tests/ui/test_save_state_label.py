# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pytestqt.qtbot import QtBot

from cube_net.ui import palette
from cube_net.ui.i18n import TRANSLATIONS, Language
from cube_net.ui.save_state_label import SaveStateLabel


def make(qtbot: QtBot) -> SaveStateLabel:
    label = SaveStateLabel()
    qtbot.addWidget(label)
    return label


def test_its_three_states(qtbot: QtBot) -> None:
    label = make(qtbot)
    assert label.text() == ""  # a new project nobody has changed
    label.set_state(dirty=True, has_file=False)
    assert label.text() == "Unsaved changes" and palette.UNSAVED.name() in label.styleSheet()
    label.set_state(dirty=False, has_file=True)
    assert label.text() == "Saved"
    label.set_state(dirty=True, has_file=True)
    assert label.text() == "Unsaved changes"


def test_as_wide_as_its_longest_text(qtbot: QtBot) -> None:
    label = make(qtbot)
    width = label.minimumWidth()
    label.set_state(dirty=True, has_file=True)
    assert label.minimumWidth() == width >= label.fontMetrics().horizontalAdvance("Unsaved changes")


def test_in_russian(qtbot: QtBot) -> None:
    label = make(qtbot)
    label.set_state(dirty=True, has_file=True)
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert label.text() == "Не сохранено"
    assert label.minimumWidth() >= label.fontMetrics().horizontalAdvance("Не сохранено")
