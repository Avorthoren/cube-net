# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The question an AppImage asks once, at its first start: add Cube Net to the applications menu?"""

from PyQt6.QtWidgets import QMessageBox, QWidget

from cube_net.ui.i18n import tr

QUESTION = "Add Cube Net to the applications menu?"
DETAILS = (
    "It will be there with its icon, and project files (.cubenet) will open in it with a double-click. You can change "
    "this any time in Settings → Preferences."
)


def ask_menu_entry(parent: QWidget | None) -> bool:
    """Whether the user wants it (closing the question means no: the answer is remembered either way)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Cube Net")
    box.setText(tr(QUESTION))
    box.setInformativeText(tr(DETAILS))
    buttons = QMessageBox.StandardButton
    box.setStandardButtons(buttons.Yes | buttons.No)
    box.setDefaultButton(buttons.Yes)
    box.exec()
    clicked = box.standardButton(box.clickedButton())
    box.deleteLater()
    return clicked == buttons.Yes
