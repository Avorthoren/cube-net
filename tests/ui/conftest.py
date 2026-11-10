# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import gc
from collections.abc import Iterator

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent


@pytest.fixture(autouse=True)
def collect_garbage_only_between_tests() -> Iterator[None]:
    """Qt crashes when Python's collector frees what's left of dead windows in the middle of another window's paint.

    It takes many windows: a real session has one, which lives as long as the app, and that one is fine with the
    collector running all the time. Tests leave dead windows behind, so in tests the collector works only here, while
    nothing is being painted. pytest-qt closes a test's windows before this fixture ends, so that's covered too.
    """
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
    gc.disable()
    yield
    gc.enable()


@pytest.fixture(autouse=True)
def default_style() -> Iterator[None]:
    """A test may change the style (it's global): the next one starts with the defaults again."""
    from cube_net.ui.style import DEFAULT_STYLE, apply_style

    apply_style(DEFAULT_STYLE)
    yield
    apply_style(DEFAULT_STYLE)


@pytest.fixture(autouse=True)
def english_and_own_settings(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Every test starts in English, and app settings it doesn't give explicitly don't come from the user's own file."""
    from PyQt6.QtCore import QSettings

    from cube_net.ui.i18n import TRANSLATIONS, Language

    folder = str(tmp_path_factory.mktemp("settings"))
    for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
        QSettings.setPath(QSettings.Format.NativeFormat, scope, folder)
    TRANSLATIONS.set_language(Language.ENGLISH)
    yield
    TRANSLATIONS.set_language(Language.ENGLISH)


@pytest.fixture(autouse=True)
def no_modifiers_held(qapp: object) -> None:
    """The test platform remembers the modifiers of the latest input event, and a window that becomes active reads
    them (`SheetView.eventFilter`): a Shift+click of one test would hold SHIFT in the next. A key press without
    modifiers forgets them. (`qapp`: the application, which a widget needs, even in a test that has no window.)"""
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QWidget

    QTest.keyClick(QWidget(), Qt.Key.Key_A)
