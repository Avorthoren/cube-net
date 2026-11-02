import dataclasses


@dataclasses.dataclass(frozen=True)
class CubeFace:
    """
    Represents real cube's face.
    Face is defined by its index, which can be used for serialization.
    """
    index: int
    color: str
