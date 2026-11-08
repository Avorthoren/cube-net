"""`Editor`: the state machine of the main feature (docs/idea.txt; docs/plan.md, section 5.1). No Qt.

DEFAULT       click on a cut or a vertex    -> the cut line starts there              -> CUTTING
CUTTING       click inside the net          -> a new point (if the segment is valid), on the fold line if clicked on one
              click on a cut or a vertex    -> the last point (if the segment is valid) -> CUT_EDITING
CUT_EDITING   click a segment's middle      -> a new point there
              delete an inner point         -> (if the shortcut segment is valid)
              move a point                  -> (if its segments stay valid; endpoints walk along the perimeter;
                                                 inner points snap to fold lines and may not go near the perimeter)
              click a cut                   -> the half with its counterpart moves onto it -> CUT_APPROVING
                                               (rejected if the counterpart is in the same half)
CUT_APPROVING (overlap check and approval: next steps of M6)

The UI decides where a click lands: on a perimeter vertex (inside its circle), on a cut (inside its hitbox), on a fold
line (inside its hitbox), or elsewhere; in that order of priority. A rejected click
returns a `Rejection` with the segments to flash black.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cube_net.core.cutting import (
    MAX_POINTS_AFTER_FIRST,
    CutLine,
    CutPoint,
    Rearranged,
    SplitNet,
    invalid_segments,
    project_onto,
    rearrange,
    segment_allowed,
    segment_valid,
    split_net,
)
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net, NetVertex, boundary_edge_from


class EditorState(Enum):
    DEFAULT = "default"
    CUTTING = "cutting"
    CUT_EDITING = "cut_editing"
    CUT_APPROVING = "cut_approving"


@dataclass(frozen=True, slots=True)
class Rejection:
    # The segments that break the rules (to be shown in black for a moment).
    segments: tuple[tuple[Vec, Vec], ...]

    # The line to show meanwhile, if it differs from the current one (deleting a point: without that point).
    preview: tuple[CutPoint, ...] | None = None

    @property
    def segment(self) -> tuple[Vec, Vec]:
        return self.segments[0]


class Editor:
    def __init__(self, net: Net) -> None:
        self.net = net
        self.cut_line: CutLine | None = None
        self.rearranged: Rearranged | None = None
        self._split: tuple[tuple[CutPoint, ...], SplitNet] | None = None

    @property
    def state(self) -> EditorState:
        if self.rearranged is not None:
            return EditorState.CUT_APPROVING
        if self.cut_line is None:
            return EditorState.DEFAULT
        return EditorState.CUT_EDITING if self.cut_line.closed else EditorState.CUTTING

    @property
    def display_net(self) -> Net:
        """The net to show: the rearranged one in CUT_APPROVING, otherwise the current one."""
        return self.rearranged.net if self.rearranged is not None else self.net

    def candidate(
        self, p: Vec, cut: HalfEdge | None, vertex: NetVertex | None = None, fold: HalfEdge | None = None
    ) -> CutPoint:
        """The point a click at `p` would create: exactly at `vertex`, on `cut` or `fold` (the closest point of it), or
        at `p` inside the net."""
        if cut is not None and vertex is None:
            projected = project_onto(cut, p)
            for end in (cut.origin, cut.destination):
                if projected == end.position:  # landed exactly on the end of the cut: that's the vertex
                    vertex = end
            if vertex is None:
                return CutPoint(projected, cut)
        if vertex is not None:
            return CutPoint(vertex.position, boundary_edge_from(self.net, vertex), vertex)
        if fold is not None:
            return CutPoint(project_onto(fold, p), fold=fold)
        return CutPoint(p)

    def click(
        self, p: Vec, cut: HalfEdge | None, vertex: NetVertex | None = None, fold: HalfEdge | None = None
    ) -> Rejection | None:
        """A left click at sheet point `p`; `vertex`, `cut` and `fold` are what the click hit, if anything.

        Returns a `Rejection` if the click would break the rules; None if it was accepted or means nothing here.
        """
        on_perimeter = vertex is not None or cut is not None
        match self.state:
            case EditorState.DEFAULT:
                if on_perimeter:
                    self.cut_line = CutLine([self.candidate(p, cut, vertex)])
                return None
            case EditorState.CUTTING:
                return self._extend(self.candidate(p, cut, vertex, fold))
            case _:
                return None

    # --- CUT_EDITING ------------------------------------------------------------------------------------------------

    def insert_midpoint(self, i: int) -> Rejection | None:
        """A new point in the middle of segment i (always valid geometrically; limited to 50 points after the first)."""
        line = self._editing_line()
        a, b = line.points[i].position, line.points[i + 1].position
        if line.inner_count >= MAX_POINTS_AFTER_FIRST:
            return Rejection(((a, b),))
        line.points.insert(i + 1, CutPoint((a + b) / 2))
        return None

    def delete_point(self, i: int) -> Rejection | None:
        """Delete point i (not the first or the last). Rejected if the segment that replaces its two segments would
        break the rules; the rejection then previews the line without the point, with that segment black."""
        line = self._editing_line()
        if not 0 < i < len(line.points) - 1:
            raise ValueError(f"only inner points can be deleted, not point {i} of {len(line.points)}")
        remaining = [p for j, p in enumerate(line.points) if j != i]
        if not segment_valid(self.net, remaining, i - 1):
            return Rejection(((remaining[i - 1].position, remaining[i].position),), tuple(remaining))
        line.points[:] = remaining
        return None

    def drag_target(
        self,
        i: int,
        p: Vec,
        vertex: NetVertex | None = None,
        fold: HalfEdge | None = None,
        current: CutPoint | None = None,
    ) -> CutPoint:
        """Where point i goes when dragged to `p`; `current` is where the drag has brought it so far.

        An inner point goes to `p`, or onto `fold` if the mouse is in that fold's hitbox. An endpoint goes to the
        perimeter `vertex` if the mouse is in its circle; otherwise it walks along the perimeter from `current` towards
        `p`, passing vertices on the way, and stops where it gets no closer.
        """
        line = self._editing_line()
        if line.points[i].edge is None:
            return CutPoint(project_onto(fold, p), fold=fold) if fold is not None else CutPoint(p)
        if vertex is not None:
            return CutPoint(vertex.position, boundary_edge_from(self.net, vertex), vertex)
        point = current if current is not None else line.points[i]
        while True:
            target = self._closest_on_adjacent_cuts(point, p)
            if target.vertex is None or target.vertex is point.vertex:
                return target
            point = target  # reached the end of the cut: go on along the next one, if that gets closer

    def _closest_on_adjacent_cuts(self, point: CutPoint, p: Vec) -> CutPoint:
        """The point closest to `p` on the point's cut (on either cut, if the point is at a vertex)."""
        assert point.edge is not None
        cuts = [point.edge]
        if point.vertex is not None:
            cuts += [he for he in self.net.boundary_edges() if point.vertex in (he.origin, he.destination)]
        best = min(cuts, key=lambda cut: ((project_onto(cut, p) - p).length_squared(), cut.id))
        projected = project_onto(best, p)
        vertex = next((end for end in (best.origin, best.destination) if end.position == projected), None)
        return CutPoint(projected, best, vertex)

    def move_point(self, i: int, target: CutPoint, over_perimeter: bool = False) -> Rejection | None:
        """Put point i at `target` (from `drag_target`). Rejected, and nothing changes, if its segments break the
        rules; the rejection names those segments at the new position. `over_perimeter`: the mouse is in a hitbox of
        the perimeter, where an inner point may never be released (only the line's ends belong on the perimeter)."""
        line = self._editing_line()
        moved = [*line.points[:i], target, *line.points[i + 1 :]]
        inner_over_perimeter = over_perimeter and not line.points[i].on_perimeter
        bad = [i - 1, i] if inner_over_perimeter else invalid_segments(self.net, moved, (i - 1, i))
        if bad:
            return Rejection(tuple((moved[j].position, moved[j + 1].position) for j in bad))
        line.points[:] = moved
        return None

    def split(self) -> SplitNet:
        """The net as it would be with the closed cut line turned into cuts (computed when the line has changed)."""
        line = self._editing_line()
        points = tuple(line.points)
        if self._split is None or self._split[0] != points:
            self._split = (points, split_net(self.net, line))
        return self._split[1]

    def glue(self, clicked: HalfEdge) -> Rejection | None:
        """The user chose the cut `clicked` of `split().net`: rearrange the halves so that it's glued with its
        counterpart. Rejected if the counterpart is in the same half. Cuts of the new line itself mean nothing."""
        split = self.split()
        if clicked in split.line_edges:
            return None
        rearranged = rearrange(split, clicked)
        if rearranged is None:
            return Rejection(((clicked.origin.position, clicked.destination.position),))
        self.rearranged = rearranged
        return None

    def cancel_rearrangement(self) -> None:
        """Back from CUT_APPROVING to CUT_EDITING."""
        self.rearranged = None

    # --- internals --------------------------------------------------------------------------------------------------

    def _editing_line(self) -> CutLine:
        if self.state is not EditorState.CUT_EDITING or self.cut_line is None:
            raise RuntimeError(f"the cut line can only be edited in CUT_EDITING, not in {self.state.name}")
        return self.cut_line

    def _extend(self, point: CutPoint) -> Rejection | None:
        line = self.cut_line
        assert line is not None
        too_many = line.inner_count >= MAX_POINTS_AFTER_FIRST and not point.on_perimeter
        if too_many or not segment_allowed(self.net, line, point):
            return Rejection(((line.last.position, point.position),))
        line.points.append(point)
        return None
