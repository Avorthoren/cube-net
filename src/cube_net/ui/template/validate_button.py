# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ValidateButton`: the instrument panel's square button below Net area while a template is made
(docs/template_plan.md, §8.2), nearly as wide as the panel. It says the template's validation status and validates
it (as V does):

- Undefined: "Validate" / "template", on two lines; it can be clicked;
- Valid: "Validated"; it can't (there's nothing to validate again);
- Invalid: "Invalid"; it can, to validate again and see what's wrong.

Valid is a muted green, Invalid a muted red. Its size is the same whatever it says (the widest of the three texts in
the language shown), so the panel doesn't change its width with the status.

Whether it can be clicked is the Validate action's (`set_enabled`): never while the loop isn't closed."""

from PyQt6.QtCore import QObject, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QResizeEvent
from PyQt6.QtWidgets import QSizePolicy, QToolBar, QToolButton, QWidget

from cube_net.core.template import ValidationStatus
from cube_net.ui import palette
from cube_net.ui.i18n import TRANSLATIONS, bind, tr
from cube_net.ui.instruments.button_look import colored_button_style


class SquareButton(QToolButton):
    """A button as high as it's wide; it takes the panel's width."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # At least this wide (the widest of the texts it may show).
        self.least_width = 0

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        width = max(hint.width(), self.least_width)
        return QSize(width, width)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        if self.height() != self.width():
            self.setFixedHeight(self.width())


class ValidateButton(QObject):
    # Clicked (validate the template).
    clicked = pyqtSignal()

    def __init__(self, toolbar: QToolBar, with_separator: bool = True) -> None:
        super().__init__(toolbar)
        self._status = ValidationStatus.UNDEFINED
        # The line between Net area and the button (None: another button above it has it).
        self.separator: QAction | None = toolbar.addSeparator() if with_separator else None
        self.button = SquareButton(toolbar)
        bind(self.button, self.button.setToolTip, "Hotkey: V")  # its key (see `MainWindow`)
        self.button.clicked.connect(self.clicked)
        self.action: QAction = toolbar.addWidget(self.button)
        TRANSLATIONS.changed.connect(self._show)
        self._show()

    def set_visible(self, visible: bool) -> None:
        if self.separator is not None:
            self.separator.setVisible(visible)
        self.action.setVisible(visible)

    @property
    def status(self) -> ValidationStatus:
        return self._status

    def set_status(self, status: ValidationStatus) -> None:
        self._status = status
        self._show()

    def set_enabled(self, enabled: bool) -> None:
        self.button.setEnabled(enabled)

    def _show(self) -> None:
        texts = {
            ValidationStatus.UNDEFINED: tr("Validate\ntemplate"),
            ValidationStatus.VALID: tr("Validated"),
            ValidationStatus.INVALID: tr("Invalid"),
        }
        if self._status is ValidationStatus.VALID:
            style = colored_button_style(
                palette.VALID_BUTTON_TOP,
                palette.VALID_BUTTON_BOTTOM,
                palette.VALID_BUTTON_BOTTOM,
                palette.VALID_BUTTON_TOP,
            )  # it can't be clicked
        elif self._status is ValidationStatus.INVALID:
            style = colored_button_style(
                palette.INVALID_BUTTON_TOP,
                palette.INVALID_BUTTON_BOTTOM,
                palette.INVALID_BUTTON_HOVER_BOTTOM,
                palette.INVALID_BUTTON_DOWN_TOP,
            )
        else:
            style = ""  # the panel's
        self.button.setStyleSheet(style)
        least = 0  # in its look now (the same room inside the outline in every look)
        for text in texts.values():  # each one's size, as the button would want it
            self.button.setText(text)
            least = max(least, QToolButton.sizeHint(self.button).width())
        self.button.least_width = least
        self.button.setText(texts[self._status])
        self.button.updateGeometry()
