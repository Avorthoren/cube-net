# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.core.geometry import Vec
from cube_net.core.history import History
from cube_net.core.net import validate_net
from cube_net.core.origin import Origin
from cube_net.core.project import TemplateDocument
from cube_net.core.project.from_template import project_from_template
from cube_net.core.style import Style
from cube_net.core.template import Template, TemplateSnapshot

STYLE = Style(3, 4, 7, 2.5, 5.0, "#ABCDEF", 0.5)


def test_the_body_its_net_where_the_template_has_it(cross_template: Template) -> None:
    project = project_from_template(TemplateDocument(TemplateSnapshot(cross_template), History(), STYLE))
    net = project.state.net
    validate_net(net)
    assert len(net.body.face_numbers) == 6
    assert {v.position for v in net.vertices} == {v.position for v in cross_template.vertices}
    assert project.state.points is None and project.state.rearranged is None and project.state.approved_cuts == 0
    assert project.history.done_count == 0


def test_the_templates_colours_style_and_origin(cross_template: Template) -> None:
    origin = Origin().moved(Vec(11, 10), Vec(0, 0), "A3")
    project = project_from_template(TemplateDocument(TemplateSnapshot(cross_template, origin), History(), STYLE))
    assert project.settings.face_colors == tuple(face.color for face in cross_template.faces)
    assert project.settings.style == STYLE
    assert project.state.origin == origin


def test_a_template_without_a_style_leaves_it_to_the_application(cross_template: Template) -> None:
    project = project_from_template(TemplateDocument(TemplateSnapshot(cross_template), History()))
    assert project.settings.style is None


def test_no_ghost_where_the_line_is_smooth(half_moved_template: Template) -> None:
    """The half-moved cube (the steps shown to the user on 2026-11-19): X and Y, the middles of the edges A-E and B-F,
    are corners of the starting net and keep the template's names there; glued back, face 5 is a square again and they
    go; glued onto face 4, A-E is a fold with nothing in its middle."""
    from cube_net.core.editor import Editor
    from cube_net.core.labels import vertex_labels
    from cube_net.core.net import Net, NetVertex

    project = project_from_template(TemplateDocument(TemplateSnapshot(half_moved_template), History()))
    net = project.state.net
    names = {str(label) for label in vertex_labels(net, project.labels).values()}
    assert {"X_1", "X_2", "X_3", "Y_1", "Y_2", "Y_3"} <= names

    def on_perimeter(net: Net, p: Vec) -> NetVertex:
        return next(v for v in net.vertices if v.position == p and v in {he.origin for he in net.boundary_edges()})

    def cut(editor: Editor, a: Vec, b: Vec, glue_at: tuple[Vec, Vec]) -> Net:
        for p in (a, b):
            assert editor.click(p, None, on_perimeter(editor.net, p)) is None
        split = editor.split().net
        clicked = next(
            he for he in split.boundary_edges() if {he.origin.position, he.destination.position} == set(glue_at)
        )
        assert editor.glue(clicked) is None and editor.rearranged is not None and editor.rearranged.valid
        editor.approve()
        validate_net(editor.net)
        return editor.net

    editor = Editor(net)
    whole = cut(editor, Vec(22, 28), Vec(24, 28), (Vec(22, 21), Vec(24, 21)))  # the half back onto the other one
    assert all(v.point.vertex is not None for v in whole.vertices)  # no X, no Y: only the cube's vertices
    folded = cut(editor, Vec(22, 22), Vec(24, 22), (Vec(20, 24), Vec(20, 26)))  # face 5 onto face 4's side A-E
    assert not [v for v in folded.vertices if v.position == Vec(20, 25)]  # nothing in the middle of the fold A-E
    assert all(v.point.vertex is not None for v in folded.vertices)
