"""Counterpart images of the cut line's endpoints (docs/idea.txt: the z_3 case).

An endpoint that lies inside a cut X-Y is a cube point that also lies on the cut's counterpart (the other image of
X-Y). That other image has to show it right away, not only when gluing: otherwise, in CUT_EDITING, the user couldn't
click the part of the counterpart they want to glue.

The net itself is not changed while the line is being drawn; the images are computed from the line. The net is split
for real when a segment is chosen for gluing (M6).
"""

from dataclasses import dataclass

from cube_net.core.cube import SurfacePoint
from cube_net.core.cutting.cut_line import CutPoint
from cube_net.core.cutting.pieces import surface_point_at
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net


@dataclass(frozen=True, slots=True)
class CounterpartImage:
    # The counterpart cut the image lies on.
    edge: HalfEdge

    # The image's position on the sheet.
    position: Vec

    # The cube point (the same as the endpoint's).
    point: SurfacePoint


def endpoint_point(net: Net, endpoint: CutPoint) -> SurfacePoint:
    """The cube point of a cut line point (an endpoint is taken from the region of its cut)."""
    region = endpoint.edge.region if endpoint.edge is not None else None
    return surface_point_at(net, endpoint.position, region)


def counterpart_image(net: Net, endpoint: CutPoint) -> CounterpartImage | None:
    """Where the endpoint's cube point appears on the counterpart of its cut; None for points inside the net and for
    endpoints at perimeter vertices (all images of a vertex already exist)."""
    edge = endpoint.edge
    if edge is None or endpoint.vertex is not None:
        return None
    a, b = edge.origin.position, edge.destination.position
    d = b - a
    t = (endpoint.position - a).dot(d) / d.length_squared()
    other = net.counterpart(edge)  # runs the other way: from the image of b to the image of a
    c, e = other.origin.position, other.destination.position
    return CounterpartImage(other, c + (e - c) * (1 - t), endpoint_point(net, endpoint))
