import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication
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
