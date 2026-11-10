# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Why a project can't be saved or opened, in the user's language."""

from cube_net.core.project import ProjectFileError
from cube_net.ui.i18n.translator import tr


def error_text(error: ProjectFileError) -> str:
    """The error's message in the current language (its reason too, if it has one). What the system or the file said
    (a path, the system's reason, technical details) stays as it is."""
    values = {k: error_text(v) if isinstance(v, ProjectFileError) else str(v) for k, v in error.values.items()}
    return tr(error.template, **values)
