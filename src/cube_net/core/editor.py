"""`Editor`: the state machine of the main feature (docs/idea.txt; docs/plan.md, section 5.1). No Qt.

DEFAULT       click on a cut or a vertex    -> the cut line starts there              -> CUTTING
CUTTING       click inside the net          -> a new point (if the segment is valid)
              click on a cut or a vertex    -> the last point (if the segment is valid) -> CUT_EDITING
CUT_EDITING   (editing the line, choosing the segment to glue: next steps of M5 / M6)

The UI decides where a click lands: on a perimeter vertex (inside its circle), on a cut (inside its hitbox), or
elsewhere; a vertex wins over a cut. A rejected click
returns a `Rejection` with the segment to flash black.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cube_net.core.cutting import MAX_POINTS_AFTER_FIRST, CutLine, CutPoint, project_onto, segment_allowed
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net, NetVertex, boundary_edge_from


class EditorState(Enum):
    DEFAULT = "default"
    CUTTING = "cutting"
    CUT_EDITING = "cut_editing"
    CUT_APPROVING = "cut_approving"


@dataclass(frozen=True, slots=True)
class Rejection:
    # The segment that breaks the rules (to be shown in black for a moment).
    segment: tuple[Vec, Vec]


class Editor:
    def __init__(self, net: Net) -> None:
        self.net = net
        self.cut_line: CutLine | None = None

    @property
    def state(self) -> EditorState:
        if self.cut_line is None:
            return EditorState.DEFAULT
        return EditorState.CUT_EDITING if self.cut_line.closed else EditorState.CUTTING

    def candidate(self, p: Vec, cut: HalfEdge | None, vertex: NetVertex | None = None) -> CutPoint:
        """The point a click at `p` would create: exactly at `vertex`, on `cut` (projected onto it), or inside the
        net."""
        if vertex is not None:
            return CutPoint(vertex.position, boundary_edge_from(self.net, vertex), vertex)
        return CutPoint(project_onto(cut, p), cut) if cut is not None else CutPoint(p)

    def click(self, p: Vec, cut: HalfEdge | None, vertex: NetVertex | None = None) -> Rejection | None:
        """A left click at sheet point `p`; `vertex` is the perimeter vertex whose circle contains `p`, `cut` the cut
        whose hitbox contains `p` (if any).

        Returns a `Rejection` if the click would break the rules; None if it was accepted or means nothing here.
        """
        on_perimeter = vertex is not None or cut is not None
        match self.state:
            case EditorState.DEFAULT:
                if on_perimeter:
                    self.cut_line = CutLine([self.candidate(p, cut, vertex)])
                return None
            case EditorState.CUTTING:
                return self._extend(self.candidate(p, cut, vertex))
            case _:
                return None

    def _extend(self, point: CutPoint) -> Rejection | None:
        line = self.cut_line
        assert line is not None
        too_many = line.inner_count >= MAX_POINTS_AFTER_FIRST and not point.on_perimeter
        if too_many or not segment_allowed(self.net, line, point):
            return Rejection((line.last.position, point.position))
        line.points.append(point)
        return None
