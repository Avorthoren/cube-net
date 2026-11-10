# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Iterator
from pathlib import Path

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication, QPushButton
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Box, Vec
from cube_net.ui.session.session_log import SessionLog
from cube_net.ui.session.session_recorder import SessionRecorder, format_modifiers
from cube_net.ui.sheet.sheet_view import SheetView


@pytest.fixture
def recorder(tmp_path: Path, qapp: QApplication) -> Iterator[SessionRecorder]:
    rec = SessionRecorder(SessionLog(tmp_path / "s.log"))
    qapp.installEventFilter(rec)
    yield rec
    qapp.removeEventFilter(rec)
    rec.log.close()


@pytest.fixture
def view(qtbot: QtBot, recorder: SessionRecorder) -> SheetView:
    v = SheetView()
    qtbot.addWidget(v)
    v.resize(800, 600)
    v.set_sheet(Box(Vec(5, 5), Vec(18, 19)))
    v.set_press_claim(lambda x, y: 10 <= x <= 13 and 10 <= y <= 14)
    v.show_initial_view(Box(Vec(10, 10), Vec(13, 14)))
    v.show()
    qtbot.waitExposed(v)
    recorder.watch_sheet(v)
    return v


def entries(recorder: SessionRecorder) -> list[str]:
    """Logged lines without the time."""
    return [line.split(" ", 1)[1] for line in recorder.log.path.read_text().splitlines() if not line.startswith("#")]


def test_click_on_sheet_in_sheet_coordinates(view: SheetView, recorder: SessionRecorder, qtbot: QtBot) -> None:
    pos = view.from_sheet(QPointF(11.5, 12.25)).toPoint()
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos)
    lines = entries(recorder)
    assert lines[0].startswith("press L 11.5") and lines[0].endswith("[S]")
    assert lines[1].startswith("release L 11.5")
    assert len([line for line in lines if line.startswith("press")]) == 1  # recorded once, not per parent widget


def test_key_press_recorded_once_without_modifier_only_keys(recorder: SessionRecorder, qtbot: QtBot) -> None:
    button = QPushButton("OK")
    qtbot.addWidget(button)
    qtbot.keyClick(button, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert entries(recorder) == ["key Ctrl+Z"]


def test_wheel_and_view_state(view: SheetView, recorder: SessionRecorder, qtbot: QtBot) -> None:
    pos = view.from_sheet(QPointF(11.5, 12.5))
    event = QWheelEvent(
        pos,
        QPointF(view.viewport().mapToGlobal(pos.toPoint())),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(view.viewport(), event)
    qtbot.wait(10)  # the view state is recorded after the view has handled the event
    lines = entries(recorder)
    assert lines[0] == "wheel +1 11.500,12.500"
    assert lines[1].startswith(f"view {view.scale_factor():.3f} ")


def test_view_recorded_only_when_changed(view: SheetView, recorder: SessionRecorder) -> None:
    recorder.record_view()
    recorder.record_view()
    assert len([line for line in entries(recorder) if line.startswith("view")]) == 1


def test_drag_on_sheet(view: SheetView, recorder: SessionRecorder, qtbot: QtBot) -> None:
    start = view.from_sheet(QPointF(7, 7)).toPoint()
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    view.viewport().mouseMoveEvent  # noqa: B018  (QTest moves carry no buttons; send a real one)

    move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(start + QPoint(20, 0)),
        QPointF(view.viewport().mapToGlobal(start + QPoint(20, 0))),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(view.viewport(), move)
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(20, 0))
    kinds = [line.split()[0] for line in entries(recorder)]
    assert kinds[:3] == ["press", "drag", "release"]


def test_widget_outside_sheet(recorder: SessionRecorder, qtbot: QtBot) -> None:
    button = QPushButton("Apply")
    qtbot.addWidget(button)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton, pos=QPoint(3, 4))
    assert entries(recorder)[0] == 'press L QPushButton"Apply" 3,4'


def test_note(recorder: SessionRecorder) -> None:
    recorder.note("net", "default")
    assert entries(recorder) == ["net default"]


def test_format_modifiers() -> None:
    assert format_modifiers(Qt.KeyboardModifier.NoModifier) == []
    mods = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
    assert format_modifiers(mods) == ["[CS]"]


def test_shift_is_on_the_drag_lines(view: SheetView, recorder: SessionRecorder, qtbot: QtBot) -> None:
    start = view.from_sheet(QPointF(7, 7)).toPoint()
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(start + QPoint(20, 0)),
        QPointF(view.viewport().mapToGlobal(start + QPoint(20, 0))),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier,
    )
    QApplication.sendEvent(view.viewport(), move)
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(20, 0))
    drag = next(line for line in entries(recorder) if line.startswith("drag"))
    assert drag.endswith(" [S]")
