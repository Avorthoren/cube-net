import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
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
    v.set_net_hit_test(lambda x, y: 10 <= x <= 13 and 10 <= y <= 14)
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

    def test_new_sheet_clamps_zoom(self, view: SheetView) -> None:
        view.zoom_by(1e6, center_of_viewport(view))
        view.set_sheet(Box(Vec(0, 0), Vec(100, 100)))  # much bigger sheet: lower zoom-in limit
        assert view.scale_factor() == pytest.approx(view.zoom_limits()[1])
