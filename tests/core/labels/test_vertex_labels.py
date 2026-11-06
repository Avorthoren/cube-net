from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, VertexLabel, vertex_labels
from cube_net.core.net import default_net

# docs/idea.txt
EXPECTED = {
    "A_1": Vec(11, 14), "A_2": Vec(10, 13), "A_3": Vec(11, 10),
    "B_1": Vec(12, 14), "B_2": Vec(13, 13), "B_3": Vec(12, 10),
    "C_1": Vec(11, 13), "D_1": Vec(12, 13),
    "E_1": Vec(11, 11), "E_2": Vec(10, 12),
    "F_1": Vec(12, 11), "F_2": Vec(13, 12),
    "G_1": Vec(12, 12), "H_1": Vec(11, 12),
}  # fmt: skip


def test_default_net_labels_match_idea() -> None:
    labels = vertex_labels(default_net(), PointLabels())
    assert {str(label): vertex.position for vertex, label in labels.items()} == EXPECTED


def test_label_str() -> None:
    assert str(VertexLabel("AB", 3)) == "AB_3"


def test_numbering_is_stable() -> None:
    net, names = default_net(), PointLabels()
    assert vertex_labels(net, names) == vertex_labels(net, names)
