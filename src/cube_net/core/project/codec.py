# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""A `Project` as plain JSON data, and back (docs/plan.md, section 5.3).

All numbers are exact: fractions are written as strings ("1/3"). Nets, rearrangements and states are stored once each,
in tables, and referred to by their index: the history holds up to 2000 states, while most of them share the same net.
Going through the tables also keeps that sharing after loading. The order of the elements of a net and their ids are
kept as they were, so that a loaded project behaves exactly like the saved one. The body is written out too (unless
it's the cube), so a project of a body made from a template doesn't need the template.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from typing import Any

from cube_net.core.body import CUBE, Body, SurfacePoint
from cube_net.core.cutting import CutPoint, Rearranged
from cube_net.core.editor import EditorSnapshot
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.history import ActionKind, History, HistoryEntry
from cube_net.core.labels import PointLabels
from cube_net.core.net import EdgeKind, HalfEdge, Net, NetInvariantError, NetVertex, Region, validate_net
from cube_net.core.origin import Origin
from cube_net.core.project.project import Project, ProjectFileError
from cube_net.core.project_settings import ProjectSettings, format_threshold

# Exact coordinates can have many digits, more than Python turns into text by default (a guard against huge numbers from
# strangers, which doesn't apply here). A project must be saved and loaded, however complicated it got.
sys.set_int_max_str_digits(0)

# Raise it whenever the format changes (and keep reading the older ones, if there's anything worth keeping).
FORMAT_VERSION = 3

# The older versions still read. 1: no origin (the states have the default one). 1 and 2: no kind, always the cube,
# no face colours (the application fills them in).
READ_VERSIONS = (1, 2, FORMAT_VERSION)

# What a file of format 3 or later holds: a project (a template is the other kind).
PROJECT_KIND = "project"

# The body of a project of the cube, which isn't written out.
CUBE_BODY = "cube"


def encode_project(project: Project) -> dict[str, Any]:
    return _Encoder().project(project)


def decode_project(data: object) -> Project:
    """The project from `encode_project`'s data. Raises `ProjectFileError` if there's anything wrong with it."""
    if not isinstance(data, dict):
        raise ProjectFileError("It isn't a Cube Net project.")
    version = data.get("format_version")
    if version not in READ_VERSIONS:
        if isinstance(version, int) and version > FORMAT_VERSION:
            raise ProjectFileError("It was saved by a newer version of the application.")
        raise ProjectFileError("It has an unknown format version: {version}.", version=repr(version))
    if version >= 3 and data.get("kind") != PROJECT_KIND:
        raise ProjectFileError("It isn't a Cube Net project.")
    try:
        return _Decoder(data).project()
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, ZeroDivisionError, NetInvariantError) as e:
        raise ProjectFileError("It is damaged ({detail}).", detail=f"{type(e).__name__}: {e}") from e


def write_vec(v: Vec) -> list[str]:
    return [str(v.x), str(v.y)]


def read_number(text: object) -> Fraction:
    if not isinstance(text, str):
        raise TypeError(f"expected a number as a string, got {text!r}")
    return Fraction(text)


def read_vec(data: list[object]) -> Vec:
    x, y = data
    return Vec(read_number(x), read_number(y))


def write_origin(origin: Origin) -> dict[str, Any]:
    return {
        "at": write_vec(origin.position),
        "point": None if origin.point is None else write_vec(origin.point),
        "name": origin.name,
    }


def read_origin(data: dict[str, Any] | None) -> Origin:
    """The origin of a state (None: a state of format version 1, which had none)."""
    if data is None:
        return Origin()
    point, name = data["point"], data["name"]
    if name is not None and not isinstance(name, str):
        raise TypeError(f"expected a point's name, got {name!r}")
    return Origin(read_vec(data["at"]), None if point is None else read_vec(point), name)


def _write_motion(motion: Rigid90) -> dict[str, Any]:
    return {"k": motion.k, "t": write_vec(motion.t)}


def _read_motion(data: dict[str, Any]) -> Rigid90:
    return Rigid90(data["k"], read_vec(data["t"]))


def _write_body(body: Body) -> str | dict[str, Any]:
    if body is CUBE:
        return CUBE_BODY
    return {
        "faces": [
            {"corners": [write_vec(c) for c in body.face(n).corners], "names": list(body.face(n).names)}
            for n in body.face_numbers
        ],
        "start": [{"face": face, "placement": _write_motion(placement)} for face, placement in body.start],
        "colors": list(body.colors),
        "vertex_order": None if body.vertex_order is None else [[write_vec(p), name] for p, name in body.vertex_order],
    }


def _read_body(data: object) -> Body:
    if data == CUBE_BODY:
        return CUBE
    if not isinstance(data, dict):
        raise TypeError(f"expected a body, got {data!r}")
    faces = {
        n: ([read_vec(c) for c in face["corners"]], [_read_name(name) for name in face["names"]])
        for n, face in enumerate(data["faces"], start=1)
    }
    start = [(s["face"], _read_motion(s["placement"])) for s in data["start"]]
    order = data.get("vertex_order")
    vertex_order = None if order is None else [(read_vec(p), _read_name(name)) for p, name in order]
    return Body(faces, start, [str(c) for c in data["colors"]], vertex_order)


def _read_name(name: object) -> str:
    if not isinstance(name, str):
        raise TypeError(f"expected a vertex name, got {name!r}")
    return name


def _write_point(point: SurfacePoint) -> dict[str, Any]:
    return {"face": point.face, "local": write_vec(point.local)}


def _read_point(body: Body, data: dict[str, Any]) -> SurfacePoint:
    return SurfacePoint(body, data["face"], read_vec(data["local"]))


def _write_net(net: Net) -> dict[str, Any]:
    return {
        "vertices": [
            {"id": v.id, "at": write_vec(v.position), "point": _write_point(v.point), "edge": v.edge.id}
            for v in net.vertices
        ],
        "edges": [
            {
                "id": he.id,
                "origin": he.origin.id,
                "kind": he.kind.value,
                "region": None if he.region is None else he.region.id,
                "twin": he.twin.id,
                "next": he.next.id,
                "prev": he.prev.id,
            }
            for he in net.half_edges
        ],
        "regions": [
            {"id": r.id, "face": r.face, "placement": _write_motion(r.placement), "edge": r.edge.id}
            for r in net.regions
        ],
    }


class _LoadedNet:
    """A net read from the file, with its elements by id."""

    def __init__(self, body: Body, data: dict[str, Any]) -> None:
        self.vertices = {
            v["id"]: NetVertex(v["id"], read_vec(v["at"]), _read_point(body, v["point"])) for v in data["vertices"]
        }
        self.regions = {r["id"]: Region(r["id"], r["face"], _read_motion(r["placement"])) for r in data["regions"]}
        self.edges = {
            e["id"]: HalfEdge(
                e["id"],
                self.vertices[e["origin"]],
                EdgeKind(e["kind"]),
                None if e["region"] is None else self.regions[e["region"]],
            )
            for e in data["edges"]
        }
        if not (
            len(self.vertices) == len(data["vertices"])
            and len(self.regions) == len(data["regions"])
            and len(self.edges) == len(data["edges"])
        ):
            raise ValueError("two elements of a net have the same id")
        for e in data["edges"]:
            he = self.edges[e["id"]]
            he.twin, he.next, he.prev = self.edges[e["twin"]], self.edges[e["next"]], self.edges[e["prev"]]
        for v in data["vertices"]:
            self.vertices[v["id"]].edge = self.edges[v["edge"]]
        for r in data["regions"]:
            self.regions[r["id"]].edge = self.edges[r["edge"]]
        self.net = Net(body, self.vertices.values(), self.edges.values(), self.regions.values())


class _Encoder:
    def __init__(self) -> None:
        self._nets: list[Net] = []
        self._nets_data: list[dict[str, Any]] = []
        self._rearranged: list[Rearranged] = []
        self._rearranged_data: list[dict[str, Any]] = []
        self._states: dict[EditorSnapshot, int] = {}
        self._states_data: list[dict[str, Any]] = []

    def project(self, project: Project) -> dict[str, Any]:
        state = self._state(project.state)
        history = {
            "done": [self._entry(entry) for entry in project.history.done_entries()],
            "undone": [self._entry(entry) for entry in project.history.undone_entries()],
        }
        names, next_index = project.labels.saved()
        colors = project.settings.face_colors
        return {
            "format_version": FORMAT_VERSION,
            "kind": PROJECT_KIND,
            "body": _write_body(project.state.net.body),
            "settings": {
                "area_threshold": format_threshold(project.settings.area_threshold),
                "face_colors": None if colors is None else list(colors),
            },
            "labels": {"names": [[_write_point(p), name] for p, name in names.items()], "next": next_index},
            "nets": self._nets_data,
            "rearranged": self._rearranged_data,
            "states": self._states_data,
            "state": state,
            "history": history,
        }

    def _entry(self, entry: HistoryEntry[EditorSnapshot]) -> dict[str, Any]:
        return {
            "kind": entry.kind.value,
            "before": self._state(entry.before),
            "after": self._state(entry.after),
            "forget_on_undo": entry.forget_on_undo,
        }

    def _state(self, state: EditorSnapshot) -> int:
        index = self._states.get(state)
        if index is None:
            index = self._states[state] = len(self._states_data)
            self._states_data.append(
                {
                    "net": self._net(state.net),
                    "points": None if state.points is None else [self._cut_point(p) for p in state.points],
                    "rearranged": None if state.rearranged is None else self._rearrangement(state.rearranged),
                    "approved_cuts": state.approved_cuts,
                    "origin": write_origin(state.origin),
                }
            )
        return index

    def _net(self, net: Net) -> int:
        for i, known in enumerate(self._nets):
            if known is net:
                return i
        self._nets.append(net)
        self._nets_data.append(_write_net(net))
        return len(self._nets) - 1

    def _rearrangement(self, rearranged: Rearranged) -> int:
        for i, known in enumerate(self._rearranged):
            if known is rearranged:
                return i
        self._rearranged.append(rearranged)
        self._rearranged_data.append(
            {
                "net": self._net(rearranged.net),
                "kept": rearranged.kept.id,
                "moved": rearranged.moved.id,
                "motion": _write_motion(rearranged.motion),
                "overlapping": sorted(he.id for he in rearranged.overlapping),
            }
        )
        return len(self._rearranged) - 1

    @staticmethod
    def _cut_point(point: CutPoint) -> dict[str, Any]:
        data: dict[str, Any] = {"at": write_vec(point.position)}
        if point.edge is not None:
            data["edge"] = point.edge.id
        if point.vertex is not None:
            data["vertex"] = point.vertex.id
        if point.fold is not None:
            data["fold"] = point.fold.id
        return data


class _Decoder:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._body = _read_body(data["body"]) if data["format_version"] >= 3 else CUBE
        self._nets = [_LoadedNet(self._body, net) for net in data["nets"]]
        self._rearranged = [self._rearrangement(r) for r in data["rearranged"]]
        self._states = [self._state(state) for state in data["states"]]

    def project(self) -> Project:
        for net in {state.net for state in self._states}:  # most of the states share a net
            validate_net(net)
        data = self._data
        history: History[EditorSnapshot] = History.restored(
            [self._entry(entry) for entry in data["history"]["done"]],
            [self._entry(entry) for entry in data["history"]["undone"]],
        )
        names = {_read_point(self._body, point): name for point, name in data["labels"]["names"]}
        return Project(
            self._states[data["state"]],
            history,
            ProjectSettings(read_number(data["settings"]["area_threshold"]), self._face_colors()),
            PointLabels.restored(self._body, names, data["labels"]["next"]),
        )

    def _face_colors(self) -> tuple[str, ...] | None:
        colors = self._data["settings"].get("face_colors")
        if colors is None:
            return None
        if len(colors) != len(self._body.face_numbers):
            raise ValueError(f"{len(colors)} face colours for {len(self._body.face_numbers)} faces")
        return tuple(colors)

    def _entry(self, data: dict[str, Any]) -> HistoryEntry[EditorSnapshot]:
        return HistoryEntry(
            ActionKind(data["kind"]), self._states[data["before"]], self._states[data["after"]], data["forget_on_undo"]
        )

    def _state(self, data: dict[str, Any]) -> EditorSnapshot:
        loaded = self._nets[data["net"]]
        points = None if data["points"] is None else tuple(self._cut_point(loaded, p) for p in data["points"])
        rearranged = None if data["rearranged"] is None else self._rearranged[data["rearranged"]]
        origin = read_origin(data.get("origin"))
        return EditorSnapshot(loaded.net, points, rearranged, data["approved_cuts"], origin)

    def _rearrangement(self, data: dict[str, Any]) -> Rearranged:
        loaded = self._nets[data["net"]]
        return Rearranged(
            loaded.net,
            loaded.edges[data["kept"]],
            loaded.edges[data["moved"]],
            _read_motion(data["motion"]),
            frozenset(loaded.edges[i] for i in data["overlapping"]),
        )

    @staticmethod
    def _cut_point(loaded: _LoadedNet, data: dict[str, Any]) -> CutPoint:
        return CutPoint(
            read_vec(data["at"]),
            loaded.edges[data["edge"]] if "edge" in data else None,
            loaded.vertices[data["vertex"]] if "vertex" in data else None,
            loaded.edges[data["fold"]] if "fold" in data else None,
        )
