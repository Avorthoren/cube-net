import dataclasses

from src.models.cube_vertex import CubeVertex


@dataclasses.dataclass(frozen=True)
class CubeCut:
    """
    Represents a segment between two vertices of a cut on cube's surface.
    Should NOT intersect edges of the cube, but may start/end on them.
    I.e. there should be no two points of the cut such that they are strictly
    inside different cube faces.
    """
    index: int
    first: CubeVertex
    second: CubeVertex
