# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The question asked before unsaved changes would get lost (docs/idea.txt): Save / Don't save / Cancel."""

from enum import Enum

from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow
from cube_net.ui.i18n import tr


class SaveChoice(Enum):
    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"


def ask_save_changes(parent: QWidget | None, project_name: str) -> SaveChoice:
    """Ask what to do with the unsaved changes of the project. Closing the question means Cancel."""
    window = MessageWindow(
        tr("Save changes?"), tr('Save changes to "{name}"?', name=project_name), icon=MessageIcon.WARNING, parent=parent
    )
    buttons = QDialogButtonBox.StandardButton
    save = window.add_standard(buttons.Save)
    discard = window.add_standard(buttons.Discard, tr("Don't save"))
    cancel = window.add_standard(buttons.Cancel)
    window.set_default(save)
    window.set_escape(cancel)
    clicked = window.ask()
    if clicked is save:
        return SaveChoice.SAVE
    return SaveChoice.DISCARD if clicked is discard else SaveChoice.CANCEL
