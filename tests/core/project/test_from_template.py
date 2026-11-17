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
