"""Development labels for the cut line being drawn: its points, the counterpart images of its endpoints, and the
points where it crosses cube edges.

A new cube point gets the next free name (I, J, ...). Its images are numbered after the images already in the net:
an endpoint inside a cut is image 1 and its counterpart image is image 2 (like x_1 and x_2 in docs/idea.txt).
Points at existing perimeter vertices are not listed: the net already labels them.
"""

from cube_net.core.cutting import CutLine, counterpart_image, crossings, endpoint_point, surface_point_at
from cube_net.core.geometry import Vec
from cube_net.core.labels.point_labels import PointLabels
from cube_net.core.labels.vertex_labels import VertexLabel
from cube_net.core.net import Net


def cut_line_labels(net: Net, line: CutLine, labels: PointLabels) -> list[tuple[Vec, VertexLabel]]:
    """(position, label) for every new point of `line` and every counterpart image of its endpoints."""
    result: list[tuple[Vec, VertexLabel]] = []
    used: dict[str, int] = {}

    def add(position: Vec, point_name: str, existing_images: int) -> None:
        used[point_name] = used.get(point_name, existing_images) + 1
        result.append((position, VertexLabel(point_name, used[point_name])))

    for i, cut_point in enumerate(line.points):
        if cut_point.vertex is None:
            point = endpoint_point(net, cut_point)
            name = labels.register(point)
            existing = len(net.images(point))
            add(cut_point.position, name, existing)
            image = counterpart_image(net, cut_point)
            if image is not None:
                add(image.position, name, existing)
        if i + 1 < len(line.points):  # crossings with cube edges on the way to the next point
            for crossing in crossings(net, [cut_point.position, line.points[i + 1].position]):
                point = surface_point_at(net, crossing)
                add(crossing, labels.register(point), len(net.images(point)))
    return result
