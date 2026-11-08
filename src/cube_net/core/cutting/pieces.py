"""Which cube faces a segment of the cut line passes through (for its colours, docs/idea.txt note 3).

A straight segment on the sheet can cross fold edges; on the cube it then goes from one face to another. Split at
those crossings, every piece lies in a single region, so its ends can be expressed as cube surface points.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from cube_net.core.cube import SurfacePoint
from cube_net.core.geometry import Vec, classify_segments, polygon_contains
from cube_net.core.net import Net, Region


@dataclass(frozen=True, slots=True)
class Piece:
    start: Vec
    end: Vec
    start_point: SurfacePoint
    end_point: SurfacePoint


def region_at(net: Net, p: Vec) -> Region | None:
    """A region containing sheet point `p` (on a fold, either of the two)."""
    return next((r for r in net.regions if polygon_contains(net.region_polygon(r), p)), None)


def surface_point_at(net: Net, p: Vec, region: Region | None = None) -> SurfacePoint:
    """The cube surface point at sheet point `p` (which must lie on the net)."""
    region = region or region_at(net, p)
    if region is None:
        raise ValueError(f"{p} is not on the net")
    return SurfacePoint(region.face, region.placement.inverse().apply(p))


def pieces(net: Net, a: Vec, b: Vec) -> list[Piece]:
    """Segment a-b (lying on the net) split at every point where it meets a fold edge."""
    if a == b:
        return []
    d = b - a
    length2 = d.length_squared()
    cuts = {a, b}
    for fold in net.fold_edges():
        for p in classify_segments(a, b, fold.origin.position, fold.destination.position).points:
            cuts.add(p)
    ordered = sorted(cuts, key=lambda p: (p - a).dot(d) / length2)
    result = []
    for start, end in pairwise(ordered):
        region = region_at(net, (start + end) / 2)
        if region is None:
            raise ValueError(f"segment {a} - {b} leaves the net")
        result.append(Piece(start, end, surface_point_at(net, start, region), surface_point_at(net, end, region)))
    return result


def crossings(net: Net, positions: Sequence[Vec]) -> list[Vec]:
    """Where the polyline through `positions` meets cube edges between its own points (in order along the line).

    These are vertices of the new cut line too (docs/idea.txt, note 3): when the line becomes cuts, every piece between
    two consecutive vertices lies in one face (or along one cube edge). They are derived from the line, so they follow
    its points when those move.
    """
    own = set(positions)
    result: list[Vec] = []
    for a, b in pairwise(positions):
        for piece in pieces(net, a, b)[:-1]:
            if piece.end not in own:
                result.append(piece.end)
    return result
