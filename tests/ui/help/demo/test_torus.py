# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.core.geometry import Vec
from cube_net.core.history import History
from cube_net.ui.help.demo.torus import torus_project


def test_the_torus_project_with_its_look_and_origin() -> None:
    project = torus_project()
    assert project.settings.style is not None and project.settings.face_colors is not None  # the animations' look
    assert project.state.origin.position == Vec(44, 50)  # what the scenes' typed coordinates are from
    assert project.state.points is None and project.state.rearranged is None  # nothing going on
    assert project.history.revision == History().revision
