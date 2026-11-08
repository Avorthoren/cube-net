from fractions import Fraction as F

import pytest

from cube_net.core.cube import VERTICES, SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels


def test_cube_vertices_are_a_to_h() -> None:
    labels = PointLabels()
    assert [labels.name(SurfacePoint.at_vertex(v)) for v in VERTICES] == list("ABCDEFGH")


def test_new_points_continue_from_i_and_are_stable() -> None:
    labels = PointLabels()
    x = SurfacePoint(1, Vec(F(1, 2), 1))
    y = SurfacePoint(1, Vec(F(1, 2), F(1, 2)))
    assert labels.name(x) is None
    assert labels.register(x) == "I"
    assert labels.register(y) == "J"
    assert labels.register(x) == "I"  # same point (even if created from another face): same name
    assert labels.register(SurfacePoint(5, Vec(F(1, 2), 0))) == "I"
    assert labels.register(SurfacePoint.at_vertex("C")) == "C"


def test_upcoming_names_do_not_register_anything() -> None:
    labels = PointLabels()
    assert [labels.upcoming(i) for i in range(3)] == ["I", "J", "K"]
    x = SurfacePoint(1, Vec(F(1, 2), 1))
    assert labels.name(x) is None
    assert labels.upcoming() == "I"
    assert labels.register(x) == "I"
    assert labels.upcoming() == "J"


class TestSavedAndRestored:
    def point(self, x: int) -> SurfacePoint:
        return SurfacePoint(1, Vec(F(x, 10), F(1, 2)))

    def test_new_ones_have_nothing_to_save(self) -> None:
        assert PointLabels().saved() == ({}, 8)

    def test_round_trip(self) -> None:
        labels = PointLabels()
        i, j = labels.register(self.point(1)), labels.register(self.point(2))
        restored = PointLabels.restored(*labels.saved())
        assert (restored.name(self.point(1)), restored.name(self.point(2))) == (i, j)
        assert restored.upcoming() == labels.upcoming()
        assert restored.name(SurfacePoint.at_vertex("A")) == "A"

    def test_names_are_not_reused(self) -> None:
        labels = PointLabels()
        i = labels.register(self.point(1))
        assert PointLabels.restored(*labels.saved()).register(self.point(2)) != i

    def test_a_gap_in_the_names_stays(self) -> None:
        restored = PointLabels.restored({self.point(1): "K"}, 11)
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
            PointLabels.restored({self.point(x): name for x, name in names.items()}, next_index)
