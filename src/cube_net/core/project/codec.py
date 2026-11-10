"""A `Project` as plain JSON data, and back (docs/plan.md, section 5.3).

All numbers are exact: fractions are written as strings ("1/3"). Nets, rearrangements and states are stored once each,
in tables, and referred to by their index: the history holds up to 2000 states, while most of them share the same net.
Going through the tables also keeps that sharing after loading. The order of the elements of a net and their ids are
kept as they were, so that a loaded project behaves exactly like the saved one.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from typing import Any

from cube_net.core.cube import SurfacePoint
from cube_net.core.cutting import CutPoint, Rearranged
from cube_net.core.editor import EditorSnapshot
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.history import ActionKind, History, HistoryEntry
from cube_net.core.labels import PointLabels
from cube_net.core.net import EdgeKind, HalfEdge, Net, NetInvariantError, NetVertex, Region, validate_net
from cube_net.core.project.project import Project, ProjectFileError
from cube_net.core.project_settings import ProjectSettings, format_threshold

# Exact coordinates can have many digits, more than Python turns into text by default (a guard against huge numbers from
# strangers, which doesn't apply here). A project must be saved and loaded, however complicated it got.
sys.set_int_max_str_digits(0)

# Raise it whenever the format changes (and keep reading the older ones, if there's anything worth keeping).
FORMAT_VERSION = 1


def encode_project(project: Project) -> dict[str, Any]:
    return _Encoder().project(project)


def decode_project(data: object) -> Project:
    """The project from `encode_project`'s data. Raises `ProjectFileError` if there's anything wrong with it."""
    if not isinstance(data, dict):
        raise ProjectFileError("It isn't a Cube Net project.")
    version = data.get("format_version")
    if version != FORMAT_VERSION:
        if isinstance(version, int) and version > FORMAT_VERSION:
            raise ProjectFileError("It was saved by a newer version of the application.")
        raise ProjectFileError("It has an unknown format version: {version}.", version=repr(version))
    try:
        return _Decoder(data).project()
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, ZeroDivisionError, NetInvariantError) as e:
        raise ProjectFileError("It is damaged ({detail}).", detail=f"{type(e).__name__}: {e}") from e


def _write_vec(v: Vec) -> list[str]:
    return [str(v.x), str(v.y)]


def _read_number(text: object) -> Fraction:
    if not isinstance(text, str):
        raise TypeError(f"expected a number as a string, got {text!r}")
    return Fraction(text)


def _read_vec(data: list[object]) -> Vec:
    x, y = data
    return Vec(_read_number(x), _read_number(y))


def _write_motion(motion: Rigid90) -> dict[str, Any]:
    return {"k": motion.k, "t": _write_vec(motion.t)}


def _read_motion(data: dict[str, Any]) -> Rigid90:
    return Rigid90(data["k"], _read_vec(data["t"]))


def _write_point(point: SurfacePoint) -> dict[str, Any]:
    return {"face": point.face, "local": _write_vec(point.local)}


def _read_point(data: dict[str, Any]) -> SurfacePoint:
    return SurfacePoint(data["face"], _read_vec(data["local"]))


def _write_net(net: Net) -> dict[str, Any]:
    return {
        "vertices": [
            {"id": v.id, "at": _write_vec(v.position), "point": _write_point(v.point), "edge": v.edge.id}
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

    def __init__(self, data: dict[str, Any]) -> None:
        self.vertices = {
            v["id"]: NetVertex(v["id"], _read_vec(v["at"]), _read_point(v["point"])) for v in data["vertices"]
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
        self.net = Net(self.vertices.values(), self.edges.values(), self.regions.values())


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
        return {
            "format_version": FORMAT_VERSION,
            "settings": {"area_threshold": format_threshold(project.settings.area_threshold)},
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
        data: dict[str, Any] = {"at": _write_vec(point.position)}
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
        self._nets = [_LoadedNet(net) for net in data["nets"]]
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
        names = {_read_point(point): name for point, name in data["labels"]["names"]}
        return Project(
            self._states[data["state"]],
            history,
            ProjectSettings(_read_number(data["settings"]["area_threshold"])),
            PointLabels.restored(names, data["labels"]["next"]),
        )

    def _entry(self, data: dict[str, Any]) -> HistoryEntry[EditorSnapshot]:
        return HistoryEntry(
            ActionKind(data["kind"]), self._states[data["before"]], self._states[data["after"]], data["forget_on_undo"]
        )

    def _state(self, data: dict[str, Any]) -> EditorSnapshot:
        loaded = self._nets[data["net"]]
        points = None if data["points"] is None else tuple(self._cut_point(loaded, p) for p in data["points"])
        rearranged = None if data["rearranged"] is None else self._rearranged[data["rearranged"]]
        return EditorSnapshot(loaded.net, points, rearranged, data["approved_cuts"])

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
            _read_vec(data["at"]),
            loaded.edges[data["edge"]] if "edge" in data else None,
            loaded.vertices[data["vertex"]] if "vertex" in data else None,
            loaded.edges[data["fold"]] if "fold" in data else None,
        )
