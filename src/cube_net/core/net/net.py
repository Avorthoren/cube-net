# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Net`: the net on the sheet as a DCEL of `NetVertex`, `HalfEdge` and `Region` (docs/plan.md, section 3.3).

Build one with `build_net()` (or `starting_net()`). Queries return fresh lists; lookup indices are rebuilt by
`reindex()` after every structural change (cheap at this size).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from cube_net.core.body import Body, BodyEdge, Face, SurfacePoint
from cube_net.core.geometry import Box, Vec, area_centroid, polygon_contains
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region

# A segment of the body, one way: a face number (or -1 - edge id, for a segment on an edge) and its two ends in that
# face's (or edge's) frame.
type SegmentKey = tuple[int, Vec, Vec]


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
        self, body: Body, vertices: Iterable[NetVertex], half_edges: Iterable[HalfEdge], regions: Iterable[Region]
    ) -> None:
        # The surface the net folds into: what its vertices and regions are points and parts of.
        self.body = body
        self.vertices: list[NetVertex] = list(vertices)
        self.half_edges: list[HalfEdge] = list(half_edges)
        self.regions: list[Region] = list(regions)
        self._images: dict[SurfacePoint, list[NetVertex]] = {}
        self._boundary_by_segment: dict[SegmentKey, HalfEdge] = {}
        self.reindex()

    def reindex(self) -> None:
        """Rebuild lookup indices. Raises `NetInvariantError` if a cut has other than exactly 2 images."""
        self._images = {}
        for v in self.vertices:
            self._images.setdefault(v.point, []).append(v)
        self._boundary_by_segment = {}
        for he in self.boundary_edges():
            key = self._segment_key(he)
            if key in self._boundary_by_segment:
                raise NetInvariantError(
                    f"two boundary segments {he.origin.point} -> {he.destination.point} in the same direction"
                )
            self._boundary_by_segment[key] = he
        for (where, a, b), he in self._boundary_by_segment.items():
            if (where, b, a) not in self._boundary_by_segment:
                raise NetInvariantError(f"boundary segment {he} has no counterpart")

    def _segment_key(self, he: HalfEdge) -> SegmentKey:
        """Which segment of the body `he` is an image of, and which way it runs: its ends in the frame of the face it
        lies in, or, if it lies on an edge, in the frame of the edge's first side (both images then give the same).
        Its end points alone may not tell (two faces can share several edges, a face can be glued to itself)."""
        region = he.region if he.region is not None else he.twin.region
        if region is None:
            raise NetInvariantError(f"{he} has no region on either side")
        to_local = region.placement.inverse()
        a, b = to_local.apply(he.origin.position), to_local.apply(he.destination.position)
        side = self.body.side_through(region.face, a, b)
        if side is None:
            return (region.face, a, b)
        edge = self.body.side_edge(side)
        if side != edge.sides[0]:
            to_first = edge.transition(side)
            a, b = to_first.apply(a), to_first.apply(b)
        return (-1 - edge.id, a, b)

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
        return NetCopy(Net(self.body, vertices.values(), edges.values(), regions.values()), vertices, edges, regions)

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
        """The outside half-edges, cycle by cycle (each clockwise around its part of the net). A net has one cycle, and
        one more for each hole; a net that has just been split along a cut line has those of both its parts, until
        they're glued."""
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
        """One half-edge for every body edge lying inside the net."""
        return [he for he in self.half_edges if he.kind is EdgeKind.FOLD and he.id < he.twin.id]

    def inner_seams(self) -> list[HalfEdge]:
        """One half-edge for every seam left in the net: inside a face, with one region on both sides (without it,
        that region would be a ring)."""
        return [he for he in self.half_edges if he.kind is EdgeKind.SEAM and he.id < he.twin.id]

    def body_edge_of(self, he: HalfEdge) -> BodyEdge | None:
        """The edge of the body that `he` lies on, if any (seen from a region on one of its sides)."""
        region = he.region if he.region is not None else he.twin.region
        if region is None:
            raise NetInvariantError(f"{he} has no region on either side")
        to_local = region.placement.inverse()
        a, b = to_local.apply(he.origin.position), to_local.apply(he.destination.position)
        return self.body.edge_through(region.face, a, b)

    def segment_faces(self, he: HalfEdge) -> frozenset[Face]:
        """The faces `he` belongs to, which give it its colours: the 2 of the body edge it lies on, or its region's."""
        edge = self.body_edge_of(he)
        if edge is not None:
            return edge.faces
        region = he.region if he.region is not None else he.twin.region
        assert region is not None  # body_edge_of checked it
        return frozenset((region.face,))

    def counterpart(self, boundary_edge: HalfEdge) -> HalfEdge:
        """The other image of the same cut (as an inside half-edge, so it runs the opposite way on the cube)."""
        where, a, b = self._segment_key(boundary_edge)
        return self._boundary_by_segment[(where, b, a)]

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

    def centroid(self) -> Vec | None:
        """The centre of mass of the net's paper, of uniform density: its regions together (its holes are no region;
        where rearranged halves overlap, both count). None if it has no area."""
        return area_centroid(self.region_polygon(r) for r in self.regions)


def _cycle(start: HalfEdge) -> list[HalfEdge]:
    cycle = [start]
    he = start.next
    while he is not start:
        cycle.append(he)
        he = he.next
    return cycle
