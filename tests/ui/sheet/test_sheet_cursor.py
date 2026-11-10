from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from pytestqt.qtbot import QtBot

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import MainWindow
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cursors import CursorKind


def make(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.record_session = False
    window = MainWindow(settings=settings, session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def shown(window: MainWindow) -> Qt.CursorShape:
    viewport = window.sheet_view.viewport()
    assert viewport is not None
    return viewport.cursor().shape()


def test_follows_the_mouse(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.mouse_moved.emit(10 + h, 12.5)
    assert window.sheet_cursor.kind() is CursorKind.SCISSORS
    assert shown(window) == Qt.CursorShape.BitmapCursor
    view.mouse_moved.emit(11.5, 12.5)
    assert window.sheet_cursor.kind() is CursorKind.ARROW
    assert shown(window) == Qt.CursorShape.ArrowCursor


def test_follows_a_change_without_a_move(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.mouse_moved.emit(11.5, 13.5)
    assert window.sheet_cursor.kind() is CursorKind.ARROW  # DEFAULT: nothing to click inside a face
    view.left_pressed.emit(11.5, 14 - h)  # the mouse is elsewhere when the line starts
    view.mouse_moved.emit(11.5, 13.5)
    assert window.sheet_cursor.kind() is CursorKind.SCISSORS
    window.ruler_action.trigger()
    assert window.sheet_cursor.kind() is CursorKind.ARROW
    window.ruler_action.trigger()
    assert window.sheet_cursor.kind() is CursorKind.SCISSORS


def rearranged(window: MainWindow) -> None:
    view = window.sheet_view
    h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - h)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - h, 13.5)
    view.left_pressed.emit(11.75, 10 + h)


class TestTooltip:
    """It really appears: half a second after the mouse came over the button, and it's gone as soon as it leaves."""

    def test_appears_after_half_a_second(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet.sheet_cursor import TOOLTIP_DELAY_MS

        window = make(qtbot, tmp_path)
        rearranged(window)
        window.sheet_view.mouse_moved.emit(11.75, 10.0)
        assert shown(window) == Qt.CursorShape.PointingHandCursor
        qtbot.wait(TOOLTIP_DELAY_MS - 200)
        assert not window.sheet_cursor.tooltip_label.isVisible()
        qtbot.waitUntil(window.sheet_cursor.tooltip_label.isVisible, timeout=1000)
        assert window.sheet_cursor.tooltip_label.text() == "Approve"

    def test_moving_over_the_button_does_not_start_over(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet.sheet_cursor import TOOLTIP_DELAY_MS

        window = make(qtbot, tmp_path)
        rearranged(window)
        view = window.sheet_view
        view.mouse_moved.emit(11.75, 10.0)
        for step in range(5):
            qtbot.wait(TOOLTIP_DELAY_MS // 5)
            view.mouse_moved.emit(11.75 + step / 1000, 10.0)
        qtbot.waitUntil(window.sheet_cursor.tooltip_label.isVisible, timeout=300)

    def test_gone_as_soon_as_the_mouse_leaves(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        rearranged(window)
        view = window.sheet_view
        view.mouse_moved.emit(11.75, 10.0)
        qtbot.waitUntil(window.sheet_cursor.tooltip_label.isVisible, timeout=1500)
        view.mouse_moved.emit(11.5, 12.5)
        assert not window.sheet_cursor.tooltip_label.isVisible()  # at once, not after a delay
        assert window.sheet_cursor.tooltip() == ""

    def test_none_if_the_mouse_leaves_before_it_appears(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet.sheet_cursor import TOOLTIP_DELAY_MS

        window = make(qtbot, tmp_path)
        rearranged(window)
        view = window.sheet_view
        view.mouse_moved.emit(11.75, 10.0)
        qtbot.wait(TOOLTIP_DELAY_MS // 2)
        view.mouse_moved.emit(11.5, 12.5)
        qtbot.wait(TOOLTIP_DELAY_MS)
        assert not window.sheet_cursor.tooltip_label.isVisible()

    def test_cancel_for_the_x(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)
        view.mouse_moved.emit(12.75, 13.0)
        qtbot.waitUntil(window.sheet_cursor.tooltip_label.isVisible, timeout=1500)
        assert window.sheet_cursor.tooltip_label.text() == "Cancel"

    def test_gone_when_the_mouse_leaves_the_sheet(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        rearranged(window)
        window.sheet_view.mouse_moved.emit(11.75, 10.0)
        qtbot.waitUntil(window.sheet_cursor.tooltip_label.isVisible, timeout=1500)
        window.sheet_view.mouse_left.emit()
        assert not window.sheet_cursor.tooltip_label.isVisible()  # at once, not after a delay


def test_the_hand_while_dragging_the_sheet(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtCore import QPointF

    window = make(qtbot, tmp_path)
    view = window.sheet_view
    viewport = view.viewport()
    assert viewport is not None
    start = view.from_sheet(QPointF(11.5, 12.5)).toPoint()
    qtbot.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
    assert view.is_panning()
    view.mouse_moved.emit(11.0, 12.0)
    assert shown(window) == Qt.CursorShape.ClosedHandCursor
    qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=start)


def test_tooltip_label_looks_like_a_tooltip(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtWidgets import QToolTip

    window = make(qtbot, tmp_path)
    label = window.sheet_cursor.tooltip_label
    assert label.windowFlags() & Qt.WindowType.ToolTip
    assert label.palette().color(label.backgroundRole()) == QToolTip.palette().color(label.backgroundRole())
    assert not label.isVisible()


def test_ctrl_turns_it_into_a_red_x_without_a_move(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - h)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - h, 13.5)
    view.mouse_moved.emit(11.5, 13.5)  # the inner point
    assert window.sheet_cursor.kind() is CursorKind.PENCIL
    qtbot.keyPress(view, Qt.Key.Key_Control)
    assert window.sheet_cursor.kind() is CursorKind.DELETE
    qtbot.keyRelease(view, Qt.Key.Key_Control)
    assert window.sheet_cursor.kind() is CursorKind.PENCIL
