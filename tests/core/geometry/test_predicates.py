from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.geometry.predicates import (
    IntersectionKind,
    SegmentIntersection,
    classify_segments,
    on_segment,
    orient,
)

K = IntersectionKind

# A small integer grid makes degenerate configurations (collinear, shared endpoints, T-touches) very frequent.
grid = st.builds(Vec, st.integers(-3, 3), st.integers(-3, 3))
segments = st.tuples(grid, grid).filter(lambda s: s[0] != s[1])
motions = st.builds(Rigid90, st.integers(0, 3), st.builds(Vec, st.fractions(-5, 5), st.fractions(-5, 5)))


def v(x: int | F, y: int | F) -> Vec:
    return Vec(x, y)


class TestOrient:
    def test_signs(self) -> None:
        assert orient(v(0, 0), v(1, 0), v(0, 1)) == 1
        assert orient(v(0, 0), v(0, 1), v(1, 0)) == -1
        assert orient(v(0, 0), v(1, 1), v(F(1, 3), F(1, 3))) == 0

    def test_tiny_offsets_are_exact(self) -> None:
        eps = F(1, 10**30)
        assert orient(v(0, 0), v(1, 1), v(F(1, 2), F(1, 2) + eps)) == 1
        assert orient(v(0, 0), v(1, 1), v(F(1, 2), F(1, 2) - eps)) == -1

    @pytest.mark.parametrize(
        "c",
        [
            v(4, 0),  # angle abc = 180 degrees: c continues straight past b
            v(1, 0),  # angle abc = 0 degrees: c goes back towards a, stopping between a and b
            v(-3, 0),  # angle abc = 0 degrees: c goes back past a
            v(0, 0),  # c coincides with a
            v(2, 0),  # c coincides with b
        ],
    )
    def test_zero_for_every_collinear_configuration(self, c: Vec) -> None:
        """`orient` only tells which side of line a-b the point c is on. It does NOT distinguish 0 from 180 degrees
        (or coincident points); callers that care must use `classify_segments` (see TestStraightVsBacktrack)."""
        assert orient(v(0, 0), v(2, 0), c) == 0

    @given(grid, grid, grid)
    def test_swap_flips_sign(self, a: Vec, b: Vec, c: Vec) -> None:
        assert orient(a, b, c) == -orient(b, a, c)
        assert orient(a, b, c) == orient(b, c, a)


class TestOnSegment:
    @pytest.mark.parametrize(
        ("p", "expected"),
        [
            (v(0, 0), True),  # endpoint
            (v(2, 2), True),  # endpoint
            (v(1, 1), True),  # inside
            (v(3, 3), False),  # on the line, beyond the end
            (v(-1, -1), False),  # on the line, before the start
            (v(1, F(1001, 1000)), False),  # just off the line
        ],
    )
    def test_cases(self, p: Vec, expected: bool) -> None:
        assert on_segment(p, v(0, 0), v(2, 2)) is expected

    def test_axis_aligned(self) -> None:
        assert on_segment(v(5, 0), v(0, 0), v(10, 0))
        assert not on_segment(v(11, 0), v(0, 0), v(10, 0))

    def test_degenerate_segment(self) -> None:
        assert on_segment(v(1, 1), v(1, 1), v(1, 1))
        assert not on_segment(v(1, 2), v(1, 1), v(1, 1))


class TestClassify:
    def test_disjoint_non_parallel(self) -> None:
        assert classify_segments(v(0, 0), v(1, 0), v(2, -1), v(2, 1)).kind is K.DISJOINT

    def test_disjoint_parallel(self) -> None:
        assert classify_segments(v(0, 0), v(2, 0), v(0, 1), v(2, 1)).kind is K.DISJOINT

    def test_disjoint_collinear_with_gap(self) -> None:
        assert classify_segments(v(0, 0), v(1, 0), v(2, 0), v(3, 0)).kind is K.DISJOINT

    def test_proper_crossing(self) -> None:
        result = classify_segments(v(0, 0), v(2, 2), v(0, 2), v(2, 0))
        assert result == SegmentIntersection(K.CROSSING, (v(1, 1),))
        assert result.point == v(1, 1)

    def test_crossing_point_is_exact(self) -> None:
        result = classify_segments(v(0, 0), v(3, 1), v(0, 1), v(1, 0))
        assert result.kind is K.CROSSING
        assert result.point == v(F(3, 4), F(1, 4))

    def test_touch_shared_endpoint(self) -> None:
        assert classify_segments(v(0, 0), v(1, 0), v(1, 0), v(1, 1)) == SegmentIntersection(K.TOUCH, (v(1, 0),))

    def test_touch_t_shape(self) -> None:
        # Endpoint of the second segment lies strictly inside the first one, and vice versa.
        assert classify_segments(v(0, 0), v(2, 0), v(1, 0), v(1, 1)) == SegmentIntersection(K.TOUCH, (v(1, 0),))
        assert classify_segments(v(1, 0), v(1, 1), v(0, 0), v(2, 0)) == SegmentIntersection(K.TOUCH, (v(1, 0),))

    def test_touch_collinear_end_to_end(self) -> None:
        assert classify_segments(v(0, 0), v(1, 0), v(1, 0), v(3, 0)) == SegmentIntersection(K.TOUCH, (v(1, 0),))

    def test_overlap_partial_ordered_along_first(self) -> None:
        assert classify_segments(v(0, 0), v(2, 0), v(3, 0), v(1, 0)) == SegmentIntersection(
            K.OVERLAP, (v(1, 0), v(2, 0))
        )
        assert classify_segments(v(2, 0), v(0, 0), v(3, 0), v(1, 0)) == SegmentIntersection(
            K.OVERLAP, (v(2, 0), v(1, 0))
        )

    def test_overlap_containment_and_identical(self) -> None:
        assert classify_segments(v(0, 0), v(4, 4), v(1, 1), v(2, 2)).points == (v(1, 1), v(2, 2))
        assert classify_segments(v(1, 1), v(2, 2), v(0, 0), v(4, 4)).points == (v(1, 1), v(2, 2))
        assert classify_segments(v(0, 0), v(1, 0), v(1, 0), v(0, 0)).points == (v(0, 0), v(1, 0))

    def test_point_property_rejects_non_single(self) -> None:
        with pytest.raises(ValueError):
            _ = classify_segments(v(0, 0), v(1, 0), v(5, 5), v(6, 6)).point
        with pytest.raises(ValueError):
            _ = classify_segments(v(0, 0), v(2, 0), v(1, 0), v(3, 0)).point

    def test_degenerate_rejected(self) -> None:
        with pytest.raises(ValueError, match="degenerate"):
            classify_segments(v(0, 0), v(0, 0), v(0, 0), v(1, 0))
        with pytest.raises(ValueError, match="degenerate"):
            classify_segments(v(0, 0), v(1, 0), v(1, 1), v(1, 1))


class TestStraightVsBacktrack:
    """Two consecutive segments a-b and b-c of a polyline (e.g. the cut line) with collinear a, b, c.

    `orient(a, b, c)` is 0 in all these cases; `classify_segments` is what tells them apart: going straight on
    (180 degrees at b) is a TOUCH at b, going back (0 degrees at b) is an OVERLAP, which a cut line must reject.
    """

    a, b = v(0, 0), v(2, 0)

    def test_straight_on_is_touch_at_shared_point(self) -> None:
        result = classify_segments(self.a, self.b, self.b, v(5, 0))
        assert result == SegmentIntersection(K.TOUCH, (self.b,))

    def test_back_short_of_start_is_overlap(self) -> None:
        result = classify_segments(self.a, self.b, self.b, v(1, 0))
        assert result == SegmentIntersection(K.OVERLAP, (v(1, 0), self.b))

    def test_back_exactly_to_start_is_overlap(self) -> None:
        result = classify_segments(self.a, self.b, self.b, self.a)
        assert result == SegmentIntersection(K.OVERLAP, (self.a, self.b))

    def test_back_past_start_is_overlap(self) -> None:
        result = classify_segments(self.a, self.b, self.b, v(-3, 0))
        assert result == SegmentIntersection(K.OVERLAP, (self.a, self.b))

    @given(segments, st.integers(1, 3))
    def test_any_direction_straight_vs_back(self, seg: tuple[Vec, Vec], k: int) -> None:
        a, b = seg
        d = b - a
        assert classify_segments(a, b, b, b + d * k).kind is K.TOUCH
        assert classify_segments(a, b, b, b - d * k).kind is K.OVERLAP
        assert classify_segments(a, b, b, b - d / (k + 1)).kind is K.OVERLAP


class TestClassifyProperties:
    @given(segments, segments)
    def test_symmetric(self, a: tuple[Vec, Vec], b: tuple[Vec, Vec]) -> None:
        ab = classify_segments(*a, *b)
        ba = classify_segments(*b, *a)
        assert ab.kind is ba.kind
        assert set(ab.points) == set(ba.points)

    @given(segments, segments)
    def test_independent_of_direction(self, a: tuple[Vec, Vec], b: tuple[Vec, Vec]) -> None:
        base = classify_segments(*a, *b)
        reversed_b = classify_segments(*a, b[1], b[0])
        reversed_a = classify_segments(a[1], a[0], *b)
        assert base == reversed_b
        assert base.kind is reversed_a.kind
        assert set(base.points) == set(reversed_a.points)

    @given(segments, segments, motions)
    def test_invariant_under_rigid_motion(self, a: tuple[Vec, Vec], b: tuple[Vec, Vec], m: Rigid90) -> None:
        base = classify_segments(*a, *b)
        moved = classify_segments(m.apply(a[0]), m.apply(a[1]), m.apply(b[0]), m.apply(b[1]))
        assert moved.kind is base.kind
        assert moved.points == tuple(m.apply(p) for p in base.points)

    @given(segments, segments)
    def test_result_points_lie_on_both_segments(self, a: tuple[Vec, Vec], b: tuple[Vec, Vec]) -> None:
        result = classify_segments(*a, *b)
        for p in result.points:
            assert on_segment(p, *a)
            assert on_segment(p, *b)

    @given(segments, segments)
    def test_kind_matches_definition(self, a: tuple[Vec, Vec], b: tuple[Vec, Vec]) -> None:
        result = classify_segments(*a, *b)
        endpoints = {*a, *b}
        match result.kind:
            case K.CROSSING:
                assert result.point not in endpoints
            case K.TOUCH:
                assert result.point in endpoints
            case K.OVERLAP:
                p, q = result.points
                assert p != q
                assert orient(*a, b[0]) == 0 and orient(*a, b[1]) == 0
            case K.DISJOINT:
                assert not any(on_segment(p, *b) for p in a)
                assert not any(on_segment(p, *a) for p in b)


class TestAgainstTheDefinitions:
    """The hot code takes shortcuts; these are the plain formulas it must agree with, everywhere."""

    @given(grid, grid, grid)
    def test_orient(self, a: Vec, b: Vec, c: Vec) -> None:
        cross = (b - a).cross(c - a)
        assert orient(a, b, c) == (cross > 0) - (cross < 0)

    @given(grid, grid, grid)
    def test_on_segment(self, p: Vec, a: Vec, b: Vec) -> None:
        expected = (
            (b - a).cross(p - a) == 0
            and min(a.x, b.x) <= p.x <= max(a.x, b.x)
            and min(a.y, b.y) <= p.y <= max(a.y, b.y)
        )
        assert on_segment(p, a, b) == expected

    @given(grid, grid, st.integers(0, 10))
    def test_points_between_are_on_it(self, a: Vec, b: Vec, step: int) -> None:
        assert on_segment(a + (b - a) * F(step, 10), a, b)
