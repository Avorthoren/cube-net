from collections.abc import Iterator

import pytest
from PyQt6.QtWidgets import QLabel, QMessageBox
from pytestqt.qtbot import QtBot

from cube_net.ui.i18n import TRANSLATIONS, Language, bind, tr
from cube_net.ui.i18n.translator import in_every_language


@pytest.fixture
def russian() -> Iterator[None]:
    TRANSLATIONS.set_language(Language.RUSSIAN)
    yield
    TRANSLATIONS.set_language(Language.ENGLISH)


def test_english_by_default() -> None:
    assert TRANSLATIONS.language is Language.ENGLISH
    assert tr("Ruler") == "Ruler"


def test_russian(russian: None) -> None:
    assert tr("Ruler") == "Линейка"
    assert tr('Save changes to "{name}"?', name="cube.cubenet") == "Сохранить изменения в проекте «cube.cubenet»?"


def test_an_unknown_text_stays_as_it_is(russian: None) -> None:
    assert tr("Something new") == "Something new"


def test_bound_texts_follow_the_language(qtbot: QtBot) -> None:
    label = QLabel()
    qtbot.addWidget(label)
    bind(label, label.setText, "Ruler")
    assert label.text() == "Ruler"
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert label.text() == "Линейка"
    TRANSLATIONS.set_language(Language.ENGLISH)
    assert label.text() == "Ruler"


def test_a_deleted_widget_is_forgotten(qtbot: QtBot) -> None:
    label = QLabel()
    bind(label, label.setText, "Ruler")
    label.deleteLater()
    from PyQt6.QtCore import QCoreApplication, QEvent

    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    TRANSLATIONS.set_language(Language.RUSSIAN)  # doesn't touch it


def test_changed_is_told(qtbot: QtBot) -> None:
    with qtbot.waitSignal(TRANSLATIONS.changed):
        TRANSLATIONS.set_language(Language.RUSSIAN)


def test_qt_own_texts_too(qtbot: QtBot, russian: None) -> None:
    box = QMessageBox()
    qtbot.addWidget(box)
    box.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
    save = box.button(QMessageBox.StandardButton.Save)
    assert save is not None and save.text().replace("&", "") == "Сохранить"


def test_in_every_language() -> None:
    assert in_every_language("Language") == ["Language", "Язык"]
