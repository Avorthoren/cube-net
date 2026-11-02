import dataclasses

from src.models.cube_vertex import CubeVertex


@dataclasses.dataclass(frozen=True)
class CubeFoldingEdge:
    """
    Represents edge that should be folded.
    It's not necessarily a full cube's edge, it might be a piece of it, because
    cut line can divide cube's edge into pieces.
    """
    index: int
    first: CubeVertex
    second: CubeVertex


def main():
    from src.models.cube_face import CubeFace

    face = CubeFace(0, "red")
    edge = CubeFoldingEdge(
        0,
        CubeVertex(10, (face,)),
        CubeVertex(11, (face,)),
    )
    edges = {0: edge}
    print(edges)


if __name__ == "__main__":
    main()
