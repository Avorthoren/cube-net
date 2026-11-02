import dataclasses
from src.models.cube_face import CubeFace


@dataclasses.dataclass(frozen=True)
class CubeVertex:
    """
    Represents "real" vertex of the cut on cube's surface.
    CubeVertex is defined by its index, which can be used for serialization.
    """
    index: int
    faces: tuple[CubeFace, ...]  # 1, 2 or 3 faces.
