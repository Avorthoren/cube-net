# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: cutting, rearranging and approving, undo and redo, the target area, blinking counterparts."""

from fractions import Fraction as F
from pathlib import Path

import pytest
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot
from window_checks import session_lines, settings_in

from cube_net.core.geometry import Vec
from cube_net.core.project import project_from_bytes
from cube_net.ui.main_window import (
    MainWindow,
)
from cube_net.ui.session.snapshots import snapshots_in


class TestRearrangement:
    def closed_corner_cut(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        view = window.sheet_view
        inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - inside)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - inside, 13.5)

    def bottom_of_face_5(self, window: MainWindow) -> tuple[float, float]:
        """On the part x_2-B_3 of the cut A_3-B_3."""
        from cube_net.ui.sheet import net_style

        return 11.75, 10 + net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_click_on_a_part_of_a_cut_rearranges_and_everything_follows(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        view = window.sheet_view
        h1_before = view.from_sheet(QPointF(11, 12))
        assert window.bounding.label.text() == "Area\n12.000"
        view.left_pressed.emit(*self.bottom_of_face_5(window))
        assert window.editor.state.value == "cut_approving"
        assert window.net is window.editor.display_net
        item = view.net_item()
        assert item is not None and len(item.glue()) == 2
        assert window.cut_tool.item.points() == ()  # the line is part of the net now
        assert window.cut_tool.item.midpoints() == []
        assert window.bounding.label.text() != "Area\n12.000"  # the area follows
        r = view.sheet_rect()
        assert r.top() == 4.5  # the sheet follows: y_2 is at 9.5, plus the margin of 5
        h1_after = view.from_sheet(QPointF(11, 12))
        assert (h1_after.x(), h1_after.y()) == pytest.approx((h1_before.x(), h1_before.y()), abs=1.5)  # nothing jumps

    def test_undo_goes_back_to_editing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.closed_corner_cut(window)
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        window.undo_action.trigger()
        assert window.editor.state.value == "cut_editing"
        assert window.bounding.label.text() == "Area\n12.000"
        assert len(window.cut_tool.item.points()) == 3
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert lines[-2:] == ["cut glue 11.500,10.000 12.000,10.000 ok", "cut undo cut_editing"]
        window.stop_recording("test over")

    def test_labels_keep_the_previewed_names_after_rearranging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        before = {label.name for _, label in window.cut_tool.item.labels()}
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        item = window.sheet_view.net_item()
        assert item is not None
        labels = item.labels()
        assert labels is not None
        assert before == {"I", "J", "K"}
        assert before <= {label.name for label in labels.values()}
        assert sorted(label.index for label in labels.values() if label.name == "I") == [1, 2, 3]  # x_1, x_2, x's copy

    def test_hover_follows_the_divided_cut_in_editing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        x, y = self.bottom_of_face_5(window)
        window.cut_hover.update_at(x, y)
        cut = window.cut_hover.hovered()
        assert cut is not None
        ends = {float(p.x) for p in (cut.origin.position, cut.destination.position)}
        assert ends == {11.5, 12.0}  # only the part x_2-B_3 of A_3-B_3

    def test_state_snapshot_has_the_glue(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        window.logging_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "state glue 11.500,10.000 12.000,10.000" in lines
        assert any(line.startswith("state cut cut_approving ") for line in lines)
        window.stop_recording("test over")


class TestApproveButton:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def valid_rearrangement(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)

    def overlapping_rearrangement(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)  # on D_1-B_1
        view.left_pressed.emit(11 + h, 11.5)  # on H_1-E_1: closes the line
        view.left_pressed.emit(12.75, 13 + h - 2 * h)  # on z_3-B_2, from inside face 3

    def test_disabled_until_a_valid_rearrangement(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.approve_action.isEnabled()
        self.valid_rearrangement(window)
        assert window.approve_action.isEnabled()
        item = window.sheet_view.net_item()
        assert item is not None and item.overlapping() == frozenset()
        window.undo_action.trigger()
        assert not window.approve_action.isEnabled()

    def test_overlap_shown_black_and_not_approvable(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.overlapping_rearrangement(window)
        assert window.editor.state.value == "cut_approving"
        assert not window.approve_action.isEnabled()
        item = window.sheet_view.net_item()
        assert item is not None and item.overlapping()
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1].endswith(" overlap")
        window.undo_action.trigger()
        assert item.overlapping() == frozenset()
        window.stop_recording("test over")

    def test_click_on_the_x_acts_as_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.overlapping_rearrangement(window)
        line = window.editor.cut_line
        window.sheet_view.left_pressed.emit(12.75, 13.0)
        window.sheet_view.left_released.emit(12.75, 13.0)
        assert window.editor.state.value == "cut_editing"
        assert window.editor.cut_line is not None and window.editor.cut_line.points == line.points
        assert window.net is window.editor.net
        assert window.cut_tool.approve_button.position() is None
        assert not window.redo_action.isEnabled()  # it overlapped: it's forgotten
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "cut undo cut_editing"
        window.stop_recording("test over")

    def test_shortcut_is_ctrl_enter(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.approve_action.shortcut().toString() == "Ctrl+Return"


class TestDividedView:
    """While hovering a perimeter edge in CUT_EDITING, cuts that can't be chosen are shown thin and black."""

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
        """From the top of face 1, through y, to its right side (the corner cut)."""
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def divided_on(self, window: MainWindow) -> bool:
        item = window.sheet_view.net_item()
        assert item is not None
        return item.divided() is not None

    def hover_edge(self, window: MainWindow) -> None:
        window.sheet_view.mouse_moved.emit(10 + self.hitbox(window), 12.5)  # A_2-E_2

    def test_on_while_hovering_an_edge_off_elsewhere(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(7.0, 7.0)
        assert not self.divided_on(window)
        self.hover_edge(window)
        assert self.divided_on(window)
        window.sheet_view.mouse_moved.emit(11.5, 12.5)  # the middle of face 2
        assert not self.divided_on(window)
        self.hover_edge(window)
        window.sheet_view.mouse_left.emit()
        assert not self.divided_on(window)

    def test_off_in_other_states(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.hover_edge(window)
        assert not self.divided_on(window)  # DEFAULT
        h = self.hitbox(window)
        window.sheet_view.mouse_moved.emit(7.0, 7.0)
        window.sheet_view.left_pressed.emit(11.5, 14 - h)
        self.hover_edge(window)
        assert not self.divided_on(window)  # CUTTING

    def test_off_while_the_ruler_is_active(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_edge(window)
        assert self.divided_on(window)
        window.ruler_action.setChecked(True)
        assert not self.divided_on(window)
        window.sheet_view.mouse_moved.emit(7.0, 7.0)
        self.hover_edge(window)
        assert not self.divided_on(window)
        window.ruler_action.setChecked(False)
        assert self.divided_on(window)  # still over the edge

    def test_off_while_dragging_a_point(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_edge(window)
        assert self.divided_on(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)  # the inner point: the drag starts
        assert not self.divided_on(window)
        self.hover_edge(window)
        assert not self.divided_on(window)
        view.left_released.emit(11.5, 13.5)
        view.mouse_moved.emit(7.0, 7.0)
        self.hover_edge(window)
        assert self.divided_on(window)

    def test_the_new_line_itself_does_not_trigger_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(11.5 + self.hitbox(window), 13.8)  # beside the new line
        assert not self.divided_on(window)

    def test_off_after_rearranging_and_back_after_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        h = self.hitbox(window)
        window.sheet_view.mouse_moved.emit(11.75, 10 + h)
        assert self.divided_on(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + h)
        assert window.editor.state.value == "cut_approving"
        assert not self.divided_on(window)
        window.undo_action.trigger()
        assert not self.divided_on(window)  # the hover was reset; the next move decides
        window.sheet_view.mouse_moved.emit(11.75, 10 + h)
        assert self.divided_on(window)


class TestApproving:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def rearranged(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)

    def test_check_mark_accepts_and_everything_follows(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.rearranged(window)
        area = window.bounding.label.text()
        window.approve_action.trigger()
        assert window.editor.state.value == "default"
        assert window.net is window.editor.net
        assert not window.approve_action.isEnabled()
        assert window.undo_action.isEnabled()
        assert window.bounding.label.text() == area
        item = window.sheet_view.net_item()
        assert item is not None
        assert item.glue() == () and item.overlapping() == frozenset()
        assert window.cut_tool.item.points() == ()
        labels = item.labels()
        assert labels is not None and len(labels) == 20
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-2:] == [
            "cut glue 11.500,10.000 12.000,10.000 ok",
            "cut approve",
        ]
        window.stop_recording("test over")

    @pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Enter])
    def test_ctrl_enter_accepts(self, qtbot: QtBot, tmp_path: Path, key: Qt.Key) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearranged(window)
        qtbot.keyClick(window, key, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "default"

    def test_ctrl_enter_does_nothing_when_not_approvable(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        qtbot.keyClick(window, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "default"
        assert window.editor.approved_cuts == 0

    def test_the_next_cut_starts_on_the_new_net(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        self.rearranged(window)
        window.approve_action.trigger()
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        assert view.press_claimed(11.75, 9.5 + h)  # a cut of the moved piece, under face 5
        assert not view.press_claimed(11.75, 13.9)  # where the top of face 1 was
        window.cut_hover.update_at(11.75, 9.5 + h)
        cut = window.cut_hover.hovered()
        assert cut is not None  # y_2-z_2, a cut of the new net
        view.left_pressed.emit(11.75, 9.5 + h)
        assert window.editor.state.value == "cutting"
        assert window.cut_tool.item.points()[0].position == Vec(F(47, 4), F(19, 2))

    def test_state_snapshot_describes_the_new_net(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearranged(window)
        window.approve_action.trigger()
        window.logging_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "state net after 1 approved cuts" in lines
        snapshots = snapshots_in(window.recorder.log.path)
        project = project_from_bytes(snapshots[-1])
        assert project.state.approved_cuts == 1
        assert len(project.state.net.regions) == 7
        window.stop_recording("test over")


class TestApproveButtonOnTheSheet:
    def test_clicking_it_approves_and_it_is_not_on_the_panel(self, qtbot: QtBot, tmp_path: Path) -> None:

        from cube_net.ui.sheet import net_style

        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        toolbar = window.findChild(QToolBar, "instruments")
        assert toolbar is not None and window.approve_action not in toolbar.actions()
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)
        assert window.editor.state.value == "cut_approving"
        position = view.from_sheet(QPointF(11.75, 10)).toPoint()
        qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=position)
        assert window.editor.state.value == "default"
        assert window.cut_tool.approve_button.position() is None


class TestUndoRedo:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def closed_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def rearrange(self, window: MainWindow) -> None:
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))

    def shown(self, window: MainWindow) -> tuple[object, ...]:
        """What the user sees of the state."""
        item = window.sheet_view.net_item()
        assert item is not None
        return (
            window.editor.state,
            window.net,
            window.cut_tool.item.points(),
            item.glue(),
            item.overlapping(),
            window.bounding.label.text(),
            window.cut_tool.approve_button.position(),
            window.approve_action.isEnabled(),
        )

    def test_nothing_to_undo_at_first(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.undo_action.isEnabled()
        assert not window.redo_action.isEnabled()

    def test_shortcuts(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "cutting"
        qtbot.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "cut_editing"

    def test_in_every_state_everything_on_screen_follows(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        h = self.hitbox(window)
        steps = [
            lambda: view.left_pressed.emit(11.5, 14 - h),
            lambda: view.left_pressed.emit(11.5, 13.5),
            lambda: view.left_pressed.emit(12 - h, 13.5),
            lambda: self.rearrange(window),
        ]
        states = [self.shown(window)]
        for step in steps:
            step()
            states.append(self.shown(window))
        assert window.approve_action.isEnabled()
        window.approve_action.trigger()
        states.append(self.shown(window))
        assert window.editor.state.value == "default"

        window.undo_action.trigger()  # the approval and the rearrangement together
        assert self.shown(window) == states[3]
        for i in (2, 1, 0):
            window.undo_action.trigger()
            assert self.shown(window) == states[i]
        assert not window.undo_action.isEnabled()
        for i in range(1, 6):
            assert window.redo_action.isEnabled()
            window.redo_action.trigger()
            assert self.shown(window) == states[i]
        assert not window.redo_action.isEnabled()

    def test_a_new_action_disables_redo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        window.undo_action.trigger()
        assert window.redo_action.isEnabled()
        window.sheet_view.left_pressed.emit(11.7, 13.7)
        assert not window.redo_action.isEnabled()

    def test_not_while_dragging_a_point(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        assert window.cut_tool.dragging
        assert not window.undo_action.isEnabled()
        view.mouse_moved.emit(11.6, 13.6)
        assert not window.undo_action.isEnabled()
        view.left_released.emit(11.6, 13.6)
        assert window.undo_action.isEnabled()
        window.undo_action.trigger()
        line = window.editor.cut_line
        assert line is not None and float(line.points[1].position.x) == 11.5

    def test_pressing_a_point_without_moving_it_gives_undo_back(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        done = window.editor.history.done_count
        window.sheet_view.left_pressed.emit(11.5, 13.5)
        window.sheet_view.left_released.emit(11.5, 13.5)
        assert window.undo_action.isEnabled()
        assert window.editor.history.done_count == done

    def test_rubber_band_does_not_start_at_a_point_that_is_gone(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.7, 13.5)
        window.undo_action.trigger()
        assert window.cut_tool.item.rubber_band() is None
        view.mouse_moved.emit(11.7, 13.5)
        band = window.cut_tool.item.rubber_band()
        assert band is not None and band[0].y == 14

    def test_hover_follows_the_line_after_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        view = window.sheet_view
        view.mouse_moved.emit(10 + self.hitbox(window), 12.5)
        item = view.net_item()
        assert item is not None and item.divided() is not None
        window.undo_action.trigger()  # the line isn't closed anymore: nothing to show
        assert window.editor.state.value == "cutting"
        assert item.divided() is None
        window.redo_action.trigger()
        view.mouse_moved.emit(7.0, 7.0)
        view.mouse_moved.emit(10 + self.hitbox(window), 12.5)
        assert item.divided() is window.editor.split()

    def test_labels_come_back(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        self.rearrange(window)
        item = window.sheet_view.net_item()
        assert item is not None

        def names() -> set[str]:
            labels = item.labels()
            assert labels is not None
            return {str(label) for label in labels.values()}

        window.approve_action.trigger()
        approved = names()
        window.undo_action.trigger()
        window.redo_action.trigger()
        window.redo_action.trigger()
        assert names() == approved

    def test_the_ruler_is_not_part_of_the_history(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        done = window.editor.history.done_count
        window.ruler_tool.set_active(True)
        window.sheet_view.left_pressed.emit(7.0, 7.0)
        points = window.ruler_tool.ruler.points
        assert len(points) == 1
        assert window.editor.history.done_count == done
        window.undo_action.trigger()
        assert window.ruler_tool.ruler.points == points

    def test_drawing_area_follows_the_net(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        self.rearrange(window)
        window.undo_action.trigger()
        area = window.cut_tool.item.boundingRect()
        box = window.editor.display_net.bounding_box()
        assert area.left() < float(box.lo.x) and area.bottom() > float(box.hi.y)

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.closed_line(window)
        window.undo_action.trigger()
        window.redo_action.trigger()
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-2:] == ["cut undo cutting", "cut redo cut_editing"]
        window.stop_recording("test over")


class TestTargetArea:
    """The project's target area, edited on the instruments panel."""

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def enter(self, qtbot: QtBot, window: MainWindow, text: str) -> None:
        """Type it into the field and press Enter, as the user does."""
        line = window.bounding.target.lineEdit()
        assert line is not None
        line.selectAll()
        qtbot.keyClicks(line, text)
        qtbot.keyClick(line, Qt.Key.Key_Return)

    def test_it_shows_the_project_s_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.bounding.target.text() == "7.100"
        assert window.bounding.target_label.text() == "Target area"

    def test_its_range_and_decimals(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        field = window.bounding.target
        assert (field.minimum(), field.maximum(), field.decimals()) == (0, 10000, 3)

    def test_an_entered_value_is_used_at_once(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.bounding.success
        self.enter(qtbot, window, "12.5")  # the cross has 12.000
        assert window.project_settings.area_threshold == F(25, 2)
        assert window.bounding.success
        self.enter(qtbot, window, "6.789")
        assert window.project_settings.area_threshold == F(6789, 1000)
        assert not window.bounding.success

    def test_digits_count_only_once_entered(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        line = window.bounding.target.lineEdit()
        assert line is not None
        line.selectAll()
        qtbot.keyClicks(line, "13")
        assert window.project_settings.area_threshold == F(71, 10)

    def test_out_of_range_cannot_get_through(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.enter(qtbot, window, "12345")
        assert 0 <= window.project_settings.area_threshold <= 10000

    def test_a_change_is_an_unsaved_change(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.enter(qtbot, window, "5")
        assert window.is_dirty and window.isWindowModified()
        assert window.save_project_to(tmp_path / "cube.cubenet")
        assert not window.is_dirty
        self.enter(qtbot, window, "6")
        self.enter(qtbot, window, "5")
        assert not window.is_dirty  # back to what was saved

    def test_saved_with_the_project_and_shown_when_opened(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.enter(qtbot, window, "5")
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        other = self.make(qtbot, tmp_path)
        other.open_project_from(path)
        assert other.project_settings.area_threshold == 5
        assert other.bounding.target.text() == "5.000"
        assert not other.is_dirty
        other.start_new_project()
        assert other.bounding.target.text() == "7.100"
        assert not other.is_dirty

    def test_undo_does_not_touch_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.sheet_view.left_pressed.emit(10.0, 13.0)
        self.enter(qtbot, window, "5")
        window.undo_action.trigger()
        assert window.project_settings.area_threshold == 5

    def test_no_more_project_settings_in_the_file_menu(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not hasattr(window, "project_settings_action")

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        assert window.recorder is not None
        assert "state threshold 7.100" in session_lines(window.recorder.log.path)
        self.enter(qtbot, window, "5")
        assert session_lines(window.recorder.log.path)[-1] == "project threshold 5.000"
        window.stop_recording("test over")


# x_1-B_1, on the top of face 1 (for the corner cut).
TOP_PART = frozenset({Vec(F(23, 2), 14), Vec(12, 14)})


class TestCounterpartBlinks:
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

    def blinking(self, window: MainWindow) -> set[Vec] | None:
        cut = window.counterpart_blink.cut()
        return None if cut is None else {cut.origin.position, cut.destination.position}

    def hover_bottom(self, window: MainWindow) -> None:
        """x_2-B_3, on the bottom of face 5: it can be chosen, and its counterpart is x_1-B_1 on the top of face 1."""
        window.sheet_view.mouse_moved.emit(11.75, 10 + self.hitbox(window))

    def test_the_exact_part_that_is_the_counterpart(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        assert self.blinking(window) == TOP_PART
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is window.counterpart_blink.cut()

    def test_it_is_a_cut_that_gets_painted(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        cut = window.counterpart_blink.cut()
        assert cut is not None
        assert cut in window.editor.split().net.boundary_edges()

    def test_it_really_blinks(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        item = window.sheet_view.net_item()
        assert item is not None
        qtbot.waitUntil(lambda: item.hidden_cut() is None, timeout=2000)
        qtbot.waitUntil(lambda: item.hidden_cut() is not None, timeout=2000)

    def test_not_for_a_useless_cut(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(10.5, 12 + self.hitbox(window))  # E_2-H_1: thin and black
        item = window.sheet_view.net_item()
        assert item is not None and item.divided() is not None
        assert window.cut_hover.hovered() is not None
        assert self.blinking(window) is None
        assert item.hidden_cut() is None

    def test_not_for_the_new_line(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(11.5 + self.hitbox(window), 13.8)
        assert self.blinking(window) is None

    def test_not_on_a_vertex(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(12.0, 10.0)
        assert self.blinking(window) is None

    @pytest.mark.parametrize("state", ["default", "cutting"])
    def test_not_in_other_states(self, qtbot: QtBot, tmp_path: Path, state: str) -> None:
        window = self.make(qtbot, tmp_path)
        if state == "cutting":
            window.sheet_view.left_pressed.emit(11.5, 14 - self.hitbox(window))
        self.hover_bottom(window)
        assert window.cut_hover.hovered() is not None
        assert self.blinking(window) is None

    def test_not_while_approving(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))
        assert window.editor.state.value == "cut_approving"
        assert self.blinking(window) is None
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is None

    def test_stops_when_the_mouse_moves_away(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.sheet_view.mouse_moved.emit(11.5, 12.5)
        assert self.blinking(window) is None
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is None

    def test_stops_when_the_mouse_leaves_the_view(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.sheet_view.mouse_left.emit()
        assert self.blinking(window) is None

    def test_follows_the_mouse_to_another_cut(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        assert self.blinking(window) == TOP_PART
        window.sheet_view.mouse_moved.emit(11.75, 14 - self.hitbox(window))  # x_1-B_1: now the other way round
        assert self.blinking(window) == {Vec(F(23, 2), 10), Vec(12, 10)}
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is window.counterpart_blink.cut()

    def test_not_while_dragging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        assert self.blinking(window) is None
        self.hover_bottom(window)
        assert self.blinking(window) is None
        view.left_released.emit(11.75, 10 + self.hitbox(window))
        view.mouse_moved.emit(7.0, 7.0)
        self.hover_bottom(window)
        assert self.blinking(window) is not None

    def test_not_while_the_ruler_is_active(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.ruler_action.trigger()
        assert self.blinking(window) is None
        window.ruler_action.trigger()
        assert self.blinking(window) is not None

    def test_undo_stops_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"
        assert self.blinking(window) is None
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is None

    def test_the_counterpart_follows_the_line(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Moving the end of the line changes where the parts begin."""
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14.0)
        view.mouse_moved.emit(11.25, 14.0)
        view.left_released.emit(11.25, 14.0)
        view.mouse_moved.emit(7.0, 7.0)
        view.mouse_moved.emit(11.75, 10 + self.hitbox(window))
        assert self.blinking(window) == {Vec(F(45, 4), 14), Vec(12, 14)}
