# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.core.template import ValidationStatus
from cube_net.ui import palette
from cube_net.ui.instruments.button_look import tool_buttons_style
from cube_net.ui.template.validate_button import ValidateButton


@pytest.fixture
def toolbar(qtbot: QtBot) -> QToolBar:
    """A vertical panel, as the instrument panel is."""
    toolbar = QToolBar()
    toolbar.setOrientation(Qt.Orientation.Vertical)
    toolbar.setStyleSheet(tool_buttons_style())
    qtbot.addWidget(toolbar)
    return toolbar


@pytest.fixture
def button(toolbar: QToolBar, qtbot: QtBot) -> ValidateButton:
    button = ValidateButton(toolbar)
    toolbar.show()
    qtbot.waitExposed(toolbar)
    return button


@pytest.mark.parametrize(
    ("status", "text"),
    [
        (ValidationStatus.UNDEFINED, "Validate\ntemplate"),
        (ValidationStatus.VALID, "Validated"),
        (ValidationStatus.INVALID, "Invalid"),
    ],
)
def test_it_says_the_status(button: ValidateButton, status: ValidationStatus, text: str) -> None:
    button.set_status(status)
    assert button.button.text() == text
    assert button.button.toolTip() == "Hotkey: V"


def test_square_and_as_wide_as_the_panel(button: ValidateButton, toolbar: QToolBar, qtbot: QtBot) -> None:
    widget = button.button
    qtbot.waitUntil(lambda: widget.height() == widget.width())
    assert widget.width() >= toolbar.width() - 12


def test_clicked(button: ValidateButton, qtbot: QtBot) -> None:
    with qtbot.waitSignal(button.clicked):
        button.button.click()
    button.set_enabled(False)
    assert not button.button.isEnabled()


def test_the_same_size_whatever_it_says(button: ValidateButton) -> None:
    hints = set()
    for status in ValidationStatus:
        button.set_status(status)
        hints.add(button.button.sizeHint())
    assert len(hints) == 1
    (hint,) = hints
    assert hint.width() == hint.height()


def test_valid_is_green_and_invalid_red(button: ValidateButton) -> None:
    button.set_status(ValidationStatus.VALID)
    assert palette.VALID_BUTTON_BOTTOM.name() in button.button.styleSheet()
    button.set_status(ValidationStatus.INVALID)
    assert palette.INVALID_BUTTON_BOTTOM.name() in button.button.styleSheet()
    button.set_status(ValidationStatus.UNDEFINED)
    assert button.button.styleSheet() == ""  # the panel's look
