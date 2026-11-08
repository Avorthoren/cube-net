from fractions import Fraction as F

import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Box, Vec
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView


@pytest.fixture
def view(qtbot: QtBot) -> SheetView:
    v = SheetView()
    qtbot.addWidget(v)
    v.resize(800, 600)
    v.set_sheet(Box(Vec(5, 5), Vec(18, 19)))
    v.set_press_claim(lambda x, y: 10 <= x <= 13 and 10 <= y <= 14)
    v.show_initial_view(Box(Vec(10, 10), Vec(13, 14)))
    v.show()
    qtbot.waitExposed(v)
    return v


def at(view: SheetView, x: float, y: float) -> QPoint:
    return view.from_sheet(QPointF(x, y)).toPoint()


def test_inactive_by_default_and_clicks_ignored(view: SheetView, qtbot: QtBot) -> None:
    tool = RulerTool(view)
    assert not tool.active
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=at(view, 11.5, 12.5))
    assert tool.ruler.points == ()


def test_clicks_add_rounded_points_anywhere_on_the_sheet(view: SheetView, qtbot: QtBot) -> None:
    tool = RulerTool(view)
    tool.set_active(True)
    with qtbot.waitSignal(tool.point_added):
        qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=at(view, 11.5, 12.5))  # on the net
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=at(view, 7, 7))  # off the net: no panning
    points = tool.ruler.points
    assert len(points) == 2
    assert all((p.x * 1000).denominator == 1 and (p.y * 1000).denominator == 1 for p in points)
    assert float(points[1].x) == pytest.approx(7, abs=0.02) and float(points[1].y) == pytest.approx(7, abs=0.02)


def test_no_panning_while_active(view: SheetView, qtbot: QtBot) -> None:
    tool = RulerTool(view)
    tool.set_active(True)
    start = at(view, 7, 7)
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    assert not view.is_panning()
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    tool.set_active(False)
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    assert view.is_panning()
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start)


def test_click_outside_sheet_ignored(view: SheetView, qtbot: QtBot) -> None:
    tool = RulerTool(view)
    tool.set_active(True)
    view.left_pressed.emit(2.0, 2.0)  # the main area around the sheet
    assert tool.ruler.points == ()


def test_deactivating_forgets_points(view: SheetView) -> None:
    tool = RulerTool(view)
    tool.set_active(True)
    view.left_pressed.emit(11.0, 12.0)
    assert len(tool.ruler.points) == 1
    tool.set_active(False)
    assert tool.ruler.points == ()
    tool.set_active(True)
    assert tool.ruler.points == ()


def test_cursor_follows_mouse(view: SheetView) -> None:
    tool = RulerTool(view)
    tool.set_active(True)
    view.left_pressed.emit(11.0, 12.0)
    view.mouse_moved.emit(12.25, 13.5)
    assert tool.item._cursor == Vec(F(49, 4), F(27, 2))
    view.mouse_left.emit()
    assert tool.item._cursor is None


def test_item_area_has_label_room_at_current_zoom(view: SheetView) -> None:
    from cube_net.ui.sheet import ruler_style

    tool = RulerTool(view)
    tool.set_active(True)
    margin = ruler_style.LABEL_REACH_PX / view.scale_factor()
    assert tool.item.boundingRect() == view.sheet_rect().adjusted(-margin, -margin, margin, margin)
    view.zoom_by(2, QPointF(100, 100))  # zooming in: the same pixels are fewer units
    margin = ruler_style.LABEL_REACH_PX / view.scale_factor()
    assert tool.item.boundingRect() == view.sheet_rect().adjusted(-margin, -margin, margin, margin)


def test_total_length(view: SheetView, qtbot: QtBot) -> None:
    tool = RulerTool(view)
    tool.set_active(True)
    assert tool.total_length() is None  # nothing placed yet
    with qtbot.waitSignal(tool.points_changed):
        view.left_pressed.emit(11.0, 12.0)
    assert tool.total_length() == 0.0  # one point: no segment yet
    view.mouse_moved.emit(14.0, 16.0)  # the line to the mouse doesn't count
    assert tool.total_length() == 0.0
    view.left_pressed.emit(14.0, 16.0)  # 3-4-5
    view.left_pressed.emit(14.0, 17.0)
    assert tool.total_length() == pytest.approx(6.0)
    tool.set_active(False)
    assert tool.total_length() is None
