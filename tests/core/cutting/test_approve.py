import random
from collections import deque
from fractions import Fraction as F

import pytest

from cube_net.core.cutting import (
    CutLine,
    CutPoint,
    Rearranged,
    SplitNet,
    approve,
    rearrange,
    segment_valid,
    split_net,
    strictly_inside,
)
from cube_net.core.geometry import Rigid90, Vec, on_segment, signed_area
from cube_net.core.net import EdgeKind, HalfEdge, Net, boundary_edge_from, default_net, validate_net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def on(net: Net, p: Vec) -> CutPoint:
    """The cut-line point at perimeter position `p`: a vertex, or a point on a cut."""
    for w in net.boundary_vertices():
        if w.position == p:
            return CutPoint(p, boundary_edge_from(net, w), w)
    return CutPoint(
        p, next(he for he in net.boundary_edges() if on_segment(p, he.origin.position, he.destination.position))
    )


def cut_between(split: SplitNet, a: Vec, b: Vec) -> HalfEdge:
    return next(
        he
        for he in split.net.boundary_edges()
        if he not in split.line_edges and {he.origin.position, he.destination.position} == {a, b}
    )


def corner_rearranged(net: Net) -> Rearranged:
    """docs/idea.txt: the corner cut x-y-z, with x-B glued to its image at the bottom of face 5."""
    split = split_net(net, CutLine([on(net, v("11.5", "14")), CutPoint(v("11.5", "13.5")), on(net, v("12", "13.5"))]))
    result = rearrange(split, cut_between(split, v("11.5", "10"), Vec(12, 10)))
    assert result is not None
    return result


def corner_net() -> Net:
    return approve(corner_rearranged(default_net()))


class TestCornerCutFromIdea:
    def test_the_perimeter_is_the_one_in_the_drawing(self) -> None:
        positions = [he.origin.position for he in corner_net().perimeter()]
        expected = [
            Vec(11, 14),  # A_1
            v("11.5", "14"),  # x_1
            v("11.5", "13.5"),  # y_1
            v("12", "13.5"),  # z_1
            Vec(12, 13),  # D_1
            v("12.5", "13"),  # z_3
            Vec(13, 13),  # B_2
            Vec(13, 12),  # F_2
            Vec(12, 12),  # G_1
            Vec(12, 11),  # F_1
            Vec(12, 10),  # B_3
            v("12", "9.5"),  # z_2
            v("11.5", "9.5"),  # y_2
            v("11.5", "10"),  # x_2
            Vec(11, 10),  # A_3
            Vec(11, 11),  # E_1
            Vec(11, 12),  # H_1
            Vec(10, 12),  # E_2
            Vec(10, 13),  # A_2
            Vec(11, 13),  # C_1
        ]
        start = positions.index(Vec(11, 14))
        assert positions[start:] + positions[:start] == expected

    def test_the_glued_part_is_now_a_fold_between_faces_1_and_5(self) -> None:
        net = corner_net()
        ends = {frozenset((he.origin.position, he.destination.position)) for he in net.fold_edges()}
        assert frozenset((v("11.5", "10"), Vec(12, 10))) in ends
        assert len(net.fold_edges()) == 6
        assert sorted(r.face for r in net.regions) == [1, 1, 2, 3, 4, 5, 6]

    def test_the_new_cuts_are_paired(self) -> None:
        net = corner_net()
        validate_net(net)
        x_y = next(
            he
            for he in net.boundary_edges()
            if {he.origin.position, he.destination.position} == {v("11.5", "14"), v("11.5", "13.5")}
        )
        other = net.counterpart(x_y)
        assert {other.origin.position, other.destination.position} == {v("11.5", "10"), v("11.5", "9.5")}

    def test_the_rearranged_net_itself_does_not_change(self) -> None:
        rearranged = corner_rearranged(default_net())
        count = len(rearranged.net.half_edges)
        approve(rearranged)
        assert len(rearranged.net.half_edges) == count
        assert len(rearranged.net.perimeters()) == 2


class TestGluingBack:
    def back(self) -> Net:
        """Cut the piece off the corner-cut net again and glue it where it came from."""
        net = corner_net()
        split = split_net(net, CutLine([on(net, v("11.5", "10")), on(net, Vec(12, 10))]))
        result = rearrange(split, cut_between(split, v("11.5", "14"), v("11.5", "13.5")))
        assert result is not None and result.valid
        assert result.motion == Rigid90.translation(Vec(0, 4))
        return approve(result)

    def test_gives_exactly_the_cross(self) -> None:
        """Gluing x-y zips y-z too; the seams, y, and the now pointless x and z all disappear."""
        back, cross = self.back(), default_net()
        assert {w.position for w in back.vertices} == {w.position for w in cross.vertices}
        assert len(back.regions) == 6 and len(back.fold_edges()) == 5 and len(back.perimeter()) == 14
        assert sorted(r.face for r in back.regions) == [1, 2, 3, 4, 5, 6]

    def test_no_seams_or_inner_vertices_remain(self) -> None:
        back = self.back()
        assert not any(he.kind is EdgeKind.SEAM for he in back.half_edges)
        validate_net(back)


class TestZip:
    def test_stops_at_a_cube_vertex(self) -> None:
        """Face 1 cut off along C-D and glued back along A-C: A-C can't go on to A-B, the images of A differ."""
        net = default_net()
        split = split_net(net, CutLine([on(net, Vec(11, 13)), on(net, Vec(12, 13))]))
        result = rearrange(split, cut_between(split, Vec(10, 13), Vec(11, 13)))
        assert result is not None and result.valid
        glued = approve(result)
        assert len(glued.fold_edges()) == 5
        assert len(glued.perimeter()) == 14

    def test_a_bent_line_zips_through_its_bends(self) -> None:
        """Gluing back only the first piece of a bent cut closes all of it: not just collinear neighbours."""
        net = default_net()
        line = CutLine(
            [
                on(net, v("11.2", "14")),
                CutPoint(v("11.5", "13.5")),
                CutPoint(v("11.2", "13.2")),
                on(net, v("11", "13.5")),
            ]
        )
        piece = approve(_any_valid_move(net, line))
        validate_net(piece)
        assert len(piece.regions) == 7

    def test_overlap_cannot_be_approved(self) -> None:
        net = default_net()
        split = split_net(net, CutLine([on(net, v("12", "13.5")), on(net, v("11", "11.5"))]))
        result = rearrange(split, cut_between(split, Vec(13, 13), v("12.5", "13")))
        assert result is not None and not result.valid
        with pytest.raises(ValueError, match="overlapping"):
            approve(result)


def _any_valid_move(net: Net, line: CutLine) -> Rearranged:
    split = split_net(net, line)
    for he in split.net.boundary_edges():
        if he in split.line_edges:
            continue
        result = rearrange(split, he)
        if result is not None and result.valid:
            return result
    raise AssertionError("no valid rearrangement")


def free_polyomino(net: Net) -> tuple[tuple[int, int], ...]:
    """The shape of a net made of whole unit squares, the same for all its rotations and reflections."""
    cells = []
    for region in net.regions:
        corner = min(net.region_polygon(region), key=lambda p: (p.x, p.y))
        cells.append((int(corner.x), int(corner.y)))
    forms = []
    for mirror in (1, -1):
        shape = [(mirror * x, y) for x, y in cells]
        for _ in range(4):
            shape = [(-y, x) for x, y in shape]
            low_x, low_y = min(x for x, _ in shape), min(y for _, y in shape)
            forms.append(tuple(sorted((x - low_x, y - low_y) for x, y in shape)))
    return min(forms)


def test_exactly_the_11_cube_nets_are_reachable_along_folds() -> None:
    """The main acceptance test (docs/plan.md, M7): cutting along fold lines and gluing elsewhere, from the cross,
    reaches all 11 hexomino nets of the cube, and nothing else. Every result passes `validate_net` inside `approve`."""
    start = default_net()
    seen = {free_polyomino(start)}
    queue = deque([start])
    while queue:
        net = queue.popleft()
        for fold in net.fold_edges():
            line = CutLine([on(net, fold.origin.position), on(net, fold.destination.position)])
            split = split_net(net, line)
            for he in split.net.boundary_edges():
                if he in split.line_edges or he in split.same_half_cuts:
                    continue
                result = rearrange(split, he)
                if result is None or not result.valid:
                    continue
                glued = approve(result)
                assert all(signed_area(glued.region_polygon(r)) == 1 for r in glued.regions)
                shape = free_polyomino(glued)
                if shape not in seen:
                    seen.add(shape)
                    queue.append(glued)
    assert len(seen) == 11
    cross = free_polyomino(default_net())
    long_stairs = ((0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3))
    assert cross in seen and long_stairs in seen


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_chains_of_cuts_stay_valid(seed: int) -> None:
    """Random cuts through random points, each result validated, each on top of the previous one."""
    rng = random.Random(seed)
    net = default_net()
    approved = 0
    for _ in range(120):
        if approved == 8:
            break
        line = _random_line(net, rng)
        if line is None:
            continue
        split = split_net(net, line)
        cuts = [
            he for he in split.net.boundary_edges() if he not in split.same_half_cuts and he not in split.line_edges
        ]
        rng.shuffle(cuts)
        for he in cuts[:5]:
            result = rearrange(split, he)
            if result is not None and result.valid:
                net = approve(result)
                approved += 1
                break
    assert approved == 8
    assert sum(signed_area(net.region_polygon(r)) for r in net.regions) == 6


def _random_line(net: Net, rng: random.Random) -> CutLine | None:
    box = net.bounding_box()

    def end() -> CutPoint:
        if rng.random() < 0.25:
            return on(net, rng.choice(net.boundary_vertices()).position)
        edge = rng.choice(net.boundary_edges())
        d = edge.destination.position - edge.origin.position
        return CutPoint(edge.origin.position + d * F(rng.randint(1, 19), 20), edge)

    points = [end()]
    for _ in range(rng.choice((0, 0, 1, 2))):
        p = Vec(box.lo.x + box.width * F(rng.randint(1, 99), 100), box.lo.y + box.height * F(rng.randint(1, 99), 100))
        if not strictly_inside(net, p):
            return None
        points.append(CutPoint(p))
    points.append(end())
    for i in range(len(points) - 1):
        if not segment_valid(net, points[: i + 2], i):
            return None
    return CutLine(points)
