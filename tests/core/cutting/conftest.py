from collections.abc import Callable

import pytest
from net_checks import assert_consistent

from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, default_net


@pytest.fixture
def net() -> Net:
    return default_net()


@pytest.fixture
def cut(net: Net) -> Callable[[str], HalfEdge]:
    """The cut named like in docs/idea.txt, e.g. cut("B_1-A_1") (inner half-edge, in its direction)."""
    labels = vertex_labels(net, PointLabels())
    by_name = {f"{labels[he.origin]}-{labels[he.destination]}": he for he in net.boundary_edges()}

    def find(name: str) -> HalfEdge:
        if name not in by_name:
            a, b = name.split("-")
            return by_name[f"{b}-{a}"]
        return by_name[name]

    return find


@pytest.fixture
def consistent() -> Callable[[Net], None]:
    return assert_consistent
