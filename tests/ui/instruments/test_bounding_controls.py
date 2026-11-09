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


def test_blinking_does_not_change_the_size_of_the_button(qtbot: QtBot) -> None:
    """The panel is as wide as its widest item: a button that changes its size makes the panel change its width."""
    from PyQt6.QtWidgets import QMainWindow

    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QToolBar(window)
    window.addToolBar(toolbar)
    controls = BoundingControls(toolbar, BoundingItem())
    window.show()
    qtbot.waitExposed(window)
    assert controls.button is not None
    controls.update(rect(F(5)), F(4))  # not below the threshold: the label has its text, nothing blinks
    regular = controls.button.sizeHint()
    width = toolbar.sizeHint().width()
    controls.update(rect(F(5)), F(6))
    sizes = set()
    for _ in range(4):
        qtbot.wait(BLINK_INTERVAL_MS + 20)
        sizes.add((controls.button.size().width(), controls.button.size().height(), toolbar.sizeHint().width()))
    assert sizes == {(regular.width(), regular.height(), width)}


def test_target_area(controls: BoundingControls, qtbot: QtBot) -> None:
    controls.set_target(F(71, 10))
    assert controls.target.text() == "7.100"
    with qtbot.waitSignal(controls.target_changed) as blocker:
        controls.target.setValue(6.789)
    assert blocker.args == [F(6789, 1000)]


def test_set_target_tells_nobody(controls: BoundingControls, qtbot: QtBot) -> None:
    with qtbot.assertNotEmitted(controls.target_changed):
        controls.set_target(F(5))


class TestBlinkSwitchedOff:
    def green(self, controls: BoundingControls) -> bool:
        assert controls.button is not None
        return palette.SUCCESS.name() in controls.button.styleSheet()

    def test_steadily_green_on_success(self, controls: BoundingControls, qtbot: QtBot) -> None:
        controls.set_blink_enabled(False)
        controls.update(rect(F(5)), F(6))
        assert controls.success and not controls.blinking
        for _ in range(3):
            assert self.green(controls)
            qtbot.wait(BLINK_INTERVAL_MS + 20)

    def test_regular_without_success(self, controls: BoundingControls) -> None:
        controls.set_blink_enabled(False)
        controls.update(rect(F(5)), F(6))
        controls.update(rect(F(7)), F(6))
        assert not self.green(controls)

    def test_switching_it_while_successful(self, controls: BoundingControls) -> None:
        controls.update(rect(F(5)), F(6))
        assert controls.blinking
        controls.set_blink_enabled(False)
        assert not controls.blinking and self.green(controls)
        controls.set_blink_enabled(True)
        assert controls.blinking

    def test_switching_it_without_success_changes_nothing(self, controls: BoundingControls) -> None:
        controls.update(rect(F(7)), F(6))
        controls.set_blink_enabled(False)
        controls.set_blink_enabled(True)
        assert not controls.blinking and not self.green(controls)
