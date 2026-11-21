# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Repairing a project whose numbers are longer than the application supports (`MAX_NUMBER_DIGITS`): made before the
limit, or by hand. `long_vertices` finds them; `repair_project` moves them to the nearest points with short numbers.

Every vertex of a net is an image of a point of the body (in its face's frame), placed by its region's turn and shift.
The shifts stay short (they come from the body's own geometry); long numbers come only from where cut points lie on the
body. So each such body point is moved, by at most a step of 10^-1000, to a point with short numbers: inside a face, to
the nearest point of that fine grid; on an edge of the body, along the edge (it stays on it); a corner of the body never
moves. All of its images move with it (they're recomputed from it), so every cut still matches its counterpart.

What can't be kept goes: the history (its states have the same long numbers), a cut line being drawn, a rearrangement
not approved. The result is checked as a whole (`validate_net`, every pair of perimeter segments meeting as before,
every number short); anything wrong is a `RepairError`, and nothing is repaired.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from itertools import combinations

from cube_net.core.body import SurfacePoint, SurfacePointKind
from cube_net.core.editor import EditorSnapshot
from cube_net.core.geometry import MAX_NUMBER_DIGITS, Vec, classify_segments, long_number
from cube_net.core.history import History
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, NetVertex, validate_net
from cube_net.core.origin import Origin
from cube_net.core.project.longest_number import longest_number
from cube_net.core.project.project import Project

# The grid the moved points go to: 10^-1000, far finer than anything shown, far shorter than the limit.
STEP = Fraction(1, 10**1000)


class RepairError(Exception):
    """The repair didn't give a good project (a bug of the repair): the file is left as it is."""


def long_vertices(project: Project) -> list[NetVertex]:
    """The vertices of the project's net with a number too long (in their position or in their body point)."""
    return [v for v in project.state.net.vertices if _long(v)]


def needs_repair(project: Project) -> bool:
    """Has the project, anywhere (its net, its history, its origin...), a number too long?"""
    return longest_number(project) > MAX_NUMBER_DIGITS


def vertex_names(net: Net, labels: PointLabels, vertices: list[NetVertex]) -> list[str]:
    """The vertices' names ("A1", "BF3"), in the order of the names (a vertex without one: its position)."""
    names = vertex_labels(net, labels)
    found = []
    for vertex in vertices:
        label = names.get(vertex)
        found.append(f"{label.name}{label.index}" if label is not None else f"({vertex.position})")
    return sorted(set(found))


def repair_project(project: Project) -> Project:
    """The project with every body point that has a number too long moved to the nearest short one (see the module's
    docstring). Raises `RepairError` if the result isn't a good project."""
    try:
        repaired = _repaired(project)
    except RepairError:
        raise
    except Exception as e:  # anything the net's own checks find
        raise RepairError(str(e)) from e
    if needs_repair(repaired):
        raise RepairError("numbers too long remain")
    return repaired


def _repaired(project: Project) -> Project:
    net = project.state.net
    moved = {v.point: _short_point(v.point) for v in net.vertices if _long(v)}
    copy = net.copy()
    new_net = copy.net
    for old, vertex in copy.vertices.items():
        point = moved.get(old.point)
        if point is not None:
            vertex.point = point
            vertex.position = _image(vertex, point)
    new_net.reindex()
    validate_net(new_net)
    _same_contacts(net, new_net, copy.edges)
    names, next_index = project.labels.saved()
    labels = PointLabels.restored(net.body, {moved.get(p, p): name for p, name in names.items()}, next_index)
    state = EditorSnapshot(new_net, None, None, project.state.approved_cuts, _short_origin(project.state.origin))
    return Project(state, History(), project.settings, labels)


def _long(vertex: NetVertex) -> bool:
    return long_number(vertex.position) is not None or any(long_number(local) for _, local in vertex.point.forms)


def _short_point(point: SurfacePoint) -> SurfacePoint:
    """The nearest point of the body with short numbers: on the same edge for a point on an edge (a corner stays)."""
    body = point.body
    match point.kind:
        case SurfacePointKind.VERTEX:
            raise RepairError(f"a corner of the body has a number too long: {point}")
        case SurfacePointKind.EDGE:
            (side,) = body.sides_through(point.face, point.local)
            a, b = body.face(point.face).side_ends(side.index)
            d = b - a
            t = (point.local - a).dot(d) / d.length_squared()
            steps = 1 / STEP
            k = min(max(round(t * steps), 1), int(steps) - 1)  # never an end: that would be a corner
            local = a + d * Fraction(k, int(steps))
        case SurfacePointKind.FACE:
            local = _vec_on_grid(point.local)
    short = SurfacePoint(body, point.face, local)
    if short.kind is not point.kind or (point.edge is not None and short.edge != point.edge):
        raise RepairError(f"{point} would move onto something else")
    return short


def _on_grid(value: Fraction) -> Fraction:
    return Fraction(round(value / STEP)) * STEP


def _image(vertex: NetVertex, point: SurfacePoint) -> Vec:
    """Where the vertex goes for its moved body point: placed by a region it's a corner of, in that region's face's
    frame (the form nearest to where it was, if the face holds the point twice)."""
    region = next(he.region for he in _around(vertex) if he.region is not None and he.region.face in point.faces)
    to_local = region.placement.inverse().apply(vertex.position)
    local = min(point.locals_in(region.face), key=lambda form: (form - to_local).length_squared())
    return region.placement.apply(local)


def _around(vertex: NetVertex) -> list[HalfEdge]:
    """The half-edges that start at the vertex."""
    found, he = [], vertex.edge
    while True:
        found.append(he)
        he = he.twin.next
        if he is vertex.edge:
            return found


def _same_contacts(before: Net, after: Net, edges: Mapping[HalfEdge, HalfEdge]) -> None:
    """Every pair of perimeter segments meets as it did (not at all, at a point, along a part): the moves are tiny, but
    an exact contact could have turned into a gap or an overlap."""
    for a, b in combinations(before.boundary_edges(), 2):
        was = classify_segments(a.origin.position, a.destination.position, b.origin.position, b.destination.position)
        x, y = edges[a], edges[b]
        now = classify_segments(x.origin.position, x.destination.position, y.origin.position, y.destination.position)
        if now.kind is not was.kind:
            raise RepairError(f"{a} and {b} would meet otherwise")


def _short_origin(origin: Origin) -> Origin:
    """The origin on the grid, if it has a number too long (it's no point of the net: nothing has to follow it)."""
    if long_number(origin.position) is None and (origin.point is None or long_number(origin.point) is None):
        return origin
    point = None if origin.point is None else _vec_on_grid(origin.point)
    return Origin(_vec_on_grid(origin.position), point, origin.name)


def _vec_on_grid(p: Vec) -> Vec:
    return Vec(_on_grid(p.x), _on_grid(p.y))
