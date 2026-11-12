# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The questions about the applications menu's entry of an AppImage: add Cube Net to it (asked once, at its first
start)? And before it's taken out (the Preferences checkbox): sure, knowing what it means?"""

from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow
from cube_net.ui.i18n import tr

QUESTION = "Add Cube Net to the applications menu?"
DETAILS = (
    "It will be there with its icon, and project files (.cubenet) will open in it with a double-click. You can change "
    "this any time in Settings → Preferences."
)


def ask_menu_entry(parent: QWidget | None) -> bool:
    """Whether the user wants it (closing the question means no: the answer is remembered either way)."""
    window = MessageWindow("Cube Net", tr(QUESTION), tr(DETAILS), MessageIcon.QUESTION, parent)
    yes = window.add_standard(QDialogButtonBox.StandardButton.Yes)
    no = window.add_standard(QDialogButtonBox.StandardButton.No)
    window.set_default(yes)
    window.set_escape(no)
    return window.ask() is yes


REMOVE_QUESTION = "Remove Cube Net from the applications menu?"
REMOVE_DETAILS = (
    "Cube Net will no longer be in the applications menu, project files (.cubenet) will no longer open in it with a "
    "double-click or appear with it in Open With, and the Dock will show a generic icon for it.\n\n"
    "The AppImage itself, your projects and your settings stay as they are. You can add it to the menu again here any "
    "time."
)


def confirm_menu_entry_removal(parent: QWidget | None) -> bool:
    """Whether the user really wants it out of the menu (closing the question means no)."""
    window = MessageWindow("Cube Net", tr(REMOVE_QUESTION), tr(REMOVE_DETAILS), MessageIcon.QUESTION, parent)
    remove = window.add(tr("Remove"), QDialogButtonBox.ButtonRole.DestructiveRole)
    cancel = window.add_standard(QDialogButtonBox.StandardButton.Cancel)
    window.set_default(cancel)
    window.set_escape(cancel)
    return window.ask() is remove
