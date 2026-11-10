# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Net`: the cube net on the sheet as a DCEL of `NetVertex`, `HalfEdge` and `Region` (docs/plan.md, section 3.3).

Build one with `build_net()` (or `default_net()`). Queries return fresh lists; lookup indices are rebuilt by
`reindex()` after every structural change (cheap at this size).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from cube_net.core.cube import SurfacePoint
from cube_net.core.geometry import Box, Vec, polygon_contains
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region


class NetInvariantError(RuntimeError):
    """The net's structure is inconsistent. Always a bug in the code that built or changed the net."""


@dataclass(frozen=True, slots=True)
class NetCopy:
    """A copy of a net and where each original element went."""

    net: Net
    vertices: Mapping[NetVertex, NetVertex]
    edges: Mapping[HalfEdge, HalfEdge]
    regions: Mapping[Region, Region]


class Net:
    def __init__(
        self, vertices: Iterable[NetVertex], half_edges: Iterable[HalfEdge], regions: Iterable[Region]
    ) -> None:
        self.vertices: list[NetVertex] = list(vertices)
        self.half_edges: list[HalfEdge] = list(half_edges)
        self.regions: list[Region] = list(regions)
        self._images: dict[SurfacePoint, list[NetVertex]] = {}
        self._boundary_by_points: dict[tuple[SurfacePoint, SurfacePoint], HalfEdge] = {}
        self.reindex()

    def reindex(self) -> None:
        """Rebuild lookup indices. Raises `NetInvariantError` if a cut has other than exactly 2 images."""
        self._images = {}
        for v in self.vertices:
            self._images.setdefault(v.point, []).append(v)
        self._boundary_by_points = {}
        for he in self.boundary_edges():
            key = (he.origin.point, he.destination.point)
            if key in self._boundary_by_points:
                raise NetInvariantError(f"two boundary segments {key[0]} -> {key[1]} in the same direction")
            self._boundary_by_points[key] = he
        for (a, b), he in self._boundary_by_points.items():
            if (b, a) not in self._boundary_by_points:
                raise NetInvariantError(f"boundary segment {he} has no counterpart")

    def copy(self) -> NetCopy:
        """An independent copy of the whole structure (same ids), with the maps from the originals to their copies."""
        vertices = {v: NetVertex(v.id, v.position, v.point) for v in self.vertices}
        regions = {r: Region(r.id, r.face, r.placement) for r in self.regions}
        edges = {
            he: HalfEdge(he.id, vertices[he.origin], he.kind, None if he.region is None else regions[he.region])
            for he in self.half_edges
        }
        for he, new in edges.items():
            new.twin, new.next, new.prev = edges[he.twin], edges[he.next], edges[he.prev]
        for v, new_v in vertices.items():
            new_v.edge = edges[v.edge]
        for r, new_r in regions.items():
            new_r.edge = edges[r.edge]
        return NetCopy(Net(vertices.values(), edges.values(), regions.values()), vertices, edges, regions)

    # --- regions ----------------------------------------------------------------------------------------------------

    @staticmethod
    def region_cycle(region: Region) -> list[HalfEdge]:
        """The region's half-edges, counter-clockwise."""
        return _cycle(region.edge)

    def region_polygon(self, region: Region) -> list[Vec]:
        """The region's corner positions on the sheet, counter-clockwise."""
        return [he.origin.position for he in self.region_cycle(region)]

    # --- edges ------------------------------------------------------------------------------------------------------

    def perimeters(self) -> list[list[HalfEdge]]:
        """The outside half-edges, cycle by cycle (each clockwise around its part of the net). A net has one cycle; a
        net that has just been split along a cut line has two, until the parts are glued."""
        cycles: list[list[HalfEdge]] = []
        seen: set[HalfEdge] = set()
        for he in self.half_edges:
            if he.region is None and he not in seen:
                cycle = _cycle(he)
                seen.update(cycle)
                cycles.append(cycle)
        return cycles

    def perimeter(self) -> list[HalfEdge]:
        """The outside half-edges of the (first) perimeter cycle, in order along it."""
        return self.perimeters()[0]

    def boundary_edges(self) -> list[HalfEdge]:
        """The cuts: for every perimeter segment, its half-edge on the inside of the net."""
        return [he for he in self.half_edges if he.region is not None and he.twin.region is None]

    def fold_edges(self) -> list[HalfEdge]:
        """One half-edge for every cube edge lying inside the net."""
        return [he for he in self.half_edges if he.kind is EdgeKind.FOLD and he.id < he.twin.id]

    def counterpart(self, boundary_edge: HalfEdge) -> HalfEdge:
        """The other image of the same cut (as an inside half-edge, so it runs the opposite way on the cube)."""
        return self._boundary_by_points[(boundary_edge.destination.point, boundary_edge.origin.point)]

    # --- vertices ---------------------------------------------------------------------------------------------------

    def boundary_vertices(self) -> list[NetVertex]:
        """Vertices on the perimeter, in order along each perimeter cycle."""
        return [he.origin for cycle in self.perimeters() for he in cycle]

    def images(self, point: SurfacePoint) -> list[NetVertex]:
        """All vertices of the net that are images of `point`."""
        return list(self._images.get(point, ()))

    # --- geometry ---------------------------------------------------------------------------------------------------

    def contains(self, p: Vec) -> bool:
        """True if `p` lies on the net (inside or on the boundary of some region)."""
        return any(polygon_contains(self.region_polygon(r), p) for r in self.regions)

    def bounding_box(self) -> Box:
        """Axis-aligned bounding box of all vertices."""
        return Box.around(v.position for v in self.vertices)


def _cycle(start: HalfEdge) -> list[HalfEdge]:
    cycle = [start]
    he = start.next
    while he is not start:
        cycle.append(he)
        he = he.next
    return cycle
