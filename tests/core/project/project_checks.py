# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the tests of saving projects have in common: editors in all sorts of states, and comparing what's in them."""

import json
from collections.abc import Callable
from fractions import Fraction as F

from cube_net.core.cutting import CutPoint, Rearranged
from cube_net.core.editor import Editor, EditorSnapshot, EditorState
from cube_net.core.geometry import Vec
from cube_net.core.history import HistoryEntry
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, boundary_vertex_at, default_net
from cube_net.core.project import Project, decode_project, encode_project
from cube_net.core.project_settings import ProjectSettings


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def cut_through(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {a, b})


def start_corner_cut(editor: Editor) -> None:
    """The corner cut of the default net of docs/idea.txt, closed."""
    net = editor.net
    assert editor.click(v("11.5", "14"), cut_through(net, Vec(11, 14), Vec(12, 14))) is None
    assert editor.click(v("11.5", "13.5"), None) is None
    assert editor.click(v("12", "13.5"), cut_through(net, Vec(12, 13), Vec(12, 14))) is None


def rearrange_corner_cut(editor: Editor) -> None:
    start_corner_cut(editor)
    assert editor.glue(cut_through(editor.split().net, v("11.5", "10"), Vec(12, 10))) is None


def new_project_editor() -> Editor:
    return Editor(default_net())


def cutting() -> Editor:
    editor = new_project_editor()
    editor.click(v("11.5", "14"), cut_through(editor.net, Vec(11, 14), Vec(12, 14)))
    editor.click(v("11.5", "13.5"), None)
    return editor


def starts_at_a_vertex_and_crosses_a_fold() -> Editor:
    editor = new_project_editor()
    net = editor.net
    a_1 = boundary_vertex_at(net, Vec(11, 14), F(1, 100))
    assert a_1 is not None
    fold = next(
        he for he in net.fold_edges() if {he.origin.position, he.destination.position} == {Vec(11, 13), Vec(12, 13)}
    )
    editor.click(a_1.position, None, a_1)
    editor.click(v("11.5", "13"), None, fold=fold)
    return editor


def editing() -> Editor:
    editor = new_project_editor()
    start_corner_cut(editor)
    return editor


def approving() -> Editor:
    editor = new_project_editor()
    rearrange_corner_cut(editor)
    return editor


def approving_with_an_overlap() -> Editor:
    editor = new_project_editor()
    net = editor.net
    editor.click(v("12", "13.5"), cut_through(net, Vec(12, 13), Vec(12, 14)))
    editor.click(v("11", "11.5"), cut_through(net, Vec(11, 11), Vec(11, 12)))
    chosen = next(
        he
        for he in editor.split().net.boundary_edges()
        if he.origin.position.y == he.destination.position.y == 13
        and min(he.origin.position.x, he.destination.position.x) > 12
        and he not in editor.split().line_edges
    )
    assert editor.glue(chosen) is None
    assert editor.rearranged is not None and not editor.rearranged.valid
    return editor


def after_a_cut() -> Editor:
    editor = approving()
    editor.approve()
    return editor


def with_something_to_redo() -> Editor:
    editor = after_a_cut()
    editor.undo()
    editor.redo()
    editor.undo()
    return editor


def a_second_cut_in_progress() -> Editor:
    editor = after_a_cut()
    net = editor.net
    editor.click(v("11.5", "12"), None)  # means nothing
    edge = cut_through(net, Vec(10, 12), Vec(10, 13))
    editor.click(v("10", "12.5"), edge)
    editor.click(v("10.5", "12.5"), None)
    editor.undo()
    return editor


# All sorts of states an editor can be in.
EDITORS: dict[str, Callable[[], Editor]] = {
    "new": new_project_editor,
    "cutting": cutting,
    "vertex and fold": starts_at_a_vertex_and_crosses_a_fold,
    "editing": editing,
    "approving": approving,
    "approving with an overlap": approving_with_an_overlap,
    "after a cut": after_a_cut,
    "redo available": with_something_to_redo,
    "second cut": a_second_cut_in_progress,
}


def net_contents(net: Net) -> tuple[object, ...]:
    return (
        tuple((x.id, x.position, x.point, x.edge.id) for x in net.vertices),
        tuple(
            (
                e.id,
                e.origin.id,
                e.kind,
                None if e.region is None else e.region.id,
                e.twin.id,
                e.next.id,
                e.prev.id,
            )
            for e in net.half_edges
        ),
        tuple((r.id, r.face, r.placement, r.edge.id) for r in net.regions),
    )


def point_contents(point: CutPoint) -> tuple[object, ...]:
    return (
        point.position,
        None if point.edge is None else point.edge.id,
        None if point.vertex is None else point.vertex.id,
        None if point.fold is None else point.fold.id,
    )


def rearranged_contents(rearranged: Rearranged | None) -> tuple[object, ...] | None:
    if rearranged is None:
        return None
    return (
        net_contents(rearranged.net),
        rearranged.kept.id,
        rearranged.moved.id,
        rearranged.motion,
        sorted(he.id for he in rearranged.overlapping),
    )


def state_contents(state: EditorSnapshot) -> tuple[object, ...]:
    points = None if state.points is None else tuple(point_contents(p) for p in state.points)
    return net_contents(state.net), points, rearranged_contents(state.rearranged), state.approved_cuts


def entry_contents(entry: HistoryEntry[EditorSnapshot]) -> tuple[object, ...]:
    return entry.kind, state_contents(entry.before), state_contents(entry.after), entry.forget_on_undo


def project_of(editor: Editor, labels: PointLabels | None = None, settings: ProjectSettings | None = None) -> Project:
    return Project(
        editor.snapshot(),
        editor.history,
        ProjectSettings() if settings is None else settings,
        PointLabels() if labels is None else labels,
    )


def named_labels(editor: Editor) -> PointLabels:
    """Names for the points of the net and of the closed line, as the app gives them once a line is applied."""
    labels = PointLabels()
    vertex_labels(editor.net, labels)
    if editor.state is EditorState.CUT_EDITING:
        for vertex in editor.split().net.vertices:
            labels.register(vertex.point)
    return labels


def round_trip(project: Project) -> Project:
    """Through the real JSON text."""
    return decode_project(json.loads(json.dumps(encode_project(project))))


def editor_of(project: Project) -> Editor:
    editor = new_project_editor()
    editor.load(project.state, project.history)
    return editor
