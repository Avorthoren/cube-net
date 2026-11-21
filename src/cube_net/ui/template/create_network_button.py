# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CreateNetworkButton`: the instrument panel's square button below Validate while a template is made, as large as
Validate's: "Create" / "network" on two lines, in its middle. It starts a new project from the template as it is (as
File -> New -> Custom template does from its file); it can be clicked only while the template is validated
(`set_enabled`)."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QToolButton

from cube_net.ui.i18n import TRANSLATIONS, tr
from cube_net.ui.template.validate_button import SquareButton


class CreateNetworkButton(QObject):
    # Clicked (start a project from the template).
    clicked = pyqtSignal()

    def __init__(self, toolbar: QToolBar) -> None:
        super().__init__(toolbar)
        self.button = SquareButton(toolbar)
        self.button.clicked.connect(self.clicked)
        self.action: QAction = toolbar.addWidget(self.button)
        TRANSLATIONS.changed.connect(self._show)
        self._show()

    def set_visible(self, visible: bool) -> None:
        self.action.setVisible(visible)

    def set_enabled(self, enabled: bool) -> None:
        self.button.setEnabled(enabled)

    def _show(self) -> None:
        self.button.setText(tr("Create\nnetwork"))
        self.button.least_width = QToolButton.sizeHint(self.button).width()
        self.button.updateGeometry()
