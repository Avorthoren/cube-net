# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the user is told about a file whose numbers are longer than the application supports (`MAX_NUMBER_DIGITS`):
the question whether to repair it (`core/project/repair.py`), and how the repair went."""

from collections.abc import Sequence

from cube_net.core.geometry import MAX_NUMBER_DIGITS
from cube_net.ui.i18n import tr

UNABLE_TO_OPEN = "Unable to open the file."
TOO_LONG = (
    "This version of the application supports numbers up to {max} decimal digits long, while selected file has "
    "vertices ({names}) whose coordinates numerators and/or denominators are longer."
)
REPAIR_QUESTION = (
    'Do you want to apply automatic fix that will move "bad" vertices in closest appropriate positions (vertices on '
    "body edges will be moved along those edges)? Caution: this will wipe out undo/redo history, any unfinished cut "
    "or unapproved rearrangement."
)
REPAIR_FAILED = "Unexpected error during project repairment."
REPAIRED = "Automatic repairment completed."
ADJUSTED = "Vertices {names} were adjusted."


def too_long_question(names: Sequence[str]) -> str:
    """The question (rich text: the names may have subscripts), for the vertices `names`."""
    too_long = tr(TOO_LONG, max=MAX_NUMBER_DIGITS, names=", ".join(names))
    return "<br>".join([tr(UNABLE_TO_OPEN), too_long, tr(REPAIR_QUESTION)])


def repaired_text(names: Sequence[str]) -> str:
    return "<br>".join([tr(REPAIRED), tr(ADJUSTED, names=", ".join(names))])


def repair_failed_text() -> str:
    return tr(REPAIR_FAILED)
