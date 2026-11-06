"""Labels of the net's vertices: the point's name plus an image index, like A_1, A_2, A_3 (docs/idea.txt)."""

from dataclasses import dataclass

from cube_net.core.labels.point_labels import PointLabels
from cube_net.core.net import Net, NetVertex


@dataclass(frozen=True, slots=True)
class VertexLabel:
    # Name of the cube surface point, e.g. "A".
    name: str

    # Which image of the point this vertex is, from 1.
    index: int

    def __str__(self) -> str:
        return f"{self.name}_{self.index}"


def vertex_labels(net: Net, labels: PointLabels) -> dict[NetVertex, VertexLabel]:
    """Labels for all vertices of `net`. Images of one point are numbered by vertex id (creation order), so the numbers
    don't change while the net is only being looked at. Unregistered points are registered."""
    result: dict[NetVertex, VertexLabel] = {}
    counters: dict[str, int] = {}
    for vertex in sorted(net.vertices, key=lambda v: v.id):
        name = labels.register(vertex.point)
        counters[name] = counters.get(name, 0) + 1
        result[vertex] = VertexLabel(name, counters[name])
    return result
