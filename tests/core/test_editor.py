from collections.abc import Callable
from fractions import Fraction as F

import pytest

from cube_net.core.cutting import MAX_POINTS_AFTER_FIRST, CutLine, CutPoint
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, NetVertex, boundary_vertex_at, default_net


@pytest.fixture
def net() -> Net:
    return default_net()


@pytest.fixture
def cut(net: Net) -> Callable[[str], HalfEdge]:
    labels = vertex_labels(net, PointLabels())
    by_name = {f"{labels[he.origin]}-{labels[he.destination]}": he for he in net.boundary_edges()}
    return lambda name: by_name[name]


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def positions(editor: Editor) -> list[Vec]:
    assert editor.cut_line is not None
    return [p.position for p in editor.cut_line.points]


def test_corner_cut_from_idea(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """docs/idea.txt: x on A_1-B_1, y inside face 1, z on B_1-D_1."""
    editor = Editor(net)
    assert editor.state is EditorState.DEFAULT
    assert editor.click(v("11.5", "13.99"), cut("B_1-A_1")) is None  # projected onto the cut
    assert editor.state is EditorState.CUTTING
    assert editor.click(v("11.5", "13.5"), None) is None
    assert editor.click(v("11.99", "13.5"), cut("D_1-B_1")) is None
    assert editor.state is EditorState.CUT_EDITING
    assert positions(editor) == [v("11.5", "14"), v("11.5", "13.5"), v("12", "13.5")]


def test_click_off_any_cut_in_default_does_nothing(net: Net) -> None:
    editor = Editor(net)
    assert editor.click(v("11.5", "12.5"), None) is None
    assert editor.state is EditorState.DEFAULT and editor.cut_line is None


def test_rejection_keeps_the_line_and_reports_the_segment(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    rejection = editor.click(v("12.5", "13.5"), None)  # outside the net
    assert rejection is not None
    assert rejection.segment == (v("11.5", "14"), v("12.5", "13.5"))
    assert positions(editor) == [v("11.5", "14")]


def test_two_images_of_the_same_point_may_be_the_ends(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """From A_1 down through faces 1, 2, 6, 5 to A_3 (allowed, even though nothing can be glued afterwards)."""
    editor = Editor(net)
    editor.click(v("11", "14"), cut("B_1-A_1"))
    for y in ("13.5", "12.5", "11.5", "10.5"):
        assert editor.click(v("11.5", y), None) is None
    assert editor.click(v("11", "10"), cut("A_3-B_3")) is None
    assert editor.state is EditorState.CUT_EDITING


def test_at_most_50_points_after_the_first(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("10", "12.01"), cut("A_2-E_2"))
    for i in range(MAX_POINTS_AFTER_FIRST):  # a zigzag inside face 4
        x = F(1001, 100) + F(i, 100) * F(97, 100)
        y = F(1202, 100) if i % 2 else F(1298, 100)
        assert editor.click(Vec(x, y), None) is None, i
    assert editor.click(v("10.9", "12.5"), None) is not None  # a 51st point after the first
    assert editor.click(v("10.9", "13"), cut("C_1-A_2")) is None  # but it may still end
    assert editor.state is EditorState.CUT_EDITING


def test_clicks_after_the_line_is_closed_are_ignored_for_now(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    editor.click(v("11.5", "13.5"), None)
    editor.click(v("12", "13.5"), cut("D_1-B_1"))
    assert editor.click(v("11.7", "13.7"), None) is None
    assert len(positions(editor)) == 3


def test_candidate(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    assert editor.candidate(v("11.5", "13.9"), cut("B_1-A_1")).position == v("11.5", "14")
    assert editor.candidate(v("11.5", "13.9"), None).position == v("11.5", "13.9")


def vertex_at(net: Net, x: int, y: int) -> NetVertex:
    found = boundary_vertex_at(net, Vec(x, y), F(1, 100))
    assert found is not None
    return found


def test_start_and_end_at_perimeter_vertices(net: Net) -> None:
    """From the reflex corner C_1 across face 2 to G_1 (docs/idea.txt: cuts may start / end at vertices)."""
    editor = Editor(net)
    c1, g1 = vertex_at(net, 11, 13), vertex_at(net, 12, 12)
    assert editor.click(v("11.02", "12.98"), None, c1) is None  # anywhere in the circle: exactly the vertex
    assert editor.cut_line is not None and editor.cut_line.points[0].vertex is c1
    assert editor.click(v("11.5", "12.5"), None) is None
    assert editor.click(v("11.99", "12.01"), None, g1) is None
    assert editor.state is EditorState.CUT_EDITING
    assert positions(editor) == [Vec(11, 13), v("11.5", "12.5"), Vec(12, 12)]


def test_vertex_wins_over_the_cut(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("11.02", "13.98"), cut("B_1-A_1"), vertex_at(net, 11, 14))
    assert positions(editor) == [Vec(11, 14)]


def test_vertex_segment_must_go_into_the_net(net: Net) -> None:
    editor = Editor(net)
    editor.click(v("11", "13"), None, vertex_at(net, 11, 13))  # C_1: the empty quadrant is up-left
    assert editor.click(v("10.5", "13.5"), None) is not None  # outside the net
    assert editor.click(v("10.5", "12.5"), None) is None  # into face 4


def test_ending_at_the_starting_vertex_is_rejected(net: Net) -> None:
    editor = Editor(net)
    c1 = vertex_at(net, 11, 13)
    editor.click(v("11", "13"), None, c1)
    editor.click(v("11.5", "12.5"), None)
    assert editor.click(v("11", "13"), None, c1) is not None


def test_projection_onto_the_end_of_a_cut_is_that_vertex(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("10.8", "13.99"), cut("B_1-A_1"))  # beyond A_1: projected onto the end of the cut
    assert editor.cut_line is not None
    start = editor.cut_line.points[0]
    assert start.position == Vec(11, 14)
    assert start.vertex is not None and start.vertex.position == Vec(11, 14)


@pytest.fixture
def editing(net: Net, cut: Callable[[str], HalfEdge]) -> Editor:
    """The corner cut of docs/idea.txt, closed: x (11.5, 14), y (11.5, 13.5), z (12, 13.5)."""
    editor = Editor(net)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    editor.click(v("11.5", "13.5"), None)
    editor.click(v("12", "13.5"), cut("D_1-B_1"))
    return editor


def test_insert_midpoint(editing: Editor) -> None:
    assert editing.insert_midpoint(0) is None
    assert positions(editing) == [v("11.5", "14"), v("11.5", "13.75"), v("11.5", "13.5"), v("12", "13.5")]
    assert editing.state is EditorState.CUT_EDITING


def test_insert_midpoint_respects_the_limit(editing: Editor) -> None:
    for _ in range(MAX_POINTS_AFTER_FIRST - 2):
        assert editing.insert_midpoint(0) is None
    assert editing.insert_midpoint(0) is not None
    assert len(positions(editing)) == MAX_POINTS_AFTER_FIRST + 1


def test_delete_inner_point(editing: Editor) -> None:
    assert editing.delete_point(1) is None  # x-z is a valid shortcut inside face 1
    assert positions(editing) == [v("11.5", "14"), v("12", "13.5")]


@pytest.mark.parametrize("i", [0, 2])
def test_ends_cannot_be_deleted(editing: Editor, i: int) -> None:
    with pytest.raises(ValueError, match="only inner points"):
        editing.delete_point(i)


def test_rejected_delete_previews_the_line_without_the_point(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """A line bent around the reflex corner C_1: without its second point it would leave the net."""
    editor = Editor(net)
    editor.click(v("10.5", "13"), cut("C_1-A_2"))
    editor.click(v("11.2", "12.8"), None)
    editor.click(v("11.5", "13.5"), None)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    before = positions(editor)
    rejection = editor.delete_point(1)
    assert rejection is not None
    assert rejection.segments == ((v("10.5", "13"), v("11.5", "13.5")),)
    assert rejection.preview is not None
    assert [p.position for p in rejection.preview] == [before[0], before[2], before[3]]
    assert positions(editor) == before  # nothing changed


def test_move_inner_point(editing: Editor) -> None:
    assert editing.move_point(1, editing.drag_target(1, v("11.3", "13.3"))) is None
    assert positions(editing)[1] == v("11.3", "13.3")


def test_rejected_move_changes_nothing_and_names_the_bad_segments(editing: Editor) -> None:
    before = positions(editing)
    rejection = editing.move_point(1, editing.drag_target(1, v("10.5", "13.5")))  # the empty corner
    assert rejection is not None
    target = v("10.5", "13.5")
    assert rejection.segments == ((before[0], target), (target, before[2]))
    assert positions(editing) == before


def test_endpoint_slides_along_its_cut_and_stops_at_its_end(editing: Editor) -> None:
    assert editing.drag_target(0, v("11.8", "14.3")).position == v("11.8", "14")  # projected onto the cut
    at_end = editing.drag_target(0, v("15", "14"))  # far beyond B_1
    assert at_end.position == Vec(12, 14)
    assert at_end.vertex is not None and at_end.vertex.position == Vec(12, 14)
    far_below = editing.drag_target(0, v("11.8", "5"))  # it never leaves its cut
    assert far_below.position == v("11.8", "14")


def test_endpoint_at_a_vertex_may_slide_along_either_cut(net: Net) -> None:
    editor = Editor(net)
    editor.click(Vec(11, 13), None, vertex_at(net, 11, 13))  # C_1: cuts C_1-A_1 and C_1-A_2 meet here
    editor.click(v("11.5", "12.5"), None)
    editor.click(Vec(12, 12), None, vertex_at(net, 12, 12))
    assert editor.drag_target(0, v("10.5", "13.1")).position == v("10.5", "13")
    assert editor.drag_target(0, v("11.1", "13.5")).position == v("11", "13.5")


def test_moving_an_endpoint_validates_its_segment(editing: Editor) -> None:
    assert editing.move_point(2, editing.drag_target(2, Vec(12, 14))) is None  # z up to the end of its cut: B_1
    before = positions(editing)
    assert before[2] == Vec(12, 14)
    rejection = editing.move_point(0, editing.drag_target(0, Vec(12, 14)))  # x to B_1 too: both ends at one point
    assert rejection is not None
    assert positions(editing) == before


def test_editing_only_in_cut_editing(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    with pytest.raises(RuntimeError, match="only be edited in CUT_EDITING"):
        editor.insert_midpoint(0)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    with pytest.raises(RuntimeError, match="only be edited in CUT_EDITING"):
        editor.drag_target(0, v("11.8", "14"))


def fold_named(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.fold_edges() if {he.origin.position, he.destination.position} == {a, b})


class TestFolds:
    def test_click_on_a_fold_puts_the_point_exactly_on_it(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        fold = fold_named(net, Vec(11, 13), Vec(12, 13))
        assert editor.click(v("11.3", "13.02"), None, None, fold) is None
        assert editor.cut_line is not None
        point = editor.cut_line.points[1]
        assert point.position == v("11.3", "13")
        assert point.fold is fold and not point.on_perimeter

    def test_dragging_an_inner_point_onto_a_fold(self, editing: Editor) -> None:
        fold = fold_named(editing.net, Vec(11, 13), Vec(12, 13))
        target = editing.drag_target(1, v("11.3", "13.03"), fold=fold)
        assert target.position == v("11.3", "13") and target.fold is fold
        assert editing.move_point(1, target) is None
        assert editing.drag_target(1, v("11.3", "13.3")).fold is None  # out of the hitbox: free again

    def test_end_of_a_fold_is_on_the_perimeter_so_rejected(self, editing: Editor) -> None:
        fold = fold_named(editing.net, Vec(11, 13), Vec(12, 13))
        target = editing.drag_target(1, v("10.9", "13.02"), fold=fold)  # beyond C_1: projected onto the end
        assert target.position == Vec(11, 13)
        assert editing.move_point(1, target) is not None


class TestInnerPointsStayOffThePerimeter:
    def test_release_over_a_perimeter_hitbox_is_rejected(self, editing: Editor) -> None:
        before = positions(editing)
        close = v("11.5", "13.98")  # strictly inside the net, but in the hitbox of the cut above
        target = editing.drag_target(1, close)
        rejection = editing.move_point(1, target, over_perimeter=True)
        assert rejection is not None
        assert rejection.segments == ((before[0], close), (close, before[2]))
        assert positions(editing) == before

    def test_the_same_position_is_fine_when_not_over_a_hitbox(self, editing: Editor) -> None:
        assert editing.move_point(1, editing.drag_target(1, v("11.6", "13.8"))) is None

    def test_endpoints_are_not_affected(self, editing: Editor) -> None:
        assert editing.move_point(0, editing.drag_target(0, v("11.8", "14")), over_perimeter=True) is None


class TestEndpointWalk:
    """The bug from session-20261108-190056-647-18738.log: an end on H_1-E_1, dragged down, stopped at E_1."""

    @pytest.fixture
    def line_to_h1_e1(self, net: Net, cut: Callable[[str], HalfEdge]) -> Editor:
        editor = Editor(net)
        editor.click(Vec(12, 13), None, vertex_at(net, 12, 13))  # D_1
        editor.click(v("11.047", "11.373"), cut("H_1-E_1"))
        assert editor.state is EditorState.CUT_EDITING
        return editor

    def test_past_the_end_of_the_cut_in_one_drag(self, line_to_h1_e1: Editor) -> None:
        target = line_to_h1_e1.drag_target(1, v("11.033", "10.713"))
        assert target.position == v("11", "10.713")
        assert target.vertex is None
        assert target.edge is not None and target.edge.region is not None and target.edge.region.face == 5

    def test_and_back_again(self, line_to_h1_e1: Editor) -> None:
        down = line_to_h1_e1.drag_target(1, v("11.033", "10.713"))
        back = line_to_h1_e1.drag_target(1, v("11.013", "11.293"), current=down)
        assert back.position == v("11", "11.293")

    def test_step_by_step_as_the_mouse_moves(self, line_to_h1_e1: Editor) -> None:
        current = None
        for y in ("11.2", "11.05", "11", "10.95", "10.8"):
            current = line_to_h1_e1.drag_target(1, v("11.02", y), current=current)
            assert current.position == v("11", y)

    def test_the_image_goes_around_the_corner_with_it(self, line_to_h1_e1: Editor) -> None:
        from cube_net.core.cutting import counterpart_image, endpoint_point

        net = line_to_h1_e1.net
        target = line_to_h1_e1.drag_target(1, v("11.033", "10.713"))
        image = counterpart_image(net, target)
        assert image is not None
        assert image.point == endpoint_point(net, target)
        assert image.position.x == 10 and F(12) < image.position.y < F(13)  # on E_2-A_2

    def test_stops_where_it_gets_no_closer(self, line_to_h1_e1: Editor) -> None:
        target = line_to_h1_e1.drag_target(1, v("9", "9"))  # towards the corner A_3 and no further
        assert target.position == Vec(11, 10)

    def test_snaps_to_a_vertex_in_whose_circle_the_mouse_is(self, line_to_h1_e1: Editor, net: Net) -> None:
        e1 = vertex_at(net, 11, 11)
        target = line_to_h1_e1.drag_target(1, v("11.02", "11.02"), vertex=e1)
        assert target.position == Vec(11, 11) and target.vertex is e1
        assert line_to_h1_e1.move_point(1, target) is None
        assert positions(line_to_h1_e1)[1] == Vec(11, 11)


class TestGlue:
    def cut_at(self, editor: Editor, a: Vec, b: Vec) -> HalfEdge:
        return next(
            he
            for he in editor.split().net.boundary_edges()
            if {he.origin.position, he.destination.position} == {a, b} and he not in editor.split().line_edges
        )

    def test_click_moves_the_other_half_and_goes_to_approving(self, editing: Editor) -> None:
        assert editing.display_net is editing.net
        assert editing.glue(self.cut_at(editing, v("11.5", "10"), Vec(12, 10))) is None
        assert editing.state is EditorState.CUT_APPROVING
        assert editing.display_net is not editing.net
        assert editing.rearranged is not None
        assert editing.rearranged.motion.t == Vec(0, -4)

    def test_counterpart_in_the_same_half_is_rejected_with_that_segment(self, editing: Editor) -> None:
        rejection = editing.glue(self.cut_at(editing, Vec(10, 12), Vec(11, 12)))
        assert rejection is not None
        assert set(rejection.segment) == {Vec(10, 12), Vec(11, 12)}
        assert editing.state is EditorState.CUT_EDITING

    def test_the_new_line_itself_means_nothing(self, editing: Editor) -> None:
        line_edge = next(iter(editing.split().line_edges))
        assert editing.glue(line_edge) is None
        assert editing.state is EditorState.CUT_EDITING

    def test_undo_goes_back_with_the_line_intact(self, editing: Editor) -> None:
        before = positions(editing)
        editing.glue(self.cut_at(editing, v("11.5", "10"), Vec(12, 10)))
        editing.undo()
        assert editing.state is EditorState.CUT_EDITING
        assert positions(editing) == before
        assert editing.display_net is editing.net

    def test_split_follows_the_line(self, editing: Editor) -> None:
        first = editing.split()
        assert editing.split() is first  # computed once
        assert editing.insert_midpoint(0) is None
        second = editing.split()
        assert second is not first
        assert any(w.position == v("11.5", "13.75") for w in second.net.vertices)


class TestApprove:
    def rearranged(self, editing: Editor) -> None:
        cut = next(
            he
            for he in editing.split().net.boundary_edges()
            if {he.origin.position, he.destination.position} == {v("11.5", "10"), Vec(12, 10)}
        )
        assert editing.glue(cut) is None

    def test_makes_it_the_current_net_and_goes_to_default(self, editing: Editor) -> None:
        self.rearranged(editing)
        old = editing.net
        assert editing.approved_cuts == 0
        editing.approve()
        assert editing.state is EditorState.DEFAULT
        assert editing.net is not old
        assert editing.display_net is editing.net
        assert editing.cut_line is None and editing.rearranged is None
        assert editing.approved_cuts == 1
        assert len(editing.net.vertices) == 20

    def test_nothing_to_approve(self, editing: Editor) -> None:
        with pytest.raises(RuntimeError, match="nothing to approve"):
            editing.approve()

    def test_the_next_cut_works_on_the_new_net(self, editing: Editor) -> None:
        self.rearranged(editing)
        editing.approve()
        new_cut = next(he for he in editing.net.boundary_edges() if he.origin.position == v("11.5", "9.5"))
        assert editing.click(v("11.75", "9.5"), new_cut) is None  # on y_2-z_2, which didn't exist before
        assert editing.state is EditorState.CUTTING


def on_cut_through(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {a, b})


class TestUndoRedo:
    """docs/idea.txt: every action can be undone and redone, in every state."""

    def state_of(self, editor: Editor) -> tuple[object, ...]:
        """All there is to the editor's state. Nets and rearrangements never change: they must be the same objects."""
        points = None if editor.cut_line is None else tuple(editor.cut_line.points)
        return editor.state, editor.net, points, editor.rearranged, editor.approved_cuts

    def bottom_of_face_5(self, editor: Editor) -> HalfEdge:
        return on_cut_through(editor.split().net, v("11.5", "10"), Vec(12, 10))

    def test_nothing_to_undo_or_redo_at_first(self, net: Net) -> None:
        editor = Editor(net)
        assert not editor.undo()
        assert not editor.redo()
        assert editor.state is EditorState.DEFAULT

    def test_a_whole_walk_there_and_back(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        """All five kinds of actions; every step back and forth gives exactly the state that was there."""
        editor = Editor(net)
        actions: list[Callable[[], object]] = [
            lambda: editor.click(v("11.5", "14"), cut("B_1-A_1")),  # the first point: CUTTING
            lambda: editor.click(v("11.5", "13.5"), None),
            lambda: editor.click(v("12", "13.5"), cut("D_1-B_1")),  # the closing point: CUT_EDITING
            lambda: editor.insert_midpoint(0),
            lambda: editor.move_point(1, editor.drag_target(1, v("11.6", "13.8"))),
            lambda: editor.delete_point(1),
            lambda: editor.glue(self.bottom_of_face_5(editor)),  # CUT_APPROVING
            lambda: editor.approve(),  # DEFAULT
        ]
        states = [self.state_of(editor)]
        for action in actions:
            assert action() is None
            states.append(self.state_of(editor))
        assert [s[0] for s in states] == [
            EditorState.DEFAULT,
            EditorState.CUTTING,
            EditorState.CUTTING,
            EditorState.CUT_EDITING,
            EditorState.CUT_EDITING,
            EditorState.CUT_EDITING,
            EditorState.CUT_EDITING,
            EditorState.CUT_APPROVING,
            EditorState.DEFAULT,
        ]

        assert editor.undo()  # the approval and the rearrangement together
        assert self.state_of(editor) == states[6]
        for i in range(5, -1, -1):
            assert editor.undo()
            assert self.state_of(editor) == states[i]
        assert not editor.undo()

        for i in range(1, 9):
            assert editor.redo()
            assert self.state_of(editor) == states[i]
        assert not editor.redo()

    def test_redo_after_undoing_an_approval_is_one_action_at_a_time(self, editing: Editor) -> None:
        editing.glue(self.bottom_of_face_5(editing))
        editing.approve()
        approved = editing.net
        editing.undo()
        assert editing.state is EditorState.CUT_EDITING
        assert editing.approved_cuts == 0
        editing.redo()
        assert editing.state is EditorState.CUT_APPROVING
        assert editing.rearranged is not None
        assert editing.display_net is editing.rearranged.net
        editing.redo()
        assert editing.state is EditorState.DEFAULT
        assert editing.net is approved
        assert editing.approved_cuts == 1

    def test_back_to_the_original_net_after_approving(self, editing: Editor) -> None:
        original = editing.net
        editing.glue(self.bottom_of_face_5(editing))
        editing.approve()
        editing.undo()
        assert editing.net is original

    def test_a_new_action_forgets_what_could_be_redone(self, editing: Editor) -> None:
        editing.insert_midpoint(0)
        editing.undo()
        assert editing.history.can_redo
        editing.insert_midpoint(1)
        assert not editing.history.can_redo
        assert not editing.redo()

    def test_an_overlapping_rearrangement_cannot_be_redone(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        editor.click(v("12", "13.5"), cut("D_1-B_1"))
        editor.click(v("11", "11.5"), on_cut_through(net, Vec(11, 11), Vec(11, 12)))
        assert editor.state is EditorState.CUT_EDITING
        before = self.state_of(editor)[2]
        chosen = next(
            he
            for he in editor.split().net.boundary_edges()
            if he.origin.position.y == he.destination.position.y == 13
            and min(he.origin.position.x, he.destination.position.x) > 12
            and he not in editor.split().line_edges
        )
        assert editor.glue(chosen) is None
        assert editor.rearranged is not None and not editor.rearranged.valid
        assert editor.undo()
        assert editor.state is EditorState.CUT_EDITING
        assert self.state_of(editor)[2] == before
        assert not editor.redo()

    def test_the_split_follows_undo_and_redo(self, editing: Editor) -> None:
        split = editing.split()
        editing.insert_midpoint(0)
        editing.undo()
        assert editing.split() is not split  # worked out anew, for the line as it is now
        assert len(editing.split().line_edges) == len(split.line_edges)
        editing.redo()
        assert len(editing.split().line_edges) == len(split.line_edges) + 2  # a new segment: both of its half-edges

    def test_later_edits_do_not_change_what_was_remembered(self, editing: Editor) -> None:
        """Later edits work on the line as it is now; they must not leak into what was remembered."""
        before = positions(editing)
        editing.insert_midpoint(0)
        editing.undo()
        editing.insert_midpoint(1)
        editing.undo()
        assert positions(editing) == before

    def test_what_changes_nothing_is_not_an_action(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        editor.click(v("11.5", "12.5"), None)  # off the perimeter in DEFAULT
        assert editor.history.done_count == 0
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        editor.click(v("11.5", "13.5"), None)
        assert editor.history.done_count == 2
        assert editor.click(v("11.5", "14"), cut("B_1-A_1")) is not None  # rejected: ends at the start
        assert editor.history.done_count == 2
        editor.click(v("12", "13.5"), cut("D_1-B_1"))
        assert editor.history.done_count == 3
        editor.click(v("11.5", "13.7"), None)  # the line is closed
        assert editor.history.done_count == 3
        assert editor.move_point(1, editor.drag_target(1, v("11.5", "13.5"))) is None  # to where it is
        assert editor.history.done_count == 3
        assert editor.move_point(1, editor.drag_target(1, Vec(13, 13))) is not None  # off the net
        assert editor.glue(on_cut_through(editor.split().net, Vec(10, 12), Vec(11, 12))) is not None  # the same half
        assert editor.history.done_count == 3


class TestStraight:
    """SHIFT: the segment from the previous point is horizontal or vertical, whatever it snaps to."""

    Y = v("11.5", "13.5")

    def cutting(self, net: Net, cut: Callable[[str], HalfEdge]) -> Editor:
        editor = Editor(net)
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        editor.click(self.Y, None)
        return editor

    def test_free_point(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        assert editor.candidate(v("11.7", "13.4"), None, straight=True).position == v("11.7", "13.5")
        assert editor.candidate(v("11.6", "13.2"), None, straight=True).position == v("11.5", "13.2")

    def test_without_shift_nothing_changes(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        assert editor.candidate(v("11.7", "13.4"), None).position == v("11.7", "13.4")

    def test_click_creates_it(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        assert editor.click(v("11.7", "13.4"), None, straight=True) is None
        assert positions(editor)[-1] == v("11.7", "13.5")

    def test_click_ends_the_line_on_a_cut(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        assert editor.click(v("11.98", "13.45"), cut("D_1-B_1"), straight=True) is None
        assert editor.state is EditorState.CUT_EDITING
        assert positions(editor)[-1] == self.Y + Vec(F(1, 2), 0)

    def test_it_can_be_undone(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        editor.click(v("11.7", "13.4"), None, straight=True)
        editor.undo()
        assert positions(editor)[-1] == self.Y
        editor.redo()
        assert positions(editor)[-1] == v("11.7", "13.5")

    def test_vertex_on_its_line(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        b_1 = vertex_at(net, 12, 14)
        point = editor.candidate(v("11.99", "13.99"), None, b_1, straight=True)
        assert point.vertex is b_1 and point.position == Vec(12, 14)

    def test_vertex_off_its_line_is_ignored(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        point = editor.candidate(v("11.9", "13.45"), None, vertex_at(net, 12, 14), straight=True)
        assert point.vertex is None and point.position == v("11.9", "13.5")

    def test_vertex_off_its_line_leaves_the_cut_under_it(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        point = editor.candidate(v("11.99", "13.45"), cut("D_1-B_1"), None, straight=True)
        assert point.edge is not None and point.position == v("12", "13.5")

    def test_end_of_the_cut_is_its_vertex(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        editor.click(v("11.5", "13"), None, fold=fold_named(net, Vec(11, 13), Vec(12, 13)))
        point = editor.candidate(v("11.99", "13.01"), cut("D_1-B_1"), straight=True)
        assert point.position == Vec(12, 13) and point.vertex is not None

    def test_fold_across_its_line(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        fold = fold_named(net, Vec(11, 13), Vec(12, 13))
        point = editor.candidate(v("11.6", "13.01"), None, fold=fold, straight=True)
        assert point.fold is fold and point.position == v("11.5", "13")

    def test_fold_parallel_to_its_line_is_ignored(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = self.cutting(net, cut)
        point = editor.candidate(
            v("11.9", "13.45"), None, fold=fold_named(net, Vec(11, 13), Vec(12, 13)), straight=True
        )
        assert point.fold is None and point.position == v("11.9", "13.5")

    def test_along_the_fold_it_stands_on(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        fold = fold_named(net, Vec(11, 13), Vec(12, 13))
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        editor.click(v("11.5", "13"), None, fold=fold)
        point = editor.candidate(v("11.7", "13.01"), None, fold=fold, straight=True)
        assert point.fold is fold and point.position == v("11.7", "13")

    def test_slanted_cut_at_its_crossing_not_the_closest_point(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        editor = Editor(net)
        editor.click(v("11.5", "14"), cut("B_1-A_1"))
        editor.click(v("12", "13.5"), cut("D_1-B_1"))
        edge = next(
            he
            for he in editor.split().net.boundary_edges()
            if {he.origin.position, he.destination.position} == {v("11.5", "10"), Vec(12, 10)}
        )
        assert editor.glue(edge) is None
        editor.approve()
        slanted = next(
            he
            for he in editor.net.boundary_edges()
            if he.origin.position.x != he.destination.position.x and he.origin.position.y != he.destination.position.y
        )
        a, b = slanted.origin.position, slanted.destination.position
        middle = (a + b) / 2
        anchor = middle - Vec(0, F(1, 2))
        editor.cut_line = CutLine([CutPoint(anchor)])
        point = editor.candidate(middle + Vec(F(1, 100), F(-1, 100)), slanted, straight=True)
        assert point.position == middle and point.edge is slanted

    class TestDragging:
        def test_the_first_point_goes_as_usual(self, editing: Editor) -> None:
            assert editing.drag_target(0, v("11.3", "14.2"), straight=True).position == v("11.3", "14")

        def test_an_inner_point(self, editing: Editor) -> None:
            assert editing.drag_target(1, v("11.7", "13.2"), straight=True).position == v("11.5", "13.2")
            assert editing.drag_target(1, v("11.8", "13.9"), straight=True).position == v("11.8", "14")

        def test_an_inner_point_on_a_fold(self, net: Net, editing: Editor) -> None:
            fold = fold_named(net, Vec(11, 13), Vec(12, 13))
            point = editing.drag_target(1, v("11.6", "13.01"), fold=fold, straight=True)
            assert point.fold is fold and point.position == v("11.5", "13")

        def test_the_segment_to_the_next_point_stays_free(self, editing: Editor) -> None:
            target = editing.drag_target(1, v("11.7", "13.2"), straight=True)
            assert editing.move_point(1, target) is None
            line = positions(editing)
            assert line[0].x == line[1].x
            assert line[1].x != line[2].x and line[1].y != line[2].y

        def test_the_last_point_stays_on_the_perimeter(self, editing: Editor) -> None:
            point = editing.drag_target(2, v("11.1", "13.4"), straight=True)
            assert point.position == v("11", "13.5") and point.edge is not None
            assert editing.move_point(2, point) is None
            assert positions(editing)[2] == v("11", "13.5")

        def test_the_last_point_at_a_vertex(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
            editor = Editor(net)
            editor.click(v("11.5", "14"), cut("B_1-A_1"))
            editor.click(v("11.5", "13"), None, fold=fold_named(net, Vec(11, 13), Vec(12, 13)))
            editor.click(Vec(12, 13), cut("D_1-B_1"))
            point = editor.drag_target(2, v("12.9", "13.1"), straight=True)
            assert point.position == Vec(13, 13) and point.vertex is not None

        def test_a_move_that_breaks_the_rules_is_still_rejected(self, editing: Editor) -> None:
            before = positions(editing)
            point = editing.drag_target(2, v("11.6", "13.9"), straight=True)  # back to the start of the line
            assert point.position == v("11.5", "14")
            assert editing.move_point(2, point) is not None
            assert positions(editing) == before
