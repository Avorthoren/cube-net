from collections.abc import Iterable
import itertools
from typing import Self

from src.models.cube_face import CubeFace
from src.models.cube_cut import CubeCut
from src.models.cube_vertex import CubeVertex


TOTAL_FACES = 6


class Cube:
    """
    Represents the cube with all cuts.

    Features:
    DRAW CUBE NET
        VERTICES
            Each vertex should know its coordinates.
            Each vertex should know faces it touches for coloring.
        CUTS
            Each cut should know vertices it connects.
            Since we should ensure cuts do not intersect edges of the cube
            (cut line can do that, but it should be represented as two chained
            cuts, joined on the cube edge) we can deduce cut coloring from
            faces that its vertices touch: it will have colors of common faces.
            If there is only one common face - it should have color of that
            face plus white.
        FOLDS (cube's edges and their parts that weren't cut)
            Same as for CUTS.
        CUBE NET FACES (different from cube faces)
            Each cube net face should know its vertices list in a cycle order.
            Again, all those vertices will have common face (exactly one), and
            that's how we color it.
    """
    def __init__(self, colors: Iterable[str]) -> None:
        # Faces don't change
        self._faces: tuple[CubeFace, ...] = tuple(
            CubeFace(index, color)
            for index, color in zip(range(TOTAL_FACES), colors)
        )

        vertex_faces = (
            (self._faces[0], self._faces[3], self._faces[4]),  # A
            (self._faces[0], self._faces[2], self._faces[4]),  # B
            (self._faces[0], self._faces[1], self._faces[3]),  # C
            (self._faces[0], self._faces[1], self._faces[2]),  # D
            (self._faces[3], self._faces[4], self._faces[5]),  # E
            (self._faces[2], self._faces[4], self._faces[5]),  # F
            (self._faces[1], self._faces[2], self._faces[5]),  # G
            (self._faces[1], self._faces[3], self._faces[5]),  # H
        )
        # Let's generate unique index for every new vertex.
        self._next_vertex_index_gen = itertools.count()
        self._vertices: dict[int, CubeVertex] = {
            index: CubeVertex(index, faces)
            for index, faces in zip(self._next_vertex_index_gen, vertex_faces)
        }

        cut_vertices = (
            (self._vertices[0], self._vertices[1]),  # AB
            (self._vertices[0], self._vertices[2]),  # AC
            (self._vertices[0], self._vertices[4]),  # AE
            (self._vertices[1], self._vertices[3]),  # BD
            (self._vertices[1], self._vertices[5]),  # BF
            (self._vertices[4], self._vertices[7]),  # EH
            (self._vertices[5], self._vertices[6]),  # FG
        )
        # Let's generate unique index for every new cut.
        self._next_cut_index_gen = itertools.count()
        self._cuts: dict[int, CubeCut] = {
            index: CubeCut(index, *vertices)
            for index, vertices in zip(self._next_cut_index_gen, cut_vertices)
        }

        # In addition to showing cuts we want to show all edges of the cube.
        # Some of cube's edges might be divided into pieces, when cut line
        # intersects cube's edge or starts/ends there, creating cut vertex
        # on that edge.
        self._folding_edges = ...



    @classmethod
    def deserialize(cls, ...) -> Self:
        """
        Restores the cube from its serialized representation.
        """
        ...