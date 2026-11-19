# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Nets with holes (docs/template_plan.md, §8.2): the torus's purple pieces glued into a ring, and cuts in such a
net."""

from fractions import Fraction as F

import pytest
from net_checks import assert_consistent

from cube_net.core.cutting import connected_regions
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.labels import vertex_labels
from cube_net.core.net import HalfEdge, Net, NetVertex, validate_net
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.project.from_template import project_from_template


def cut_at(net: Net, p: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if on_segment(p, he.origin.position, he.destination.position))


@pytest.fixture
def ring() -> Net:
    """The torus's starting net, its lower purple piece cut off along its fold E_1-A_2 and glued onto the upper one
    along R-L: N-T lies on N-T then, and is glued too. The purple is a ring, around a hole."""
    project = project_from_template(cube_with_a_hole())
    labels: dict[str, NetVertex] = {
        str(label): v for v, label in vertex_labels(project.state.net, project.labels).items()
    }
    editor = Editor(project.state.net)
    for name in ("E_1", "A_2"):
        assert editor.click(labels[name].position, None, labels[name]) is None
    assert editor.state is EditorState.CUT_EDITING
    split = editor.split()
    r, el = labels["R_1"].position, labels["L_1"].position
    clicked = next(he for he in split.net.boundary_edges() if {he.origin.position, he.destination.position} == {r, el})
    assert editor.glue(clicked) is None and editor.rearranged is not None and editor.rearranged.valid
    editor.approve()
    return editor.net


def test_both_pairs_are_glued_into_a_ring(ring: Net) -> None:
    validate_net(ring)
    _, hole = sorted(ring.perimeters(), key=len, reverse=True)
    assert len(hole) == 4  # L, I, P, N
    assert len(ring.regions) == 11  # the two purple pieces are one region
    (seam,) = ring.inner_seams()  # what keeps the region from being a ring itself: unseen
    assert seam.region is seam.twin.region
    assert len({v.position for v in ring.vertices}) == len(ring.vertices)  # one set of vertices: no slit left


def test_a_cut_across_the_hidden_seam(ring: Net) -> None:
    """Across the seam (x = 41, from y 58 to 59) in the ring's corner: the corner comes off, and goes back on
    elsewhere."""
    seam = ring.inner_seams()[0]
    assert {seam.origin.position, seam.destination.position} == {Vec(41, 58), Vec(41, 59)}
    editor = Editor(ring)
    a, b, c, d = Vec(F(81, 2), 58), Vec(F(81, 2), F(117, 2)), Vec(F(83, 2), F(117, 2)), Vec(F(83, 2), 58)
    for p in (a, b, c, d):
        on = cut_at(ring, p) if p.y == 58 else None
        assert editor.click(p, on) is None
    split = editor.split()
    assert_consistent(split.net)
    half = connected_regions(split.net.regions[0])
    assert {len(half), len(split.net.regions) - len(half)} == {2, 11}  # the corner: two parts of the purple
    choice = next(he for he in split.net.boundary_edges() if he not in split.line_edges | split.same_half_cuts)
    assert editor.glue(choice) is None and editor.rearranged is not None and editor.rearranged.valid
    editor.approve()
    validate_net(editor.net)


def test_cutting_the_ring_in_two_through_its_hole(ring: Net) -> None:
    """The plan's example: a straight line up across the ring (x = 42), through the hole. Into the hole it only cuts
    the ring open; out of it, it divides the net, and ends at the outer side."""
    editor = Editor(ring)
    start = Vec(42, 58)
    assert editor.click(start, cut_at(ring, start)) is None
    assert editor.click(Vec(42, 60), None) is None  # in the hole
    assert editor.state is EditorState.CUTTING  # the ring is only open
    end = Vec(42, 62)
    assert editor.click(end, cut_at(ring, end)) is None
    assert editor.state is EditorState.CUT_EDITING
    real = editor.real_cut()
    assert real is not None and len(real.piece_lines()) == 2
    split = editor.split()
    assert_consistent(split.net)
    half = connected_regions(split.net.regions[0])
    assert 0 < len(half) < len(split.net.regions)
    choice = next(he for he in split.net.boundary_edges() if he not in split.line_edges | split.same_half_cuts)
    assert editor.glue(choice) is None and editor.rearranged is not None
    if editor.rearranged.valid:
        editor.approve()
        validate_net(editor.net)


def test_the_hole_alone_is_no_place_to_end(ring: Net) -> None:
    """From the outside straight into the hole and onto its side: the ring is only open, the line goes on."""
    editor = Editor(ring)
    start, end = Vec(F(83, 2), 58), Vec(F(83, 2), 59)
    assert editor.click(start, cut_at(ring, start)) is None
    assert editor.click(end, cut_at(ring, end)) is None
    assert editor.state is EditorState.CUTTING


def test_point_inside_a_hole_isnt_on_the_net(ring: Net) -> None:
    assert not ring.contains(Vec(42, 60)) and ring.contains(Vec(F(81, 2), 60))
