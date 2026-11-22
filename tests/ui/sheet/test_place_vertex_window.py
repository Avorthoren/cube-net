# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit
from pytestqt.qtbot import QtBot

from cube_net.core.cutting.placement import Action, Constraint, LineKind, Placement, Problem
from cube_net.core.geometry import Vec
from cube_net.core.origin import Origin
from cube_net.ui.sheet.coordinates_text import MAX_DIGITS
from cube_net.ui.sheet.place_vertex_window import PlaceVertexWindow, problem_text

FREE = Placement(Action.ADD, Vec(F(58, 5), F(68, 5)), Constraint.free())
SLANTED = Placement(Action.MOVE, Vec(F(23, 2), 11), Constraint(LineKind.EDGE, Vec(10, 10), Vec(13, 12)), 0)
HORIZONTAL = Placement(Action.START, Vec(F(23, 2), 14), Constraint(LineKind.EDGE, Vec(11, 14), Vec(12, 14)))


class Placed:
    """Stands for the cut tool: says `answer` and remembers where it was asked to place."""

    def __init__(self, answer: Problem | None = None) -> None:
        self.answer = answer
        self.asked: list[Vec] = []

    def __call__(self, p: Vec) -> Problem | None:
        self.asked.append(p)
        return self.answer


def make(qtbot: QtBot, placement: Placement, placed: Placed | None = None) -> PlaceVertexWindow:
    window = PlaceVertexWindow(placement, placed or Placed())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    return window


def texts(window: PlaceVertexWindow) -> list[str]:
    return [f"{row.numerator.text()}/{row.denominator.text()} {row.worth.text()}" for row in (window.y, window.x)]


def type_into(qtbot: QtBot, field: QLineEdit, text: str) -> None:
    field.setFocus()
    field.selectAll()
    qtbot.keyClicks(field, text)


def test_where_the_point_would_have_gone(qtbot: QtBot) -> None:
    window = make(qtbot, FREE)
    assert texts(window) == ["68/5 = 13.600", "58/5 = 11.600"]
    assert window.windowTitle() == "Place a vertex"


def test_free_both_typed_y_first_selected(qtbot: QtBot) -> None:
    window = make(qtbot, FREE)
    assert all(f.isEnabled() for f in (window.x.numerator, window.x.denominator, window.y.numerator))
    qtbot.waitUntil(window.y.numerator.hasFocus)
    assert window.y.numerator.selectedText() == "68"


def test_on_a_slanted_line_either_is_typed_and_the_other_follows_at_once(qtbot: QtBot) -> None:
    window = make(qtbot, SLANTED)
    assert all(f.isEnabled() for row in (window.x, window.y) for f in (row.numerator, row.denominator))
    type_into(qtbot, window.y.numerator, "31")
    assert texts(window) == ["31/1 = 31.000", "83/2 = 41.500"]  # while typing: x = 10 + (31 - 10) * 3/2
    type_into(qtbot, window.y.denominator, "3")
    assert texts(window) == ["31/3 ≈ 10.333", "21/2 = 10.500"]
    type_into(qtbot, window.x.numerator, "11")
    type_into(qtbot, window.x.denominator, "1")
    assert texts(window) == ["32/3 ≈ 10.667", "11/1 = 11.000"]  # now y follows x: 10 + (11 - 10) * 2/3


def test_half_typed_leaves_the_other_as_it_was(qtbot: QtBot) -> None:
    window = make(qtbot, SLANTED)
    type_into(qtbot, window.y.denominator, "0")
    assert window.x.numerator.text() == "23" and window.x.denominator.text() == "2"
    type_into(qtbot, window.x.numerator, "-")
    assert window.y.numerator.text() == "11"


def test_on_a_vertical_line_x_is_fixed(qtbot: QtBot) -> None:
    vertical = Placement(Action.ADD, Vec(10, F(25, 2)), Constraint(LineKind.EDGE, Vec(10, 12), Vec(10, 13)))
    window = make(qtbot, vertical)
    assert not window.x.numerator.isEnabled() and not window.x.denominator.isEnabled()
    type_into(qtbot, window.y.numerator, "51")
    type_into(qtbot, window.y.denominator, "4")
    assert texts(window) == ["51/4 = 12.750", "10/1 = 10.000"]


def test_on_a_horizontal_line_x_typed_and_first(qtbot: QtBot) -> None:
    window = make(qtbot, HORIZONTAL)
    assert not window.y.numerator.isEnabled() and window.x.numerator.isEnabled()
    qtbot.waitUntil(window.x.numerator.hasFocus)
    assert window.x.numerator.selectedText() == "23"


class TestFields:
    def test_at_most_10_digits_typed(self, qtbot: QtBot) -> None:
        window = make(qtbot, FREE)
        type_into(qtbot, window.y.numerator, "1" * (MAX_DIGITS + 2))
        assert window.y.numerator.text() == "1" * MAX_DIGITS

    def test_a_longer_one_can_be_shortened_and_signed(self, qtbot: QtBot) -> None:
        long = "9" * (MAX_DIGITS + 3)
        window = make(qtbot, Placement(Action.ADD, Vec(F(int(long)), F(1, 3)), Constraint.free()))
        field = window.x.numerator
        assert field.text() == long  # shown in full
        field.setFocus()
        field.end(False)
        qtbot.keyClick(field, Qt.Key.Key_9)
        assert field.text() == long  # no more digits
        qtbot.keyClick(field, Qt.Key.Key_Backspace)
        assert field.text() == long[:-1]  # shorter is fine
        field.home(False)
        qtbot.keyClick(field, Qt.Key.Key_Minus)
        assert field.text() == "-" + long[:-1]  # and a minus sign always

    def test_denominators_positive(self, qtbot: QtBot) -> None:
        window = make(qtbot, FREE)
        type_into(qtbot, window.y.denominator, "-3")
        assert window.y.denominator.text() == "3"  # no minus there
        type_into(qtbot, window.y.denominator, "0")
        assert window.y.worth.text() == ""  # not a number yet
        assert not window.y.denominator.hasAcceptableInput()

    def test_10_digits_fit_in_a_field(self, qtbot: QtBot) -> None:
        window = make(qtbot, FREE)
        for field in (window.y.numerator, window.y.denominator):
            digits = "1234567890"
            assert field.fontMetrics().horizontalAdvance(digits) < field.width() - 8


class TestPlace:
    def test_places_the_typed_point(self, qtbot: QtBot) -> None:
        placed = Placed()
        window = make(qtbot, SLANTED, placed)
        type_into(qtbot, window.x.numerator, "11")
        type_into(qtbot, window.x.denominator, "1")
        window.place_button.click()
        assert placed.asked == [Vec(11, F(32, 3))]  # from x, typed last
        assert window.result() == PlaceVertexWindow.DialogCode.Accepted

    def test_enter_places(self, qtbot: QtBot) -> None:
        placed = Placed()
        window = make(qtbot, FREE, placed)
        qtbot.waitUntil(window.y.numerator.hasFocus)
        qtbot.keyClick(window.y.numerator, Qt.Key.Key_Return)
        assert placed.asked == [FREE.position] and not window.isVisible()

    @pytest.mark.parametrize("problem", list(Problem))
    def test_says_why_and_stays(self, qtbot: QtBot, problem: Problem) -> None:
        window = make(qtbot, FREE, Placed(problem))
        window.place_button.click()
        assert window.isVisible() and window.message.isVisible()
        assert window.message.text() == problem_text(problem)

    def test_not_a_number_yet(self, qtbot: QtBot) -> None:
        placed = Placed()
        window = make(qtbot, FREE, placed)
        window.y.numerator.clear()
        window.place_button.click()
        assert placed.asked == [] and window.isVisible()
        assert window.message.text() == "Enter whole numbers, with denominators above 0."

    def test_escape_and_cancel_change_nothing(self, qtbot: QtBot) -> None:
        placed = Placed()
        window = make(qtbot, FREE, placed)
        qtbot.waitUntil(window.y.numerator.hasFocus)
        qtbot.keyClick(window.y.numerator, Qt.Key.Key_Escape)
        assert placed.asked == [] and window.result() == PlaceVertexWindow.DialogCode.Rejected
        other = make(qtbot, FREE, placed)
        other.cancel_button.click()
        assert placed.asked == [] and not other.isVisible()


def test_every_problem_has_its_words() -> None:
    from cube_net.core.cutting import LineProblem

    texts_ = {problem_text(problem) for problem in Problem}
    assert len(texts_) == len(Problem) and all(texts_)
    lines = {problem: problem_text(problem) for problem in LineProblem}
    assert all(lines.values())
    # The same words for the same situation: a point on the perimeter that isn't on a cut.
    assert lines.pop(LineProblem.ON_THE_PERIMETER) == problem_text(Problem.ON_PERIMETER)
    assert len(set(lines.values())) == len(lines) and not set(lines.values()) & texts_


class TestFromAMovedOrigin:
    """The coordinates are shown and typed from the origin; the point placed is the sheet's."""

    ORIGIN = Origin(Vec(11, 10))

    def make(self, qtbot: QtBot, placement: Placement, placed: Placed) -> PlaceVertexWindow:
        window = PlaceVertexWindow(placement, placed, origin=self.ORIGIN)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_free(self, qtbot: QtBot) -> None:
        placed = Placed()
        window = self.make(qtbot, FREE, placed)
        assert texts(window) == ["18/5 = 3.600", "3/5 = 0.600"]
        window.x.numerator.setText("1")
        window.x.denominator.setText("1")
        window.place_button.click()
        assert placed.asked == [Vec(12, F(68, 5))]

    def test_on_a_slanted_line_the_other_follows(self, qtbot: QtBot) -> None:
        placed = Placed()
        window = self.make(qtbot, SLANTED, placed)  # the edge (10, 10)-(13, 12): shown (-1, 0)-(2, 2)
        type_into(qtbot, window.x.numerator, "2")
        type_into(qtbot, window.x.denominator, "1")
        assert (window.y.numerator.text(), window.y.denominator.text()) == ("2", "1")
        window.place_button.click()
        assert placed.asked == [Vec(13, 12)]
