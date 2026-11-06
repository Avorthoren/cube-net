from fractions import Fraction as F

import pytest
from PyQt6.QtCore import QPointF

from cube_net.core.geometry import Rigid90, Vec
from cube_net.ui.qt_geometry import to_qpointf, to_qtransform


def test_to_qpointf() -> None:
    assert to_qpointf(Vec(F(1, 4), -3)) == QPointF(0.25, -3.0)


@pytest.mark.parametrize("k", range(4))
def test_transform_matches_rigid90(k: int) -> None:
    m = Rigid90(k, Vec(F(3, 2), -2))
    t = to_qtransform(m)
    for p in (Vec(0, 0), Vec(1, 0), Vec(F(1, 3), F(7, 10))):
        mapped = t.map(to_qpointf(p))
        expected = to_qpointf(m.apply(p))
        assert (mapped.x(), mapped.y()) == pytest.approx((expected.x(), expected.y()))
