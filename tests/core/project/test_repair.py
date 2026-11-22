# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Repairing a project whose numbers are too long: made with a limit lifted for the test (as a file made before the
limit, or by hand)."""

from fractions import Fraction as F

import pytest

import cube_net.core.geometry.long_numbers as long_numbers
from cube_net.core.body import CUBE, SurfacePointKind
from cube_net.core.cutting import CutPoint
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels
from cube_net.core.net import HalfEdge, Net, default_net, validate_net
from cube_net.core.project import Project, project_from_bytes, project_to_bytes
from cube_net.core.project.file import any_length
from cube_net.core.project.repair import RepairError, long_vertices, needs_repair, repair_project, vertex_names
from cube_net.core.project_settings import ProjectSettings


def edge(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {a, b})


def long_project(x: F) -> Project:
    """A cut from the top of face 1 at `x` (a number too long) down through its middle, glued and approved."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(long_numbers, "MAX_NUMBER_DIGITS", 10**9)  # (only while it's made)
        return _long_project(x)


def _long_project(x: F) -> Project:
    editor = Editor(default_net())
    assert editor.start_at(editor.point_on_cut(Vec(x, 14), edge(editor.net, Vec(11, 14), Vec(12, 14)))) is None
    assert editor.add_point(CutPoint(Vec(x, F(23, 2)))) is None
    assert editor.add_point(editor.point_on_cut(Vec(F(23, 2), 10), edge(editor.net, Vec(11, 10), Vec(12, 10)))) is None
    split = editor.split()
    for cut in split.net.boundary_edges():
        if cut not in split.line_edges and editor.glue(cut) is None and editor.rearranged is not None:
            if editor.rearranged.valid:
                editor.approve()
                break
            editor.undo()
    assert editor.state is EditorState.DEFAULT and editor.approved_cuts == 1
    return Project(editor.snapshot(), editor.history, ProjectSettings(), PointLabels(CUBE))


# A third, written with 2200 digits: too long, but nowhere near any other point.
THIRD = F(10**2200 // 3, 10**2200)


def test_the_long_vertices_and_their_names() -> None:
    project = long_project(11 + THIRD)
    assert needs_repair(project)
    vertices = long_vertices(project)
    assert vertices and all(v.point.kind is not SurfacePointKind.VERTEX for v in vertices)
    names = vertex_names(project.state.net, project.labels, vertices)
    assert names and names == sorted(names) and all(n[0].isalpha() for n in names)


def test_repaired_everything_short_and_the_net_whole() -> None:
    project = long_project(11 + THIRD)
    repaired = repair_project(project)
    assert not needs_repair(repaired)
    validate_net(repaired.state.net)
    assert repaired.history.done_count == 0 and repaired.history.undone_count == 0  # the history goes
    assert repaired.state.points is None and repaired.state.rearranged is None
    assert repaired.state.approved_cuts == project.state.approved_cuts
    before = sorted(v.position.to_floats() for v in project.state.net.vertices)
    after = sorted(v.position.to_floats() for v in repaired.state.net.vertices)
    assert before == after  # nothing moved visibly
    # A point on an edge of the cube stays on that edge; the names go with the points.
    moved = {v.point: v for v in long_vertices(project)}
    for old in moved:
        new = next(
            v.point for v in repaired.state.net.vertices if v.point.edge == old.edge and v.point.kind is old.kind
        )
        assert new.kind is old.kind
    assert vertex_names(repaired.state.net, repaired.labels, list(repaired.state.net.vertices))
    assert project_from_bytes(project_to_bytes(repaired)).state.net.vertices  # it saves and opens


def test_a_point_that_would_meet_another_isnt_repaired() -> None:
    """A cut a hair's breadth from the middle of the face: on the grid, its points would fall onto others."""
    project = long_project(F(23, 2) + F(1, 3 * 10**2200))
    with pytest.raises(RepairError):
        repair_project(project)


def test_a_file_with_numbers_longer_than_python_reads_by_default() -> None:
    project = long_project(11 + F(10**4500 // 3, 10**4500))
    with any_length():
        content = project_to_bytes(project)
    loaded = project_from_bytes(content)  # it opens, to be repaired
    assert needs_repair(loaded) and not needs_repair(repair_project(loaded))
