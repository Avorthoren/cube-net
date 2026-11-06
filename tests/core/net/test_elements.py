from cube_net.core.cube import SurfacePoint
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.net import EdgeKind, HalfEdge, NetVertex, Region


def test_half_edge_destination_and_side() -> None:
    a = NetVertex(0, Vec(0, 0), SurfacePoint(2, Vec(0, 0)))
    b = NetVertex(1, Vec(1, 0), SurfacePoint(2, Vec(1, 0)))
    region = Region(0, 2, Rigid90())
    inner = HalfEdge(0, a, EdgeKind.BOUNDARY, region)
    outer = HalfEdge(1, b, EdgeKind.BOUNDARY, None)
    inner.twin, outer.twin = outer, inner
    assert inner.destination is b and outer.destination is a
    assert outer.is_outside and not inner.is_outside


def test_identity_semantics_and_repr() -> None:
    p = SurfacePoint(2, Vec(0, 0))
    a, b = NetVertex(0, Vec(0, 0), p), NetVertex(1, Vec(0, 0), p)
    assert a != b  # two images of the same point are different vertices
    assert repr(a).startswith("NetVertex#0(Vec(0, 0), SurfacePoint(")
    assert repr(Region(3, 5, Rigid90())) == "Region#3(face 5, Rigid90(k=0, t=Vec(0, 0)))"
