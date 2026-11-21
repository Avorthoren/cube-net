# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: what's highlighted under the mouse, and panning the sheet."""

from pathlib import Path

import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from pytestqt.qtbot import QtBot
from window_checks import settings_in

from cube_net.ui.main_window import (
    MainWindow,
)


class TestFlashKeepsTheHover:
    def test_useless_cuts_stay_thin_black_after_the_flash(self, qtbot: QtBot, tmp_path: Path) -> None:
        """The mouse stays on a cut that can't be chosen: it flashes, and then everything is as it was."""
        from cube_net.ui.sheet import net_style

        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        useless = 10.5, 12 + h  # E_2-H_1: its counterpart is in the same half
        view.mouse_moved.emit(*useless)
        item = view.net_item()
        assert item is not None
        hovered = window.cut_hover.hovered()
        assert hovered is not None and item.divided() is not None

        with qtbot.waitSignal(window.cut_tool.rejected):
            view.left_pressed.emit(*useless)
        assert item.divided() is not None
        qtbot.waitUntil(lambda: window.cut_tool.item.flash() is None, timeout=2000)

        assert window.cut_hover.hovered() is hovered
        assert item.divided() is window.editor.split()


class TestVertexHoverWhileEditing:
    """In CUT_EDITING perimeter vertices can't be clicked, so they don't highlight, except for where a dragged endpoint
    would go."""

    # The corner cut: x on the top of face 1, y, z on its right side; z's image is on the top of face 3.
    X = 11.5, 14.0
    Y = 11.5, 13.5
    Z_IMAGE = 12.5, 13.0
    A_1 = 11.0, 14.0
    B_1 = 12.0, 14.0
    B_2 = 13.0, 13.0

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def close_line(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(*self.Y)
        view.left_pressed.emit(12 - h, 13.5)
        assert window.editor.state.value == "cut_editing"

    def highlighted(self, window: MainWindow) -> tuple[float, float] | None:
        vertex = window.cut_hover.hovered_vertex()
        return None if vertex is None else (float(vertex.position.x), float(vertex.position.y))

    def test_not_while_just_hovering(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        for place in (self.A_1, self.B_2, self.Z_IMAGE, self.X):
            view.mouse_moved.emit(*place)
            assert self.highlighted(window) is None, place

    def test_gone_as_soon_as_the_line_closes(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(*self.A_1)
        view.left_pressed.emit(*self.Y)
        view.mouse_moved.emit(*self.B_1)
        assert self.highlighted(window) == self.B_1  # still cutting: a vertex can end the line
        view.left_pressed.emit(*self.B_1)
        assert window.editor.state.value == "cut_editing"
        assert self.highlighted(window) is None

    def test_where_a_dragged_endpoint_would_go(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(*self.X)
        view.mouse_moved.emit(*self.A_1)
        assert self.highlighted(window) == self.A_1
        view.mouse_moved.emit(11.2, 14.0)
        assert self.highlighted(window) is None
        view.mouse_moved.emit(*self.B_2)
        assert self.highlighted(window) == self.B_2
        view.left_released.emit(*self.B_2)
        assert self.highlighted(window) is None

    def test_a_dragged_endpoint_does_not_light_up_an_image(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(*self.X)
        view.mouse_moved.emit(*self.Z_IMAGE)
        assert self.highlighted(window) is None

    def test_a_dragged_inner_point_does_not_light_up_anything(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(*self.Y)
        view.mouse_moved.emit(*self.A_1)
        assert self.highlighted(window) is None

    def test_back_after_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"
        window.sheet_view.mouse_moved.emit(*self.B_2)
        assert self.highlighted(window) == self.B_2


class TestNoHoverWhileApproving:
    """Only the button can be clicked in CUT_APPROVING, so nothing on the perimeter highlights."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def valid(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)

    def overlapping(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)

    def assert_nothing_highlights(self, window: MainWindow) -> None:
        view = window.sheet_view
        h = self.hitbox(window)
        for x, y in ((10 + h, 12.5), (10.0, 13.0), (11 - h, 11.5), (12.0, 10.0)):  # cuts and vertices
            view.mouse_moved.emit(x, y)
            assert window.cut_hover.hovered() is None, (x, y)
            assert window.cut_hover.hovered_vertex() is None, (x, y)

    def test_with_a_valid_rearrangement(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.valid(window)
        assert window.editor.state.value == "cut_approving"
        self.assert_nothing_highlights(window)

    def test_with_an_overlapping_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.overlapping(window)
        assert window.editor.state.value == "cut_approving"
        self.assert_nothing_highlights(window)

    def test_gone_at_once_when_rearranging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.mouse_moved.emit(11.75, 10 + h)
        assert window.cut_hover.hovered() is not None
        view.left_pressed.emit(11.75, 10 + h)
        assert window.cut_hover.hovered() is None

    def test_back_after_undo_and_after_approving(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.valid(window)
        h = self.hitbox(window)
        view = window.sheet_view
        window.undo_action.trigger()
        view.mouse_moved.emit(10 + h, 12.5)
        assert window.cut_hover.hovered() is not None  # CUT_EDITING: cuts can be chosen
        window.redo_action.trigger()
        self.assert_nothing_highlights(window)
        window.approve_action.trigger()
        assert window.editor.state.value == "default"
        view.mouse_moved.emit(10 + h, 12.5)
        assert window.cut_hover.hovered() is not None
        view.mouse_moved.emit(10.0, 13.0)
        assert window.cut_hover.hovered_vertex() is not None


class TestPanningFromInsideTheNet:
    """A drag pans the sheet from wherever a press means nothing in the current state, even inside the net."""

    MIDDLE_OF_FACE_2 = 11.5, 12.5

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        assert window.editor.state.value == "cut_editing"

    def rearrange(self, window: MainWindow) -> None:
        self.close_line(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))
        assert window.editor.state.value == "cut_approving"

    def assert_drag_pans(self, qtbot: QtBot, window: MainWindow, x: float, y: float) -> None:
        """A real drag from (x, y): the sheet follows the mouse, and the editor doesn't notice."""

        view = window.sheet_view
        state = window.editor.state
        done = window.editor.history.done_count
        start = view.from_sheet(QPointF(x, y)).toPoint()
        end = start + QPoint(40, -30)
        qtbot.mouseMove(view.viewport(), start)
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        assert view.is_panning()
        qtbot.mouseMove(view.viewport(), end)
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
        assert not view.is_panning()
        moved = view.to_sheet(QPointF(end))
        assert (moved.x(), moved.y()) == pytest.approx((x, y), abs=2 / view.scale_factor())
        assert window.editor.state is state
        assert window.editor.history.done_count == done

    def test_default_pans_from_the_middle_of_a_face(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.assert_drag_pans(qtbot, window, *self.MIDDLE_OF_FACE_2)
        assert window.editor.cut_line is None

    def test_default_what_can_be_clicked(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        assert view.press_claimed(10 + h, 12.5)  # a cut
        assert view.press_claimed(10.0, 13.0)  # a vertex
        assert not view.press_claimed(*self.MIDDLE_OF_FACE_2)
        assert not view.press_claimed(10 + 3 * h, 12.5)  # just past the hitbox of the cut

    def test_a_press_on_a_cut_still_starts_the_line(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        pos = view.from_sheet(QPointF(10 + self.hitbox(window), 12.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert window.editor.state.value == "cutting"

    def test_cutting_a_click_on_the_net_still_adds_a_point(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - self.hitbox(window))
        assert view.press_claimed(*self.MIDDLE_OF_FACE_2)
        assert not view.press_claimed(10.5, 13.5)  # off the net: panning, as always

    def test_cut_editing_what_can_be_clicked(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        h = self.hitbox(window)
        view = window.sheet_view
        for place in (
            (11.5, 14.0),  # an endpoint of the line
            (11.5, 13.5),  # its inner point
            (11.5, 13.75),  # the circle in the middle of a segment
            (11.75, 10 + h),  # a cut that can be chosen
            (10.5, 12 + h),  # a cut that can't, which is told by a flash
        ):
            assert view.press_claimed(*place), place
        for place in (
            self.MIDDLE_OF_FACE_2,
            (10.0, 13.0),  # a perimeter vertex
            (12.5, 13.0),  # a counterpart image
            (11.5 + h, 13.625),  # next to the new line, whose hitbox means nothing
        ):
            assert not view.press_claimed(*place), place

    def test_cut_editing_pans_from_a_face_and_a_vertex(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.assert_drag_pans(qtbot, window, *self.MIDDLE_OF_FACE_2)
        self.assert_drag_pans(qtbot, window, 10.0, 13.0)

    def test_cut_approving_only_the_button_can_be_clicked(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearrange(window)
        h = self.hitbox(window)
        view = window.sheet_view
        assert view.press_claimed(11.75, 10.0)  # the button
        for place in (self.MIDDLE_OF_FACE_2, (10 + h, 12.5), (10.0, 13.0)):  # a face, a cut, a vertex
            assert not view.press_claimed(*place), place
        self.assert_drag_pans(qtbot, window, *self.MIDDLE_OF_FACE_2)
        self.assert_drag_pans(qtbot, window, 10 + h, 12.5)

    def test_cut_approving_the_x_can_be_clicked_too(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)
        assert window.editor.rearranged is not None and not window.editor.rearranged.valid
        assert view.press_claimed(12.75, 13.0)

    def test_never_while_the_ruler_is_active(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path)
        window.ruler_tool.set_active(True)
        view = window.sheet_view
        pos = view.from_sheet(QPointF(*self.MIDDLE_OF_FACE_2)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert len(window.ruler_tool.ruler.points) == 1

    def test_dragging_a_point_does_not_pan(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()
        assert window.cut_tool.dragging
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)


class TestShiftInTheWindow:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def test_the_sheet_has_the_focus_from_the_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.sheet_view.hasFocus()

    def test_hover_shows_what_the_straight_segment_ends_on(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        h = self.hitbox(window)
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.7, 13.5)
        in_a_cut = 12 - h, 13.2  # in the hitbox of a cut, while the straight segment goes down from the last point
        view.mouse_moved.emit(*in_a_cut)
        assert window.cut_hover.hovered() is not None
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        assert window.cut_hover.hovered() is None
        view.mouse_moved.emit(12 - h, 13.45)  # now it goes right, into that cut
        assert window.cut_hover.hovered() is not None
        qtbot.keyRelease(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(*in_a_cut)
        assert window.cut_hover.hovered() is not None

    def test_undo_is_back_after_a_ctrl_click(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        h = self.hitbox(window)
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        modifier = Qt.KeyboardModifier.ControlModifier
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, modifier, pos)
        assert not window.undo_action.isEnabled()  # not deleted until it's released
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, modifier, pos)
        assert window.undo_action.isEnabled()
        window.undo_action.trigger()
        assert window.editor.cut_line is not None and len(window.editor.cut_line.points) == 3
