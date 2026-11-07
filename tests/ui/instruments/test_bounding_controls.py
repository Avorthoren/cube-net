from collections.abc import Iterator
from fractions import Fraction as F

import pytest
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.core.bounding import BoundingRectangle
from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.instruments.bounding_controls import BLINK_INTERVAL_MS, BoundingControls, format_area
from cube_net.ui.sheet.bounding_item import BoundingItem

CORNERS = (Vec(0, 0), Vec(3, 0), Vec(3, 4), Vec(0, 4))


@pytest.fixture
def controls(qtbot: QtBot) -> Iterator[BoundingControls]:
    toolbar = QToolBar()  # kept alive by this generator until the test ends (Qt deletes children with it)
    qtbot.addWidget(toolbar)
    yield BoundingControls(toolbar, BoundingItem())


def rect(area: F) -> BoundingRectangle:
    return BoundingRectangle(area, CORNERS)


def test_format_area() -> None:
    assert format_area(F(12)) == "12.000"
    assert format_area(F(70999, 10000)) == "7.100"


def test_six_changes_per_second() -> None:
    assert BLINK_INTERVAL_MS == 167


def test_area_label_and_no_blinking_above_threshold(controls: BoundingControls) -> None:
    controls.update(rect(F(12)), F(71, 10))
    assert controls.label.text() == "Area\n12.000"
    assert not controls.success and not controls.blinking
    assert controls.label.styleSheet() == ""


def test_equal_to_threshold_is_not_success(controls: BoundingControls) -> None:
    controls.update(rect(F(71, 10)), F(71, 10))
    assert not controls.success


def test_below_threshold_green_and_blinking(controls: BoundingControls, qtbot: QtBot) -> None:
    controls.update(rect(F(7)), F(71, 10))
    assert controls.success and controls.blinking
    assert palette.SUCCESS.name() in controls.label.styleSheet()
    button = controls.button
    assert button is not None
    looks = set()
    for _ in range(4):
        qtbot.wait(BLINK_INTERVAL_MS + 20)
        looks.add(button.styleSheet())
    assert len(looks) == 2  # regular and fully green, alternating
    controls.update(rect(F(12)), F(71, 10))  # back above: stop, regular look
    assert not controls.blinking and button.styleSheet() == ""


def test_toggle_shows_rectangle_on_item(controls: BoundingControls, qtbot: QtBot) -> None:
    item = controls._item
    controls.update(rect(F(7)), F(71, 10))
    assert item.corners() == ()  # hidden until turned on
    with qtbot.waitSignal(controls.toggled):
        controls.action.setChecked(True)
    assert item.corners() == CORNERS and item.success()
    controls.action.setChecked(False)
    assert item.corners() == ()
