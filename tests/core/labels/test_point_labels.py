# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.body import CUBE, VERTICES, Body, SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels


def test_cube_vertices_are_a_to_h() -> None:
    labels = PointLabels(CUBE)
    assert [labels.name(SurfacePoint.at_vertex(CUBE, v)) for v in VERTICES] == list("ABCDEFGH")


def test_new_points_continue_from_i_and_are_stable() -> None:
    labels = PointLabels(CUBE)
    x = SurfacePoint(CUBE, 1, Vec(F(1, 2), 1))
    y = SurfacePoint(CUBE, 1, Vec(F(1, 2), F(1, 2)))
    assert labels.name(x) is None
    assert labels.register(x) == "I"
    assert labels.register(y) == "J"
    assert labels.register(x) == "I"  # same point (even if created from another face): same name
    assert labels.register(SurfacePoint(CUBE, 5, Vec(F(1, 2), 0))) == "I"
    assert labels.register(SurfacePoint.at_vertex(CUBE, "C")) == "C"


def test_upcoming_names_do_not_register_anything() -> None:
    labels = PointLabels(CUBE)
    assert [labels.upcoming(i) for i in range(3)] == ["I", "J", "K"]
    x = SurfacePoint(CUBE, 1, Vec(F(1, 2), 1))
    assert labels.name(x) is None
    assert labels.upcoming() == "I"
    assert labels.register(x) == "I"
    assert labels.upcoming() == "J"


class TestSavedAndRestored:
    def point(self, x: int) -> SurfacePoint:
        return SurfacePoint(CUBE, 1, Vec(F(x, 10), F(1, 2)))

    def test_new_ones_have_nothing_to_save(self) -> None:
        assert PointLabels(CUBE).saved() == ({}, 8)

    def test_round_trip(self) -> None:
        labels = PointLabels(CUBE)
        i, j = labels.register(self.point(1)), labels.register(self.point(2))
        restored = PointLabels.restored(CUBE, *labels.saved())
        assert (restored.name(self.point(1)), restored.name(self.point(2))) == (i, j)
        assert restored.upcoming() == labels.upcoming()
        assert restored.name(SurfacePoint.at_vertex(CUBE, "A")) == "A"

    def test_names_are_not_reused(self) -> None:
        labels = PointLabels(CUBE)
        i = labels.register(self.point(1))
        assert PointLabels.restored(CUBE, *labels.saved()).register(self.point(2)) != i

    def test_a_gap_in_the_names_stays(self) -> None:
        restored = PointLabels.restored(CUBE, {self.point(1): "K"}, 11)
        assert restored.upcoming() == "L"

    @pytest.mark.parametrize(
        ("names", "next_index"),
        [
            pytest.param({1: "I", 2: "I"}, 10, id="the same name twice"),
            pytest.param({1: "A"}, 9, id="the name of a cube vertex"),
            pytest.param({1: "I"}, 8, id="the next one is taken already"),
        ],
    )
    def test_nonsense(self, names: dict[int, str], next_index: int) -> None:
        with pytest.raises(ValueError):
            PointLabels.restored(CUBE, {self.point(x): name for x, name in names.items()}, next_index)


def test_another_bodys_names_and_the_first_free_name_after_them(pillow: Body) -> None:
    labels = PointLabels(pillow)
    assert labels.name(SurfacePoint.at_vertex(pillow, "Q")) == "Q"
    assert [labels.upcoming(i) for i in range(4)] == ["A", "B", "C", "D"]
    for x in range(1, 17):  # 16 points of face 1's bottom: A..O, skipping P, and then T
        labels.register(SurfacePoint(pillow, 1, Vec(F(x, 20), F(1, 2))))
    assert labels.register(SurfacePoint(pillow, 1, Vec(F(1, 2), F(1, 3)))) == "U"
    assert labels.upcoming() == "V"
