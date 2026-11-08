import random
from fractions import Fraction as F
from itertools import pairwise

import pytest
from net_checks import overlap_area

from cube_net.core.cube import SurfacePoint
from cube_net.core.cutting import CutLine, CutPoint, SplitNet, overlapping_cuts, rearrange, segment_valid, split_net
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.net import EdgeKind, HalfEdge, Net, NetVertex, Region, default_net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def outer_ring(*corners: tuple[int | F, int | F]) -> list[HalfEdge]:
    """The outside half-edges of a polygon given counter-clockwise (they run clockwise, each with its inner twin)."""
    point = SurfacePoint(1, Vec(0, 0))
    region = Region(0, 1, None)  # type: ignore[arg-type]
    vertices = [NetVertex(i, Vec(x, y), point) for i, (x, y) in enumerate(corners)]
    n = len(vertices)
    inner = [HalfEdge(i, vertices[i], EdgeKind.BOUNDARY, region) for i in range(n)]
    outer = [HalfEdge(n + i, vertices[(i + 1) % n], EdgeKind.BOUNDARY, None) for i in range(n)]
    for i in range(n):
        inner[i].twin, outer[i].twin = outer[i], inner[i]
    ring = list(reversed(outer))  # clockwise
    for a, b in pairwise([*ring, ring[0]]):
        a.next, b.prev = b, a
    return ring


def square(x: int | F, y: int | F, size: int | F = 1) -> list[HalfEdge]:
    return outer_ring((x, y), (x + size, y), (x + size, y + size), (x, y + size))


class TestTouchingIsFine:
    def test_apart(self) -> None:
        assert overlapping_cuts(square(0, 0), square(5, 5)) == frozenset()

    def test_sharing_a_whole_side_from_opposite_sides(self) -> None:
        assert overlapping_cuts(square(0, 0), square(1, 0)) == frozenset()

    def test_sharing_a_part_of_a_side(self) -> None:
        assert overlapping_cuts(square(0, 0), square(1, F(1, 2))) == frozenset()

    def test_touching_at_a_corner(self) -> None:
        assert overlapping_cuts(square(0, 0), square(1, 1)) == frozenset()

    def test_a_corner_touching_a_side_from_outside(self) -> None:
        diamond = outer_ring((2, 1), (3, F(1, 2)), (4, 1), (3, F(3, 2)))  # its left corner touches x = 2 ...
        assert overlapping_cuts(square(0, 0, 2), diamond) == frozenset()

    def test_in_a_notch_of_the_other(self) -> None:
        l_shape = outer_ring((0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2))
        assert overlapping_cuts(l_shape, square(1, 1)) == frozenset()  # touches both sides of the reflex corner


class TestOverlapping:
    def test_crossing_sides(self) -> None:
        a, b = square(0, 0), square(F(1, 2), F(1, 2))
        assert overlapping_cuts(a, b)

    def test_the_same_square(self) -> None:
        assert overlapping_cuts(square(0, 0), square(0, 0))

    def test_collinear_sides_with_the_net_on_the_same_side(self) -> None:
        narrow = outer_ring((0, 0), (F(1, 2), 0), (F(1, 2), 1), (0, 1))
        assert overlapping_cuts(square(0, 0), narrow)

    def test_a_corner_poking_through_a_side(self) -> None:
        diamond = outer_ring((1, F(1, 2)), (2, 0), (3, F(1, 2)), (2, 1))  # its left corner is ON the side x = 2 ...
        poking = outer_ring((F(3, 2), F(1, 2)), (2, 0), (3, F(1, 2)), (2, 1))  # ... this one goes through it
        assert overlapping_cuts(square(0, 0, 2), poking)
        assert overlapping_cuts(square(0, 0, 2), diamond)

    def test_inside_sharing_only_a_corner(self) -> None:
        assert overlapping_cuts(square(0, 0, 2), square(0, 0))

    def test_inside_with_a_corner_touching_a_side(self) -> None:
        inside = outer_ring((0, 1), (1, F(1, 2)), (F(3, 2), 1), (1, F(3, 2)))  # a diamond whose left corner is on x = 0
        assert overlapping_cuts(square(0, 0, 2), inside)

    def test_names_the_cuts_involved(self) -> None:
        a, b = square(0, 0), square(F(1, 2), F(1, 2))
        bad = overlapping_cuts(a, b)
        assert all(he.region is not None for he in bad)  # inner half-edges
        assert {he.twin for he in bad} <= set(a) | set(b)
        assert {he.twin for he in bad} & set(a) and {he.twin for he in bad} & set(b)


def line_cut(net: Net, a: Vec, b: Vec) -> tuple[CutPoint, CutPoint]:
    def on(point: Vec) -> CutPoint:
        edge = next(he for he in net.boundary_edges() if on_segment(point, he.origin.position, he.destination.position))
        return CutPoint(point, edge)

    return on(a), on(b)


def cut_between(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {a, b})


def assert_agrees_with_exact_area(split: SplitNet, cut: HalfEdge) -> bool:
    """The verdict of the overlap test must match the area actually shared. Returns whether a rearrangement exists."""
    result = rearrange(split, cut)
    if result is None:
        return False
    cycles = result.net.perimeters()
    kept = next(c for c in cycles if result.kept.twin in c)
    moved = next(c for c in cycles if result.moved.twin in c)
    area = overlap_area(kept, moved)
    assert result.valid == (area == 0), (cut.origin.position, cut.destination.position, area)
    return True


class TestOnRealNets:
    def test_two_images_of_one_point_leave_nothing_to_glue(self) -> None:
        """A closed loop on the cube (docs/idea.txt): the line splits the net, but every cut stays within its half."""
        net = default_net()
        start, end = line_cut(net, v("11.5", "14"), v("11.5", "10"))
        split = split_net(net, CutLine([start, end]))
        cuts = [he for he in split.net.boundary_edges() if he not in split.line_edges]
        assert cuts
        assert all(rearrange(split, he) is None for he in cuts)

    def test_the_corner_cut_from_idea_is_valid(self) -> None:
        net = default_net()
        start, end = line_cut(net, v("11.5", "14"), v("12", "13.5"))
        split = split_net(net, CutLine([start, CutPoint(v("11.5", "13.5")), end]))
        result = rearrange(split, cut_between(split.net, v("11.5", "10"), Vec(12, 10)))
        assert result is not None and result.valid and result.overlapping == frozenset()

    def test_every_glue_of_a_face_cut_off_along_a_fold_is_valid(self) -> None:
        """Whole faces landing on free squares of the grid only touch."""
        net = default_net()
        c1 = next(w for w in net.boundary_vertices() if w.position == Vec(11, 13))
        d1 = next(w for w in net.boundary_vertices() if w.position == Vec(12, 13))
        edge = next(he for he in net.boundary_edges() if he.origin is c1)
        edge2 = next(he for he in net.boundary_edges() if he.origin is d1)
        split = split_net(net, CutLine([CutPoint(c1.position, edge, c1), CutPoint(d1.position, edge2, d1)]))
        results = [rearrange(split, he) for he in split.net.boundary_edges() if he not in split.line_edges]
        moved = [r for r in results if r is not None]
        assert moved
        assert all(r.valid for r in moved)

    def test_a_big_part_turned_onto_the_rest_overlaps(self) -> None:
        net = default_net()
        start, end = line_cut(net, v("12", "13.5"), v("11", "11.5"))
        split = split_net(net, CutLine([start, end]))
        result = rearrange(split, cut_between(split.net, Vec(13, 13), v("12.5", "13")))
        assert result is not None
        assert not result.valid
        assert all(he in result.net.boundary_edges() for he in result.overlapping)
        assert result.kept not in result.overlapping and result.moved not in result.overlapping

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            (v("12", "13.5"), v("11", "11.5")),
            (v("11.5", "14"), v("11", "11.5")),
            (v("11.5", "14"), v("11.25", "10")),
            (v("10", "12.5"), v("13", "12.5")),
            (v("10.5", "13"), v("12.5", "12")),
        ],
    )
    def test_agrees_with_sampling_points(self, a: Vec, b: Vec) -> None:
        net = default_net()
        start, end = line_cut(net, a, b)
        split = split_net(net, CutLine([start, end]))
        cuts = [he for he in split.net.boundary_edges() if he not in split.line_edges]
        assert any([assert_agrees_with_exact_area(split, he) for he in cuts])

    def test_agrees_on_random_lines(self) -> None:
        """The same on a fixed random sample of straight lines across the net (2008 rearrangements agreed when this
        was checked at a larger scale)."""
        rng = random.Random(11)
        rearrangements = 0
        for _ in range(60):
            net = default_net()
            e1, e2 = rng.sample(net.boundary_edges(), 2)
            t1, t2 = F(rng.randint(1, 9), 10), F(rng.randint(1, 9), 10)
            a = e1.origin.position + (e1.destination.position - e1.origin.position) * t1
            b = e2.origin.position + (e2.destination.position - e2.origin.position) * t2
            points = [CutPoint(a, e1), CutPoint(b, e2)]
            if not segment_valid(net, points, 0):
                continue
            split = split_net(net, CutLine(points))
            for he in split.net.boundary_edges():
                if he not in split.line_edges and assert_agrees_with_exact_area(split, he):
                    rearrangements += 1
        assert rearrangements > 50


class TestExactAreaHelper:
    def test_known_areas(self) -> None:
        assert overlap_area(square(0, 0), square(5, 5)) == 0
        assert overlap_area(square(0, 0), square(1, 0)) == 0
        assert overlap_area(square(0, 0), square(F(1, 2), F(1, 2))) == F(1, 4)
        assert overlap_area(square(0, 0, 2), square(0, 0)) == 1
