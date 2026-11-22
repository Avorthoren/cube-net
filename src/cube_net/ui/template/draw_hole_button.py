# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`DrawHoleButton`: the instrument panel's square button above Validate while a template is made
(docs/template_plan.md, §8.5), as large as Validate's: "Draw" / "hole" on two lines, in its middle. It starts drawing a
hole (as H does); whether it can be clicked is the Draw hole action's (`set_enabled`): only while nothing else is
being drawn or dragged."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QToolButton

from cube_net.ui.i18n import TRANSLATIONS, bind, tr
from cube_net.ui.template.validate_button import SquareButton


class DrawHoleButton(QObject):
    # Clicked (start drawing a hole).
    clicked = pyqtSignal()

    def __init__(self, toolbar: QToolBar) -> None:
        super().__init__(toolbar)
        # The line between Net area and the template's buttons.
        self.separator: QAction = toolbar.addSeparator()
        self.button = SquareButton(toolbar)
        bind(self.button, self.button.setToolTip, "Hotkey: H")  # its key (see `MainWindow`)
        self.button.clicked.connect(self.clicked)
        self.action: QAction = toolbar.addWidget(self.button)
        TRANSLATIONS.changed.connect(self._show)
        self._show()

    def set_visible(self, visible: bool) -> None:
        self.separator.setVisible(visible)
        self.action.setVisible(visible)

    def set_enabled(self, enabled: bool) -> None:
        self.button.setEnabled(enabled)

    def _show(self) -> None:
        self.button.setText(tr("Draw\nhole"))
        self.button.least_width = QToolButton.sizeHint(self.button).width()
        self.button.updateGeometry()
