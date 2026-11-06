"""`Net`: the cube net on the sheet as a DCEL of `NetVertex`, `HalfEdge` and `Region` (docs/plan.md, section 3.3).

Build one with `build_net()` (or `default_net()`). Queries return fresh lists; lookup indices are rebuilt by
`reindex()` after every structural change (cheap at this size).
"""

from __future__ import annotations

from collections.abc import Iterable

from cube_net.core.cube import SurfacePoint
from cube_net.core.geometry import Box, Vec, polygon_contains
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region


class NetInvariantError(RuntimeError):
    """The net's structure is inconsistent. Always a bug in the code that built or changed the net."""


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

    # --- regions ----------------------------------------------------------------------------------------------------

    @staticmethod
    def region_cycle(region: Region) -> list[HalfEdge]:
        """The region's half-edges, counter-clockwise."""
        return _cycle(region.edge)

    def region_polygon(self, region: Region) -> list[Vec]:
        """The region's corner positions on the sheet, counter-clockwise."""
        return [he.origin.position for he in self.region_cycle(region)]

    # --- edges ------------------------------------------------------------------------------------------------------

    def perimeter(self) -> list[HalfEdge]:
        """The outside half-edges, in order along the perimeter (clockwise around the net)."""
        start = next(he for he in self.half_edges if he.region is None)
        return _cycle(start)

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
        """Vertices on the perimeter, in perimeter order."""
        return [he.origin for he in self.perimeter()]

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
