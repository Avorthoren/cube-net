"""Do the two rearranged halves of the net overlap? (docs/idea.txt, CUT_APPROVING; docs/plan.md, section 4.5.)

The criterion: the interiors of the two halves must not share any area. Touching is fine: at a point, or along segments
with the net on opposite sides of them.

Each half is free of overlaps by itself (it's a part of a valid net), so only pairs of perimeter segments from different
halves matter. Two of them can:
- cross properly: an overlap;
- meet at a point or along a shared part: then the angular sectors each half occupies around that point (or around the
  middle of the shared part) tell whether the interiors overlap there.
This finds every overlap, because the halves share the glued cut: if one half's boundary enters the other's interior
without crossing anything, then it does so at a contact point, where the sectors overlap.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment, sectors_overlap
from cube_net.core.net import HalfEdge


@dataclass(frozen=True, slots=True)
class _Sector:
    start: Vec
    end: Vec

    # The cuts (inner half-edges) that bound this sector.
    cuts: tuple[HalfEdge, ...]


def overlapping_cuts(half_a: Iterable[HalfEdge], half_b: Iterable[HalfEdge]) -> frozenset[HalfEdge]:
    """The cuts of each half that take part in an overlap with the other; empty if the halves don't overlap.

    `half_a` and `half_b` are the outside half-edges of the two perimeter cycles."""
    outer_a, outer_b = list(half_a), list(half_b)
    bad: set[HalfEdge] = set()
    contacts: set[Vec] = set()
    for a in outer_a:
        for b in outer_b:
            hit = classify_segments(
                a.origin.position, a.destination.position, b.origin.position, b.destination.position
            )
            if hit.kind is IntersectionKind.CROSSING:
                bad.update((a.twin, b.twin))
            elif hit.kind is IntersectionKind.TOUCH:
                contacts.add(hit.point)
            elif hit.kind is IntersectionKind.OVERLAP:
                contacts.add((hit.points[0] + hit.points[1]) / 2)
    for q in contacts:
        for sector_a in _sectors_at(outer_a, q):
            for sector_b in _sectors_at(outer_b, q):
                if sectors_overlap(sector_a.start, sector_a.end, sector_b.start, sector_b.end):
                    bad.update(sector_a.cuts)
                    bad.update(sector_b.cuts)
    return frozenset(bad)


def _sectors_at(outer: list[HalfEdge], q: Vec) -> list[_Sector]:
    """The sectors around `q` occupied by the half with this perimeter cycle (clockwise around the half, so the half is
    on the right of every outside half-edge)."""
    sectors = []
    for he in outer:
        a, b = he.origin.position, he.destination.position
        if a == q:
            incoming = he.prev
            sectors.append(_Sector(incoming.origin.position - q, b - q, (incoming.twin, he.twin)))
        elif b != q and on_segment(q, a, b):
            inner = he.twin
            d = inner.destination.position - inner.origin.position
            sectors.append(_Sector(d, -d, (inner,)))
    return sectors
