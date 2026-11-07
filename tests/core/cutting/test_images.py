from collections.abc import Callable
from fractions import Fraction as F

from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.cutting import CutPoint, counterpart_image, endpoint_point, surface_point_at
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.net import HalfEdge, Net, default_net


def test_corner_cut_images_from_idea(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """docs/idea.txt: x_1 = (11.5, 14) on A_1-B_1 has x_2 on A_3-B_3; z on B_1-D_1 has z_3 on D_1-B_2."""
    x = counterpart_image(net, CutPoint(Vec(F(23, 2), 14), cut("B_1-A_1")))
    assert x is not None
    assert x.position == Vec(F(23, 2), 10)
    assert x.edge is cut("A_3-B_3")
    z = counterpart_image(net, CutPoint(Vec(12, F(27, 2)), cut("D_1-B_1")))
    assert z is not None
    assert z.position == Vec(F(25, 2), 13)
    assert z.point.faces == {1, 3}


def test_no_image_for_inner_points_and_vertices(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    assert counterpart_image(net, CutPoint(Vec(F(23, 2), F(27, 2)))) is None
    top = cut("B_1-A_1")
    assert counterpart_image(net, CutPoint(Vec(11, 14), top, top.destination)) is None


@given(st.data())
def test_image_is_the_same_cube_point_on_the_counterpart(data: st.DataObject) -> None:
    net = default_net()
    edge = data.draw(st.sampled_from(net.boundary_edges()))
    t = data.draw(st.fractions(0, 1, max_denominator=1000).filter(lambda t: 0 < t < 1))
    a, b = edge.origin.position, edge.destination.position
    endpoint = CutPoint(a + (b - a) * t, edge)
    image = counterpart_image(net, endpoint)
    assert image is not None
    other = image.edge
    assert other is net.counterpart(edge)
    assert on_segment(image.position, other.origin.position, other.destination.position)
    assert surface_point_at(net, image.position, other.region) == endpoint_point(net, endpoint) == image.point
