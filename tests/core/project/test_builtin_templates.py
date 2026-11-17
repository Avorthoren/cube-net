# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The built-in templates must be good ones: scripts/embed_template.py checks a template before writing it, and these
tests check what's in the package (it may also have been put there by hand)."""

from cube_net.core.net import validate_net
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.project.from_template import project_from_template
from cube_net.core.template import validate


def test_cube_with_a_hole_is_a_valid_template_with_a_style() -> None:
    document = cube_with_a_hole()
    assert validate(document.state.template) is None
    assert document.style is not None


def test_it_keeps_no_history() -> None:
    history = cube_with_a_hole().history
    assert history.done_count == 0 and history.undone_count == 0


def test_a_project_of_it_is_a_torus() -> None:
    project = project_from_template(cube_with_a_hole())
    validate_net(project.state.net)
    body = project.state.net.body
    # A cube with a hole is a torus: V - E + F = 0.
    assert len(body.vertex_names) - len(body.edges) + len(body.face_numbers) == 0
    assert project.settings.style == cube_with_a_hole().style
    assert project.state.origin == cube_with_a_hole().state.origin
