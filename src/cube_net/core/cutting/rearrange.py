"""Rearranging the two halves of a split net (docs/idea.txt, CUT_EDITING rule 4; docs/plan.md, section 4.4).

The clicked cut stays where it is; the half that holds its counterpart moves so that the counterpart lies on it, point
by point. The motion is a rotation by a multiple of 90 degrees plus a translation, so all coordinates stay exact. The
two cuts are not glued yet: that happens when the user approves the result.
"""

from dataclasses import dataclass

from cube_net.core.cutting.overlap import overlapping_cuts
from cube_net.core.cutting.split import SplitNet, connected_regions
from cube_net.core.geometry import Rigid90
from cube_net.core.net import HalfEdge, Net


@dataclass(frozen=True, slots=True)
class Rearranged:
    net: Net

    # The clicked cut, which didn't move.
    kept: HalfEdge

    # Its counterpart, moved onto it.
    moved: HalfEdge

    motion: Rigid90

    # The cuts that take part in an overlap of the two halves; empty if the result is valid.
    overlapping: frozenset[HalfEdge]

    @property
    def valid(self) -> bool:
        return not self.overlapping


def rearrange(split: SplitNet, clicked: HalfEdge) -> Rearranged | None:
    """Move the other half so that the counterpart of `clicked` (a cut of `split.net`) lies on it. None if the
    counterpart is in the same half as `clicked`: then no such rearrangement exists."""
    if clicked.region is None:
        raise ValueError(f"expected an inner half-edge of a cut, got {clicked}")
    counterpart = split.net.counterpart(clicked)
    assert counterpart.region is not None
    if counterpart.region in connected_regions(clicked.region):
        return None
    copy = split.net.copy()
    kept, moved = copy.edges[clicked], copy.edges[counterpart]
    motion = Rigid90.from_segments(
        moved.destination.position, moved.origin.position, kept.origin.position, kept.destination.position
    )
    assert moved.region is not None
    regions = connected_regions(moved.region)
    vertices = {he.origin for region in regions for he in Net.region_cycle(region)}
    for vertex in vertices:
        vertex.position = motion.apply(vertex.position)
    for region in regions:
        region.placement = motion @ region.placement
    cycles = copy.net.perimeters()
    outer_kept = next(c for c in cycles if kept.twin in c)
    outer_moved = next(c for c in cycles if moved.twin in c)
    return Rearranged(copy.net, kept, moved, motion, overlapping_cuts(outer_kept, outer_moved))
