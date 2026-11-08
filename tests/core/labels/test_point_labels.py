from fractions import Fraction as F

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
