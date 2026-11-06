import itertools

import pytest

from cube_net.ui.sheet.dashing import dash_pieces


def test_whole_edge_has_twenty_alternating_dashes() -> None:
    pieces = dash_pieces(1.0, 0.0, 0.05)
    assert len(pieces) == 20
    assert [p for _, _, p in pieces] == [0, 1] * 10
    assert pieces[0][:2] == pytest.approx((0, 0.05))
    assert pieces[-1][1] == pytest.approx(1.0)


def test_offset_continues_pattern() -> None:
    pieces = dash_pieces(0.12, 0.5, 0.05)  # pattern position 0.5 = start of dash #10 (even)
    assert [p for _, _, p in pieces] == [0, 1, 0]
    assert pieces[-1] == pytest.approx((0.1, 0.12, 0))


def test_offset_in_the_middle_of_a_dash() -> None:
    pieces = dash_pieces(0.1, 0.07, 0.05)  # starts inside dash #1 (odd), 0.03 left of it
    assert pieces[0] == pytest.approx((0, 0.03, 1))
    assert pieces[1] == pytest.approx((0.03, 0.08, 0))


def test_degenerate() -> None:
    assert dash_pieces(0, 0, 0.05) == []
    assert dash_pieces(1, 0, 0) == []


def test_pieces_cover_the_line_without_gaps() -> None:
    pieces = dash_pieces(0.987, 0.0333, 0.05)
    assert pieces[0][0] == 0 and pieces[-1][1] == pytest.approx(0.987)
    assert all(a[1] == pytest.approx(b[0]) for a, b in itertools.pairwise(pieces))
