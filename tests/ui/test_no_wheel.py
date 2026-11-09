from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication, QScrollArea, QSpinBox, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.no_wheel import ignore_wheel


def wheel(target: QWidget, notches: int) -> None:
    pos = QPointF(target.width() / 2, target.height() / 2)
    event = QWheelEvent(
        pos,
        target.mapToGlobal(pos),
        QPoint(0, 0),
        QPoint(0, 120 * notches),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(target, event)


def test_a_plain_field_takes_the_wheel(qtbot: QtBot) -> None:
    """What the fields would do without it."""
    box = QSpinBox()
    qtbot.addWidget(box)
    box.show()
    wheel(box, 1)
    assert box.value() == 1


def test_the_field_ignores_it(qtbot: QtBot) -> None:
    box = QSpinBox()
    qtbot.addWidget(box)
    ignore_wheel([box], box)
    box.show()
    for target in (box, box.lineEdit()):
        assert target is not None
        wheel(target, 3)
    assert box.value() == 0


def test_what_is_behind_scrolls(qtbot: QtBot) -> None:
    area = QScrollArea()
    qtbot.addWidget(area)
    content = QWidget()
    layout = QVBoxLayout(content)
    boxes = [QSpinBox() for _ in range(40)]
    for box in boxes:
        layout.addWidget(box)
    area.setWidget(content)
    area.resize(200, 150)
    ignore_wheel(boxes, area)
    area.show()
    qtbot.waitExposed(area)
    bar = area.verticalScrollBar()
    assert bar is not None and bar.value() == 0
    wheel(boxes[0], -3)
    assert bar.value() > 0
    assert all(box.value() == 0 for box in boxes)
