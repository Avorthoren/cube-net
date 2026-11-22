# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication, QFrame
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Box, Vec
from cube_net.ui.sheet import zoom
from cube_net.ui.sheet.sheet_view import SheetView

SHEET = Box(Vec(5, 5), Vec(18, 19))
NET = Box(Vec(10, 10), Vec(13, 14))


@pytest.fixture
def view(qtbot: QtBot) -> SheetView:
    v = SheetView()
    qtbot.addWidget(v)
    v.resize(800, 600)
    v.set_sheet(SHEET)
    v.set_press_claim(lambda x, y: 10 <= x <= 13 and 10 <= y <= 14)
    v.show_initial_view(NET)
    v.show()
    qtbot.waitExposed(v)
    return v


def center_of_viewport(view: SheetView) -> QPointF:
    return QPointF(view.viewport().width() / 2, view.viewport().height() / 2)


def wheel(view: SheetView, pos: QPointF, notches: int) -> None:
    event = QWheelEvent(
        pos,
        view.viewport().mapToGlobal(pos),
        QPoint(0, 0),
        QPoint(0, 120 * notches),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(view.viewport(), event)


class TestCoordinates:
    def test_y_axis_points_up(self, view: SheetView) -> None:
        c1 = view.from_sheet(QPointF(11, 13))
        h1 = view.from_sheet(QPointF(11, 12))
        g1 = view.from_sheet(QPointF(12, 12))
        assert c1.y() < h1.y()  # C_1 is above H_1
        assert g1.x() > h1.x()  # G_1 is to the right of H_1

    def test_round_trip(self, view: SheetView) -> None:
        p = view.to_sheet(view.from_sheet(QPointF(11.25, 12.5)))
        assert (p.x(), p.y()) == pytest.approx((11.25, 12.5))

    def test_mouse_moved_signal_reports_sheet_coordinates(self, view: SheetView, qtbot: QtBot) -> None:
        target = view.from_sheet(QPointF(11.5, 12.5)).toPoint()
        with qtbot.waitSignal(view.mouse_moved) as blocker:
            qtbot.mouseMove(view.viewport(), target)
        assert blocker.args is not None
        assert blocker.args == pytest.approx([11.5, 12.5], abs=2 / view.scale_factor())


class TestInitialView:
    def test_net_takes_half_the_screen_height(self, view: SheetView) -> None:
        screen = view.screen()
        assert screen is not None
        expected = zoom.clamp_scale(zoom.initial_scale(screen.geometry().height(), 4), view.zoom_limits())
        assert view.scale_factor() == pytest.approx(expected)

    def test_net_centered(self, view: SheetView) -> None:
        center = view.from_sheet(QPointF(11.5, 12))
        assert (center.x(), center.y()) == pytest.approx(
            (center_of_viewport(view).x(), center_of_viewport(view).y()), abs=2
        )


class TestZoom:
    def test_zoom_keeps_point_under_cursor(self, view: SheetView) -> None:
        pos = QPointF(200, 150)
        before = view.to_sheet(pos)
        assert view.zoom_by(1.5, pos)
        after = view.to_sheet(pos)
        tolerance = 1.5 / view.scale_factor()  # scroll positions are whole pixels
        assert (after.x(), after.y()) == pytest.approx((before.x(), before.y()), abs=tolerance)

    def test_zoom_clamped_to_limits(self, view: SheetView) -> None:
        low, high = view.zoom_limits()
        view.zoom_by(1e6, center_of_viewport(view))
        assert view.scale_factor() == pytest.approx(high)
        assert not view.zoom_by(2, center_of_viewport(view))
        view.zoom_by(1e-9, center_of_viewport(view))
        assert view.scale_factor() == pytest.approx(low)

    def test_wheel_inside_sheet_zooms(self, view: SheetView) -> None:
        before = view.scale_factor()
        wheel(view, view.from_sheet(QPointF(6, 6)), 1)
        assert view.scale_factor() == pytest.approx(before * zoom.WHEEL_STEP)
        wheel(view, view.from_sheet(QPointF(6, 6)), -2)
        assert view.scale_factor() == pytest.approx(before / zoom.WHEEL_STEP)

    def test_wheel_outside_sheet_does_not_zoom(self, view: SheetView) -> None:
        view.zoom_by(0.01, center_of_viewport(view))  # zoom out, so the main area around the sheet is visible
        before = view.scale_factor()
        outside = view.from_sheet(QPointF(4, 12))
        assert 0 <= outside.x() < view.viewport().width()
        wheel(view, outside, 1)
        assert view.scale_factor() == before


class TestPanning:
    def drag(self, view: SheetView, qtbot: QtBot, start: QPoint, end: QPoint) -> None:
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        qtbot.mouseMove(view.viewport(), end)
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)

    def test_drag_outside_net_moves_the_sheet_with_the_mouse(self, view: SheetView, qtbot: QtBot) -> None:
        start = view.from_sheet(QPointF(7, 7)).toPoint()
        end = start + QPoint(40, -30)
        self.drag(view, qtbot, start, end)
        moved = view.to_sheet(QPointF(end))
        assert (moved.x(), moved.y()) == pytest.approx((7, 7), abs=2 / view.scale_factor())

    def test_drag_on_net_does_not_pan(self, view: SheetView, qtbot: QtBot) -> None:
        start = view.from_sheet(QPointF(11.5, 12.5)).toPoint()
        self.drag(view, qtbot, start, start + QPoint(40, -30))
        stayed = view.to_sheet(QPointF(start))
        assert (stayed.x(), stayed.y()) == pytest.approx((11.5, 12.5), abs=2 / view.scale_factor())

    def test_pan_by(self, view: SheetView) -> None:
        before = view.to_sheet(QPointF(100, 100))
        view.pan_by(30, 0)
        after = view.to_sheet(QPointF(100, 100))
        assert after.x() == pytest.approx(before.x() + 30 / view.scale_factor(), abs=1e-9)


class TestSheet:
    def test_sheet_rect(self, view: SheetView) -> None:
        r = view.sheet_rect()
        assert (r.left(), r.top(), r.width(), r.height()) == (5, 5, 13, 14)

    def test_lower_max_zoom_zooms_out_to_it(self, view: SheetView) -> None:
        view.zoom_by(1e6, center_of_viewport(view))
        view.set_max_zoom(600)
        assert view.zoom_limits()[1] == 600
        assert view.scale_factor() == pytest.approx(600)

    def test_a_smaller_net_can_zoom_out_less(self, view: SheetView) -> None:
        from cube_net.core.net import default_net

        view.set_net(default_net())
        low, _ = view.zoom_limits()
        screen = view.screen()
        assert screen is not None
        w, h = screen.geometry().width(), screen.geometry().height()
        assert max(3 * low / w, 4 * low / h) == pytest.approx(0.5)  # the default net is 3 x 4
        view.zoom_by(1e-9, center_of_viewport(view))
        assert view.scale_factor() == pytest.approx(low)

    def test_a_new_net_brings_the_zoom_within_its_limits(self, view: SheetView) -> None:
        from cube_net.core.net import default_net

        view.zoom_by(1e-9, center_of_viewport(view))  # as far out as the sheet allows, before there's a net
        before = view.scale_factor()
        view.set_net(default_net())
        assert view.scale_factor() > before
        assert view.scale_factor() == pytest.approx(view.zoom_limits()[0])


class TestNet:
    def test_set_net_adds_and_replaces_item(self, view: SheetView) -> None:
        from cube_net.core.net import default_net

        assert view.net_item() is None
        view.set_net(default_net())
        item = view.net_item()
        assert item is not None and item.scene() is view.scene()
        view.set_net(default_net())
        assert view.net_item() is item


class TestLeftPressed:
    def test_click_on_net_emits_left_pressed(self, view: SheetView, qtbot: QtBot) -> None:
        with qtbot.waitSignal(view.left_pressed) as blocker:
            qtbot.mousePress(
                view.viewport(), Qt.MouseButton.LeftButton, pos=view.from_sheet(QPointF(11.5, 12.5)).toPoint()
            )
        assert blocker.args == pytest.approx([11.5, 12.5], abs=2 / view.scale_factor())
        assert not view.is_panning()

    def test_click_outside_net_pans_unless_disabled(self, view: SheetView, qtbot: QtBot) -> None:
        pos = view.from_sheet(QPointF(7, 7)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert view.is_panning()
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        view.set_panning_enabled(False)
        with qtbot.waitSignal(view.left_pressed):
            qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()


class TestStaysInPlace:
    """When the view moves inside its window (a panel next to it grows), the sheet must not move on screen."""

    def test_sheet_stays_when_neighbour_widens(self, qtbot: QtBot) -> None:
        from PyQt6.QtWidgets import QHBoxLayout, QWidget

        window = QWidget()
        qtbot.addWidget(window)
        panel = QWidget(window)
        panel.setFixedWidth(50)
        view = SheetView(window)
        view.set_sheet(SHEET)
        layout = QHBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(panel)
        layout.addWidget(view)
        window.resize(900, 600)
        view.show_initial_view(NET)
        window.show()
        qtbot.waitExposed(window)

        def h1_in_window() -> QPoint:
            return view.viewport().mapTo(window, view.from_sheet(QPointF(11, 12)).toPoint())

        before, x = h1_in_window(), view.x()
        panel.setFixedWidth(130)  # the view moves 80 px to the right and gets narrower
        qtbot.waitUntil(lambda: view.x() == x + 80)
        assert h1_in_window() == before
        panel.setFixedWidth(50)  # and back
        qtbot.waitUntil(lambda: view.x() == x)
        assert h1_in_window() == before

    def test_moving_the_whole_window_moves_the_sheet_with_it(self, view: SheetView) -> None:
        before = view.to_sheet(QPointF(100, 100))
        view.window().move(view.window().pos() + QPoint(40, 30))
        after = view.to_sheet(QPointF(100, 100))
        assert (after.x(), after.y()) == pytest.approx((before.x(), before.y()))


class TestReleaseAndModifiers:
    def test_left_released_on_the_net(self, view: SheetView, qtbot: QtBot) -> None:
        pos = view.from_sheet(QPointF(11.5, 12.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        with qtbot.waitSignal(view.left_released) as blocker:
            qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert blocker.args == pytest.approx([11.5, 12.5], abs=2 / view.scale_factor())

    def test_no_left_released_after_panning(self, view: SheetView, qtbot: QtBot) -> None:
        pos = view.from_sheet(QPointF(7, 7)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        with qtbot.assertNotEmitted(view.left_released):
            qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)

    def test_a_click_where_a_press_pans_is_a_pan_click(self, view: SheetView, qtbot: QtBot) -> None:
        pos = view.from_sheet(QPointF(7, 7)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        with qtbot.waitSignal(view.pan_clicked) as blocker:
            qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert blocker.args == pytest.approx([7, 7], abs=2 / view.scale_factor())

    def test_a_drag_that_pans_is_no_click(self, view: SheetView, qtbot: QtBot) -> None:
        start = view.from_sheet(QPointF(7, 7)).toPoint()
        with qtbot.assertNotEmitted(view.pan_clicked):
            qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
            qtbot.mouseMove(view.viewport(), start + QPoint(40, -30))
            qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(40, -30))

    def test_press_modifiers(self, view: SheetView, qtbot: QtBot) -> None:
        pos = view.from_sheet(QPointF(11.5, 12.5)).toPoint()
        qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos)
        assert view.press_modifiers() & Qt.KeyboardModifier.ShiftModifier
        qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.press_modifiers() & Qt.KeyboardModifier.ShiftModifier


def test_changing_the_sheet_keeps_what_is_on_screen(view: SheetView) -> None:
    before = view.from_sheet(QPointF(11, 12))
    view.set_sheet(Box(Vec(1, 2), Vec(25, 22)))
    after = view.from_sheet(QPointF(11, 12))
    assert (after.x(), after.y()) == pytest.approx((before.x(), before.y()), abs=1.5)


class TestShift:
    def send(self, view: SheetView, kind: QEvent.Type, button: Qt.MouseButton, shift: bool) -> None:
        pos = QPointF(view.from_sheet(QPointF(7, 7)))
        modifier = Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
        QApplication.sendEvent(
            view.viewport(), QMouseEvent(kind, pos, view.viewport().mapToGlobal(pos), button, button, modifier)
        )

    def test_key_press_and_release(self, view: SheetView, qtbot: QtBot) -> None:
        assert not view.shift_held()
        with qtbot.waitSignal(view.shift_changed):
            qtbot.keyPress(view, Qt.Key.Key_Shift)
        assert view.shift_held()
        with qtbot.waitSignal(view.shift_changed):
            qtbot.keyRelease(view, Qt.Key.Key_Shift)
        assert not view.shift_held()

    def test_ctrl_is_tracked_too(self, view: SheetView, qtbot: QtBot) -> None:
        assert not view.ctrl_held()
        with qtbot.waitSignal(view.ctrl_changed), qtbot.assertNotEmitted(view.shift_changed):
            qtbot.keyPress(view, Qt.Key.Key_Control)
        assert view.ctrl_held()
        with qtbot.waitSignal(view.ctrl_changed):
            qtbot.keyRelease(view, Qt.Key.Key_Control)
        assert not view.ctrl_held()

    def test_read_while_the_mouse_is_over_it(
        self, view: SheetView, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A key the desktop takes for itself (GNOME's "Locate pointer" takes the left CTRL) sends no key events."""
        from cube_net.ui.sheet import sheet_view

        held = [Qt.KeyboardModifier.ControlModifier]

        class Desktop:
            @staticmethod
            def queryKeyboardModifiers() -> Qt.KeyboardModifier:
                return held[0]

        monkeypatch.setattr(sheet_view, "QGuiApplication", Desktop)
        view.activateWindow()
        qtbot.waitUntil(view.isActiveWindow)
        QApplication.sendEvent(view, QEvent(QEvent.Type.Enter))
        with qtbot.waitSignal(view.ctrl_changed, timeout=sheet_view.MODIFIER_POLL_MS * 10):
            pass
        assert view.ctrl_held()
        held[0] = Qt.KeyboardModifier.NoModifier
        with qtbot.waitSignal(view.ctrl_changed, timeout=sheet_view.MODIFIER_POLL_MS * 10):
            pass
        assert not view.ctrl_held()
        QApplication.sendEvent(view, QEvent(QEvent.Type.Leave))
        held[0] = Qt.KeyboardModifier.ControlModifier
        with qtbot.assertNotEmitted(view.ctrl_changed):
            qtbot.wait(sheet_view.MODIFIER_POLL_MS * 4)  # not read while the mouse is elsewhere

    def test_whichever_widget_has_the_focus(self, view: SheetView, qtbot: QtBot) -> None:
        from PyQt6.QtWidgets import QSpinBox

        other = QSpinBox()  # say, the target area on the instrument panel
        qtbot.addWidget(other)
        with qtbot.waitSignal(view.ctrl_changed):
            qtbot.keyPress(other, Qt.Key.Key_Control)
        assert view.ctrl_held()
        with qtbot.waitSignal(view.shift_changed):
            qtbot.keyPress(other, Qt.Key.Key_Shift)
        assert view.shift_held()
        qtbot.keyRelease(other, Qt.Key.Key_Control)
        qtbot.keyRelease(other, Qt.Key.Key_Shift)
        assert not view.ctrl_held() and not view.shift_held()

    def test_other_keys_do_not_count(self, view: SheetView, qtbot: QtBot) -> None:
        with qtbot.assertNotEmitted(view.shift_changed):
            qtbot.keyPress(view, Qt.Key.Key_A)
            qtbot.keyRelease(view, Qt.Key.Key_A)

    def test_the_mouse_tells_too(self, view: SheetView) -> None:
        """A key release can get lost (the window wasn't active then): the next mouse move puts it right."""
        self.send(view, QEvent.Type.MouseMove, Qt.MouseButton.NoButton, True)
        assert view.shift_held()
        self.send(view, QEvent.Type.MouseMove, Qt.MouseButton.NoButton, False)
        assert not view.shift_held()

    def test_known_before_the_press_is_reported(self, view: SheetView, qtbot: QtBot) -> None:
        seen: list[bool] = []
        view.set_panning_enabled(False)
        view.left_pressed.connect(lambda _x, _y: seen.append(view.shift_held()))
        self.send(view, QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton, True)
        assert seen == [True]


class TestFixed:
    def test_shows_the_box_in_the_middle_and_keeps_its_zoom(self, qtbot: QtBot) -> None:
        view = SheetView()
        qtbot.addWidget(view)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setFixedSize(400, 300)
        view.set_sheet(Box(Vec(0, 0), Vec(20, 20)))
        view.show_fixed(Box(Vec(8, 8), Vec(12, 11)), 1.0)
        view.show()
        qtbot.waitExposed(view)
        assert view.scale_factor() == pytest.approx(100)  # 4 x 3 units in 400 x 300 px
        middle = view.to_sheet(QPointF(view.viewport().width() / 2, view.viewport().height() / 2))
        assert (middle.x(), middle.y()) == (pytest.approx(10, abs=0.02), pytest.approx(9.5, abs=0.02))
        assert not view.zoom_by(2, QPointF(10, 10))  # no zooming


def test_a_view_that_does_not_follow_the_keyboard(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QSpinBox

    view = SheetView(follow_keyboard=False)
    qtbot.addWidget(view)
    other = QSpinBox()
    qtbot.addWidget(other)
    with qtbot.assertNotEmitted(view.ctrl_changed):
        qtbot.keyPress(other, Qt.Key.Key_Control)
        qtbot.keyRelease(other, Qt.Key.Key_Control)
    assert not view.ctrl_held()


class TestRightPressed:
    def test_anywhere_on_the_sheet(self, view: SheetView, qtbot: QtBot) -> None:
        for x, y in ((11.5, 12.5), (7.0, 7.0)):  # on the net and off it: the tools decide what it means
            with qtbot.waitSignal(view.right_pressed) as blocker, qtbot.assertNotEmitted(view.left_pressed):
                qtbot.mousePress(
                    view.viewport(), Qt.MouseButton.RightButton, pos=view.from_sheet(QPointF(x, y)).toPoint()
                )
            assert blocker.args == pytest.approx([x, y], abs=2 / view.scale_factor())
            assert not view.is_panning()
            qtbot.mouseRelease(view.viewport(), Qt.MouseButton.RightButton)

    def test_not_while_the_sheet_is_dragged(self, view: SheetView, qtbot: QtBot) -> None:
        pos = view.from_sheet(QPointF(7, 7)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert view.is_panning()
        with qtbot.assertNotEmitted(view.right_pressed):
            qtbot.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=pos)
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)


class TestFollowCursor:
    """While a modal window keeps the mouse's moves from the sheet, the view reads where the mouse is."""

    def test_tells_the_moves_over_the_sheet(
        self, view: SheetView, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PyQt6.QtWidgets import QWidget

        viewport = view.viewport()
        assert viewport is not None
        modal = QWidget()
        qtbot.addWidget(modal)
        modal.setGeometry(viewport.mapToGlobal(QPointF(0, 0).toPoint()).x(), 0, 1, 1)  # out of the way
        where = [viewport.mapToGlobal(view.from_sheet(QPointF(11.5, 12.5)).toPoint())]
        monkeypatch.setattr(view, "cursor_position", lambda: where[0])
        moves: list[tuple[float, float]] = []
        left: list[bool] = []
        view.mouse_moved.connect(lambda x, y: moves.append((x, y)))
        view.mouse_left.connect(lambda: left.append(True))
        view.follow_cursor(modal)
        assert moves[-1] == pytest.approx((11.5, 12.5), abs=2 / view.scale_factor())
        view.follow_tick()
        assert len(moves) == 1  # it didn't move: nothing to tell
        where[0] = viewport.mapToGlobal(view.from_sheet(QPointF(10.0, 13.0)).toPoint())
        view.follow_tick()
        assert moves[-1] == pytest.approx((10.0, 13.0), abs=2 / view.scale_factor())
        where[0] = viewport.mapToGlobal(QPointF(-50, -50).toPoint())  # off the sheet
        view.follow_tick()
        assert left == [True]
        view.follow_cursor(None)
        where[0] = viewport.mapToGlobal(view.from_sheet(QPointF(11.5, 12.5)).toPoint())
        qtbot.wait(100)
        assert len(moves) == 2  # stopped: the real moves come again

    def test_over_the_window_itself_is_off_the_sheet(
        self, view: SheetView, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Told by the window's own Enter and Leave, not by its geometry: on Wayland, an application doesn't know where
        its windows are (Qt's idea of the window's place may be elsewhere, here: right over the mouse's spot)."""
        from PyQt6.QtCore import QEvent, QRect
        from PyQt6.QtWidgets import QApplication, QWidget

        viewport = view.viewport()
        assert viewport is not None
        spot = viewport.mapToGlobal(view.from_sheet(QPointF(11.5, 12.5)).toPoint())
        modal = QWidget()
        qtbot.addWidget(modal)
        modal.setGeometry(QRect(spot.x() - 20, spot.y() - 20, 40, 40))  # where Qt thinks it is: no matter
        monkeypatch.setattr(view, "cursor_position", lambda: spot)
        moves: list[tuple[float, float]] = []
        left: list[bool] = []
        view.mouse_moved.connect(lambda x, y: moves.append((x, y)))
        view.mouse_left.connect(lambda: left.append(True))
        view.follow_cursor(modal)
        assert len(moves) == 1  # the mouse isn't in the window: it's on the sheet
        QApplication.sendEvent(modal, QEvent(QEvent.Type.Enter))
        assert left == [True]  # in the window: off the sheet at once
        view.follow_tick()
        assert len(moves) == 1  # and its position there means nothing to the sheet
        QApplication.sendEvent(modal, QEvent(QEvent.Type.Leave))
        assert len(moves) == 1  # not at the very moment of leaving: the position may still be the window's
        view.follow_tick()
        assert len(moves) == 2  # the next reading
        view.follow_cursor(None)
        QApplication.sendEvent(modal, QEvent(QEvent.Type.Enter))
        assert left == [True]  # not followed any more


def test_a_view_with_its_own_look(view: SheetView, monkeypatch: pytest.MonkeyPatch) -> None:
    """Its painting and its mouse are handled in its look; everything else keeps the one in place."""
    from dataclasses import replace

    from cube_net.core.body import CUBE
    from cube_net.ui.sheet import net_style
    from cube_net.ui.style import DEFAULT_STYLE, Look

    assert view.look() is None
    seen: list[float] = []
    monkeypatch.setattr(view, "mouseMoveEvent", lambda _event: seen.append(net_style.EDGE_WIDTH_PX))
    look = Look(replace(DEFAULT_STYLE, edge_width=1.5), CUBE.colors, CUBE)
    view.set_look(look)
    assert view.look() == look
    viewport = view.viewport()
    assert viewport is not None
    nothing = Qt.MouseButton.NoButton
    move = QMouseEvent(
        QEvent.Type.MouseMove, QPointF(5, 5), QPointF(5, 5), nothing, nothing, Qt.KeyboardModifier.NoModifier
    )
    QApplication.sendEvent(viewport, move)
    assert seen == [1.5]
    assert DEFAULT_STYLE.edge_width == net_style.EDGE_WIDTH_PX


def test_the_place_shown_again_in_another_view(view: SheetView, qtbot: QtBot) -> None:
    view.zoom_by(1.5, QPointF(100, 100))
    view.pan_by(37, -21)
    place = view.place()
    other = SheetView()
    qtbot.addWidget(other)
    other.resize(640, 480)  # another size: the same point in the middle, the same zoom
    other.set_sheet(SHEET)
    other.show_initial_view(NET)
    other.show_place(place)  # (before it's shown: it waits, instead of the initial view)
    other.show()
    qtbot.waitExposed(other)
    again = other.place()
    assert again.scale == place.scale
    assert abs(again.x - place.x) < 1 / place.scale and abs(again.y - place.y) < 1 / place.scale


def test_a_place_zoomed_beyond_the_limits_is_brought_within(view: SheetView) -> None:
    from cube_net.ui.sheet.view_place import ViewPlace

    high = view.zoom_limits()[1]
    view.show_place(ViewPlace(11.5, 12.0, high * 10))
    assert view.scale_factor() == high


@pytest.mark.parametrize("x, y", [(3e7, 0.0), (-3e7, 3e7), (1e300, 1e300), (1e308, -1e308)])
def test_a_place_far_off_the_sheet_shows_its_edge(view: SheetView, x: float, y: float) -> None:
    """As a damaged setting's last view could have it: the view goes as far as its scroll bars do (it used to crash:
    too many pixels for Qt)."""
    from cube_net.ui.sheet.view_place import ViewPlace

    view.show_place(ViewPlace(x, y, 1.0))
    for bar, wanted in ((view.horizontalScrollBar(), x), (view.verticalScrollBar(), y)):
        assert bar is not None
        if wanted != 0:
            assert bar.value() in (bar.minimum(), bar.maximum())


def test_pan_by_ignores_what_isnt_a_number(view: SheetView) -> None:
    h = view.horizontalScrollBar()
    assert h is not None
    before = h.value()
    view.pan_by(float("nan"), float("inf"))
    assert h.value() == before


def test_the_place_stays_when_the_view_moves_in_its_window_afterwards(qtbot: QtBot) -> None:
    """As at a start: the place is shown, then the instrument panel left of the view gets wider (its buttons come);
    the sheet is where it was in the window when the place was taken."""
    from PyQt6.QtWidgets import QHBoxLayout, QWidget

    def window_with(panel_px: int) -> tuple[QWidget, QWidget, SheetView]:
        window = QWidget()
        qtbot.addWidget(window)
        window.resize(900, 600)
        layout = QHBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        panel = QWidget()
        panel.setFixedWidth(panel_px)
        view = SheetView()
        view.set_sheet(SHEET)
        view.show_initial_view(NET)
        layout.addWidget(panel)
        layout.addWidget(view)
        return window, panel, view

    first, _, view = window_with(90)
    first.show()
    qtbot.waitExposed(first)
    view.zoom_by(1.4, QPointF(150, 120))
    view.pan_by(-35, 18)
    place = view.place()
    in_window = view.viewport().mapTo(first, view.from_sheet(QPointF(11, 12)).toPoint())
    second, panel, again = window_with(60)
    second.show()
    qtbot.waitExposed(second)
    again.show_place(place)
    panel.setFixedWidth(90)
    qtbot.waitUntil(
        lambda: again.viewport().mapTo(second, QPoint(0, 0)).x() == view.viewport().mapTo(first, QPoint(0, 0)).x()
    )
    assert again.viewport().mapTo(second, again.from_sheet(QPointF(11, 12)).toPoint()) == in_window


def test_center_on_puts_the_point_in_the_middle_zoomed_out_by_the_rules(view: SheetView) -> None:
    view.pan_by(200, -100)
    view.zoom_by(4.0, center_of_viewport(view))
    view.center_on(QPointF(11.5, 12.25), NET)
    middle = view.from_sheet(QPointF(11.5, 12.25))
    assert abs(middle.x() - center_of_viewport(view).x()) <= 1 and abs(middle.y() - center_of_viewport(view).y()) <= 1
    width, height = view._screen_size()
    assert view.scale_factor() == zoom.zoom_limits(width, height, 3.0, 4.0, view.zoom_limits()[1])[0]  # NET's size


def test_center_on_a_smaller_net_than_the_views_zooms_out_less(view: SheetView) -> None:
    """A template's view has the whole template sheet for its limit; Center takes the template's own size."""
    small = Box(Vec(11, 12), Vec(12, 13))
    view.center_on(QPointF(11.5, 12.5), small)
    assert view.scale_factor() > view.zoom_limits()[0]
    width, height = view._screen_size()
    assert view.scale_factor() == zoom.zoom_limits(width, height, 1.0, 1.0, view.zoom_limits()[1])[0]
