import pytest

from cube_net.ui.sheet import net_style


@pytest.fixture(autouse=True)
def default_sizes() -> object:
    """The sizes are global: every test here gets the defaults back afterwards."""
    before = net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX
    yield
    net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX = before


def test_the_default_vertex_radius() -> None:
    assert net_style.VERTEX_RADIUS_PX == 8


def test_shares_of_the_vertex_radius() -> None:
    net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX = 5.0, 10.0
    assert net_style.derived_point_radius() == 5.0
    assert net_style.midpoint_radius() == 6.0


def test_never_smaller_across_than_140_percent_of_an_edge() -> None:
    net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX = 5.0, 3.0
    assert net_style.derived_point_radius() == pytest.approx(3.5)
    assert net_style.midpoint_radius() == pytest.approx(3.5)


def test_the_least_vertex_radius_is_140_percent_of_an_edge_across() -> None:
    assert net_style.least_vertex_radius(5.0) == pytest.approx(3.5)
