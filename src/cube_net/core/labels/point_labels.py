"""`PointLabels`: stable letter names for points of the cube surface (debug labels, docs/idea.txt).

The 8 cube vertices are named A..H as in docs/idea.txt. Every other point (created by cuts) gets the next free
spreadsheet-style name when it is registered: I, J, ..., Z, AA, AB, ... Names are never reused.
"""

from cube_net.core.cube import VERTICES, SurfacePoint
from cube_net.core.labels.excel import excel_label


class PointLabels:
    def __init__(self) -> None:
        self._names: dict[SurfacePoint, str] = {SurfacePoint.at_vertex(v): v for v in VERTICES}
        self._next = len(VERTICES)
        if [excel_label(i) for i in range(self._next)] != list(VERTICES):
            raise RuntimeError(f"cube vertex labels {VERTICES} must be the first spreadsheet names A, B, ...")

    def register(self, point: SurfacePoint) -> str:
        """The name of `point`, assigning the next free one if it has none yet."""
        name = self._names.get(point)
        if name is None:
            name = self._names[point] = excel_label(self._next)
            self._next += 1
        return name

    def name(self, point: SurfacePoint) -> str | None:
        """The name of `point`, or None if it was never registered."""
        return self._names.get(point)
