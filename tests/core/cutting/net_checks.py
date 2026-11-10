# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""A structural consistency check for nets, shared by the tests in this folder."""

from collections.abc import Sequence
from fractions import Fraction as F
from itertools import pairwise

from cube_net.core.geometry import Vec, classify_segments, signed_area
from cube_net.core.net import HalfEdge, Net


def assert_consistent(net: Net) -> None:
    """Everything that must hold for any net, split or not: the links, the areas, and where the regions are."""
    for he in net.half_edges:
        assert he.next.prev is he and he.prev.next is he
        assert he.twin.twin is he and he.twin is not he
        assert he.next.origin is he.twin.origin, f"{he} doesn't lead to {he.next}"
        assert he.next.region is he.region
        assert he.origin.position != he.destination.position
    for v in net.vertices:
        assert v.edge.origin is v
    for he in net.half_edges:
        assert he.origin in net.vertices
    total = F(0)
    for region in net.regions:
        assert region.edge.region is region
        polygon = net.region_polygon(region)
        assert signed_area(polygon) > 0, f"{region} isn't counter-clockwise"
        total += signed_area(polygon)
        for he in net.region_cycle(region):
            assert region.face in he.origin.point.faces
            assert region.placement.apply(he.origin.point.local_in(region.face)) == he.origin.position
    assert total == 6
    assert {he for cycle in net.perimeters() for he in cycle} == {he for he in net.half_edges if he.region is None}
    net.reindex()  # every cut has exactly two images
    for he in net.boundary_edges():
        other = net.counterpart(he)
        assert net.counterpart(other) is he
        d1, d2 = he.destination.position - he.origin.position, other.destination.position - other.origin.position
        assert d1.length_squared() == d2.length_squared()


def overlap_area(outer_a: Sequence[HalfEdge], outer_b: Sequence[HalfEdge]) -> F:
    """The exact area shared by two parts of a net, given their perimeter cycles. Independent of the overlap test.

    Between consecutive event x-values (vertices and crossings of the two outlines) the shared height is linear in x, so
    a slab's area is its width times the shared height at its middle.
    """
    segments_a = [(he.origin.position, he.destination.position) for he in outer_a]
    segments_b = [(he.origin.position, he.destination.position) for he in outer_b]
    xs = {p.x for segment in (*segments_a, *segments_b) for p in segment}
    for sa in segments_a:
        for sb in segments_b:
            xs.update(p.x for p in classify_segments(*sa, *sb).points)
    total = F(0)
    for x0, x1 in pairwise(sorted(xs)):
        middle = (x0 + x1) / 2
        total += (x1 - x0) * _shared_height(_spans(segments_a, middle), _spans(segments_b, middle))
    return total


def _spans(segments: list[tuple[Vec, Vec]], x: F) -> list[tuple[F, F]]:
    """The parts of the vertical line at `x` inside the polygon (even-odd rule)."""
    ys = sorted(a.y + (x - a.x) * (b.y - a.y) / (b.x - a.x) for a, b in segments if (a.x < x) != (b.x < x))
    return [(ys[i], ys[i + 1]) for i in range(0, len(ys), 2)]


def _shared_height(spans_a: list[tuple[F, F]], spans_b: list[tuple[F, F]]) -> F:
    return sum((max(F(0), min(a1, b1) - max(a0, b0)) for a0, a1 in spans_a for b0, b1 in spans_b), F(0))
