# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What to do when the last project can't be reopened at start (docs/idea.txt): a new project, or another file."""

from enum import Enum

from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow
from cube_net.ui.i18n import tr


class AfterLoadFailed(Enum):
    NEW_PROJECT = "new project"
    OPEN_ANOTHER = "open another"


def ask_after_load_failed(parent: QWidget | None, message: str) -> AfterLoadFailed:
    """Tell why it failed, and suggest a new project. Closing the question means just that."""
    window = MessageWindow(
        tr("Can't open the project"),
        message,
        tr("Start a new project, or open another one?"),
        MessageIcon.WARNING,
        parent,
    )
    new_project = window.add(tr("New project"), QDialogButtonBox.ButtonRole.AcceptRole)
    open_another = window.add(tr("&Open..."), QDialogButtonBox.ButtonRole.ActionRole)
    window.set_default(new_project)
    window.set_escape(new_project)
    return AfterLoadFailed.OPEN_ANOTHER if window.ask() is open_another else AfterLoadFailed.NEW_PROJECT
