# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Look`: a style and face colours, which a view can paint in whatever the open document's are.

The style and the face colours are global (`apply_style`, `palette.set_face_colors`): everything reads them when it
paints or hit-tests. `Look.used` puts a look in place for a while and then the one before it again, so a view with its
own look (Help's animations) wraps its painting and its input in it (`SheetView.set_look`).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from cube_net.core.body import CUBE, Body
from cube_net.core.style import Style
from cube_net.ui import palette
from cube_net.ui.style.apply import apply_style, style_in_place
from cube_net.ui.style.default_style import DEFAULT_STYLE


@dataclass(frozen=True)
class Look:
    style: Style

    # The faces' colours ("#RRGGBB", face k: face_colors[k - 1]), for `body`'s faces.
    face_colors: tuple[str, ...]

    body: Body

    @contextmanager
    def used(self) -> Iterator[None]:
        """This look in place within the `with` block, the one before it again after it."""
        style, (colors, body) = style_in_place(), palette.face_colors_in_place()
        apply_style(self.style)
        palette.set_face_colors(self.face_colors, self.body)
        try:
            yield
        finally:
            apply_style(style)
            palette.set_face_colors(colors, body)


# The built-in Cube project's look (File -> New's Cube): the style files' style and the cube's own colours. Help's
# animations have it, whatever is open.
DEFAULT_CUBE_LOOK = Look(DEFAULT_STYLE, CUBE.colors, CUBE)
