# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The questions about the applications menu's entry of an AppImage: add Cube Net to it (asked once, at its first
start)? And before it's taken out (the Preferences checkbox): sure, knowing what it means?"""

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


REMOVE_QUESTION = "Remove Cube Net from the applications menu?"
REMOVE_DETAILS = (
    "Cube Net will no longer be in the applications menu, project files (.cubenet) will no longer open in it with a "
    "double-click or appear with it in Open With, and the Dock will show a generic icon for it.\n\n"
    "The AppImage itself, your projects and your settings stay as they are. You can add it to the menu again here any "
    "time."
)


def confirm_menu_entry_removal(parent: QWidget | None) -> bool:
    """Whether the user really wants it out of the menu (closing the question means no)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Cube Net")
    box.setText(tr(REMOVE_QUESTION))
    box.setInformativeText(tr(REMOVE_DETAILS))
    remove = box.addButton(tr("Remove"), QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    clicked = box.clickedButton()
    box.deleteLater()
    return clicked is remove
