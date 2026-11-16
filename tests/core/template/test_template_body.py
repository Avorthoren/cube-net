# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.body import CUBE, SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import Net, default_net, starting_net, validate_net
from cube_net.core.template import Template, body_from_template, template_area


def labels_by_position(net: Net) -> dict[Vec, str]:
    return {v.position: str(label) for v, label in vertex_labels(net, PointLabels(net.body)).items()}


def test_the_cross_gives_the_cubes_default_net(cross_template: Template) -> None:
    body = body_from_template(cross_template)
    assert body.area == template_area(cross_template) == 6
    assert len(body.edges) == 12 and body.vertex_names == CUBE.vertex_names
    assert {body.vertex_angle(v) for v in body.vertex_names} == {270}
    net = starting_net(body)
    validate_net(net)
    assert labels_by_position(net) == labels_by_position(default_net())  # A_1 where A_1 is, and so on
    assert len(net.fold_edges()) == 5 and len(net.boundary_edges()) == 14


def test_faces_and_colours_in_the_templates_order(cross_template: Template) -> None:
    body = body_from_template(cross_template)
    assert body.face_numbers == tuple(range(1, len(cross_template.faces) + 1))
    assert body.colors == tuple(face.color for face in cross_template.faces)
    assert sorted(body.colors) == sorted(CUBE.colors)


def test_a_point_glued_across_a_cut(cross_template: Template) -> None:
    """The middle of A_3-B_3 is the middle of A_1-B_1: the same point of the body."""

    body = body_from_template(cross_template)
    bottom = next(n for n in body.face_numbers if Vec(11, 10) in body.face(n).corners)
    top = next(n for n in body.face_numbers if Vec(11, 14) in body.face(n).corners)

    assert SurfacePoint(body, bottom, Vec(F(23, 2), 10)) == SurfacePoint(body, top, Vec(F(23, 2), 14))


def test_the_pinwheel_box(pinwheel_template: Template) -> None:
    body = body_from_template(pinwheel_template)
    assert body.area == 16
    assert body.vertex_angle("M") == 360 and len(body.vertex_faces("M")) == 4
    net = starting_net(body)
    validate_net(net)
    assert labels_by_position(net)[pinwheel_template.vertices[3].position] == "M_1"


def test_only_a_valid_template(cross_template: Template) -> None:
    owner = cross_template.vertices[0].id
    with pytest.raises(ValueError, match="isn't valid"):
        body_from_template(cross_template.with_label(owner, None))
