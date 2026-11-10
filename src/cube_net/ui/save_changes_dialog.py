# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The question asked before unsaved changes would get lost (docs/idea.txt): Save / Don't save / Cancel."""

from enum import Enum

from PyQt6.QtWidgets import QMessageBox, QWidget

from cube_net.ui.i18n import tr


class SaveChoice(Enum):
    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"


def ask_save_changes(parent: QWidget | None, project_name: str) -> SaveChoice:
    """Ask what to do with the unsaved changes of the project. Closing the question means Cancel."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("Save changes?"))
    box.setText(tr('Save changes to "{name}"?', name=project_name))
    buttons = QMessageBox.StandardButton
    box.setStandardButtons(buttons.Save | buttons.Discard | buttons.Cancel)
    box.setDefaultButton(buttons.Save)
    box.setEscapeButton(buttons.Cancel)
    discard = box.button(buttons.Discard)
    assert discard is not None
    discard.setText(tr("Don't save"))
    box.exec()
    clicked = box.standardButton(box.clickedButton())
    box.deleteLater()  # its parent would keep it for as long as the window lives
    if clicked == buttons.Save:
        return SaveChoice.SAVE
    return SaveChoice.DISCARD if clicked == buttons.Discard else SaveChoice.CANCEL
