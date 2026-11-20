# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What undoing or redoing a move of the origin says (docs/idea.txt: right click -> Move the origin): the coordinates
the point it was moved by has now, as the coordinates hint shows them (y, then x).

    Coordinates of C₁ were set to:
    y: 13
    x: 21/2 = 10.500

The point's name is shown as on the sheet: its image index as a subscript (rich text: C<sub>1</sub>).
"""

import html

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox, QWidget

from cube_net.core.geometry import Vec
from cube_net.ui.dialogs.message_window import MessageWindow
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.coordinates_hint import hint_font
from cube_net.ui.sheet.coordinates_text import coordinate_lines


def subscripted(name: str) -> str:
    """A label like "C_1" as rich text, its index a subscript ("C<sub>1</sub>"); a name without an index as it is."""
    point, underscore, index = name.rpartition("_")
    if not underscore or not point or not index:
        return html.escape(name)
    return f"{html.escape(point)}<sub>{html.escape(index)}</sub>"


def origin_moved_text(name: str | None) -> str:
    """The message's text, as rich text (its English and Russian words have no characters that HTML would take)."""
    if name is None:
        return tr("Coordinates of the point were set to:")
    return tr("Coordinates of {name} were set to:", name=subscripted(name))


def tell_origin_moved(parent: QWidget | None, name: str | None, coordinates: Vec) -> None:
    """`name`: the point's (None: it has none); `coordinates`: what they are now. Only OK (Enter, Space, Escape and the
    close button all mean it)."""
    window = MessageWindow("Cube Net", origin_moved_text(name), "\n".join(coordinate_lines(coordinates)), parent=parent)
    window.text_label.setTextFormat(Qt.TextFormat.RichText)
    font = hint_font()
    font.setPointSizeF(window.details_label.font().pointSizeF())  # the hint's letters (fixed width), the text's size
    window.details_label.setFont(font)
    window.details_label.setMinimumWidth(window.details_label.sizeHint().width())
    ok = window.add_standard(QDialogButtonBox.StandardButton.Ok)
    window.set_default(ok)
    window.set_escape(ok)
    window.ask()
