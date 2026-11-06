"""The building blocks of the net's DCEL (doubly connected edge list): vertices, half-edges, regions.

They reference each other, so they live together in one module. They are plain mutable objects compared by
identity; `Net` and its builder keep them consistent (docs/plan.md, section 3.3).

Conventions:
- Every edge has two half-edges (`twin`s). Half-edges of a region go counter-clockwise around it.
- A half-edge with `region is None` lies on the outside of the net. The outside half-edges form the perimeter
  cycle, which goes clockwise around the net.
"""

from __future__ import annotations

from enum import Enum

from cube_net.core.cube import Face, SurfacePoint
from cube_net.core.geometry import Rigid90, Vec


class EdgeKind(Enum):
    # A cube edge inside the net (always drawn).
    FOLD = "fold"

    # A glued user cut inside the net (never drawn; exists only transiently, see docs/plan.md section 4.6).
    SEAM = "seam"

    # A segment of the outer perimeter: a cut.
    BOUNDARY = "boundary"


class NetVertex:
    """An image of a cube surface point on the sheet. Several vertices can be images of the same `point`."""

    __slots__ = ("edge", "id", "point", "position")

    id: int
    position: Vec
    point: SurfacePoint

    # Some half-edge that starts at this vertex.
    edge: HalfEdge

    def __init__(self, vertex_id: int, position: Vec, point: SurfacePoint) -> None:
        self.id = vertex_id
        self.position = position
        self.point = point

    def __repr__(self) -> str:
        return f"NetVertex#{self.id}({self.position}, {self.point})"


class HalfEdge:
    """One side of an edge, directed from `origin` to `twin.origin`."""

    __slots__ = ("id", "kind", "next", "origin", "prev", "region", "twin")

    id: int
    origin: NetVertex
    kind: EdgeKind

    # The region on the left of this half-edge, or None for the outside of the net.
    region: Region | None

    twin: HalfEdge
    next: HalfEdge
    prev: HalfEdge

    def __init__(self, edge_id: int, origin: NetVertex, kind: EdgeKind, region: Region | None) -> None:
        self.id = edge_id
        self.origin = origin
        self.kind = kind
        self.region = region

    @property
    def destination(self) -> NetVertex:
        return self.twin.origin

    @property
    def is_outside(self) -> bool:
        return self.region is None

    def __repr__(self) -> str:
        side = "outside" if self.region is None else f"region#{self.region.id}"
        return f"HalfEdge#{self.id}({self.kind.name}, {self.origin.position} -> {self.destination.position}, {side})"


class Region:
    """A polygon of the net lying inside a single cube face."""

    __slots__ = ("edge", "face", "id", "placement")

    id: int
    face: Face

    # Maps the face's local frame to the sheet (used for colours and the hatch pattern).
    placement: Rigid90

    # Some half-edge of this region's boundary cycle.
    edge: HalfEdge

    def __init__(self, region_id: int, face: Face, placement: Rigid90) -> None:
        self.id = region_id
        self.face = face
        self.placement = placement

    def __repr__(self) -> str:
        return f"Region#{self.id}(face {self.face}, {self.placement})"
