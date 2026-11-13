# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from pytestqt.qtbot import QtBot

from cube_net.ui.settings_panel.style_tab import (
    CUTS_AND_FOLDS,
    FACE_COLORS,
    FACE_TILING,
    GRID,
    VERTICES,
    StyleTab,
)
from cube_net.ui.style import DEFAULT_STYLE, Style
from cube_net.ui.style.style import least_vertex_radius


def make(qtbot: QtBot) -> StyleTab:
    tab = StyleTab(DEFAULT_STYLE)
    qtbot.addWidget(tab)
    return tab


def test_sections_in_order(qtbot: QtBot) -> None:
    assert list(make(qtbot).sections) == [FACE_COLORS, FACE_TILING, CUTS_AND_FOLDS, VERTICES, GRID]


def test_it_shows_the_style(qtbot: QtBot) -> None:
    tab = make(qtbot)
    assert [f.color() for f in tab.face_fields] == list(DEFAULT_STYLE.face_colors)
    assert (tab.hatch_columns.value(), tab.hatch_rows.value()) == (10, 5)
    shown = (tab.dashes.value(), tab.edge_width.value(), tab.vertex_radius.value())
    assert shown == (DEFAULT_STYLE.dashes_per_edge, DEFAULT_STYLE.edge_width, DEFAULT_STYLE.vertex_radius)
    assert tab.grid_width.value() == 1.0
    assert tab.edge_width.suffix() == ""


@pytest.mark.parametrize(
    ("box", "low", "high"),
    [
        ("hatch_columns", 1, 30),
        ("hatch_rows", 1, 30),
        ("dashes", 1, 30),
        ("edge_width", 1, 15),
        ("vertex_radius", least_vertex_radius(DEFAULT_STYLE.edge_width), 30),  # 140% of the default edges across
        ("grid_width", 0, 5),
    ],
)
def test_ranges(qtbot: QtBot, box: str, low: float, high: float) -> None:
    field = getattr(make(qtbot), box)
    assert (field.minimum(), field.maximum()) == (low, high)


def test_every_change_is_told(qtbot: QtBot) -> None:
    tab = make(qtbot)
    seen: list[Style] = []
    tab.style_changed.connect(seen.append)
    tab.hatch_rows.setValue(7)
    tab.dashes.setValue(3)
    tab.grid_width.setValue(0)
    assert [s.hatch_rows for s in seen] == [7, 7, 7]
    assert seen[-1].dashes_per_edge == 3 and seen[-1].grid_width == 0
    assert tab.grid_swatch.line_width() == 0


def test_restore_puts_back_just_its_section(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = make(qtbot)
    tab.edge_width.setValue(9)
    tab.dashes.setValue(3)
    tab.vertex_radius.setValue(20)
    monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda *_: True)
    tab.sections[CUTS_AND_FOLDS].restore_button.click()
    assert tab.style().edge_width == DEFAULT_STYLE.edge_width
    assert tab.style().dashes_per_edge == DEFAULT_STYLE.dashes_per_edge
    assert tab.edge_width.value() == DEFAULT_STYLE.edge_width
    assert tab.style().vertex_radius == 20


def test_restore_face_colors(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = make(qtbot)
    tab.face_fields[2].edit.setText("")
    qtbot.keyClicks(tab.face_fields[2].edit, "000000")
    assert tab.style().face_colors[2] == "#000000"
    monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda *_: True)
    tab.sections[FACE_COLORS].restore_button.click()
    assert tab.style().face_colors == DEFAULT_STYLE.face_colors
    assert tab.face_swatches[2].color().name().upper() == DEFAULT_STYLE.face_colors[2]


def test_units_are_outside_the_fields(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QLabel

    tab = make(qtbot)
    tab.show()
    for box in (tab.edge_width, tab.vertex_radius, tab.grid_width):
        assert box.suffix() == ""
        right = box.mapTo(tab, box.rect().topRight()).x()
        units = [
            label
            for label in tab.findChildren(QLabel)
            if label.text() == "px"
            and abs(label.mapTo(tab, label.rect().center()).y() - box.mapTo(tab, box.rect().center()).y()) < 3
        ]
        assert len(units) == 1 and units[0].mapTo(tab, units[0].rect().topLeft()).x() > right


def test_cuts_and_folds_fields_start_at_the_same_place(qtbot: QtBot) -> None:
    tab = make(qtbot)
    tab.show()
    assert (
        tab.dashes.mapTo(tab, tab.dashes.rect().topLeft()).x()
        == tab.edge_width.mapTo(tab, tab.edge_width.rect().topLeft()).x()
    )


def test_the_hash_is_right_next_to_the_digits(qtbot: QtBot) -> None:
    tab = make(qtbot)
    tab.show()
    for field in (*tab.face_fields, tab.grid_color):
        assert 0 <= field.edit.x() - (field.hash.x() + field.hash.width()) <= 4


def test_a_thin_line_between_sections(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QFrame

    tab = make(qtbot)
    tab.show()
    sections = list(tab.sections.values())
    assert len(tab.separators) == len(sections) - 1
    for line, above, below in zip(tab.separators, sections, sections[1:], strict=False):
        assert line.frameShape() == QFrame.Shape.HLine
        assert above.geometry().bottom() < line.geometry().top() <= line.geometry().bottom() < below.geometry().top()


def test_vertices_grow_with_thicker_edges_just_as_much_as_needed(qtbot: QtBot) -> None:
    tab = make(qtbot)
    seen: list[Style] = []
    tab.style_changed.connect(seen.append)
    tab.edge_width.setValue(15)
    assert seen[-1].edge_width == 15 and seen[-1].vertex_radius == 10.5  # 140% of 15 across
    assert tab.vertex_radius.value() == 10.5 and tab.vertex_radius.minimum() == 10.5
    tab.edge_width.setValue(5)
    assert tab.style().vertex_radius == 10.5  # thinner edges don't shrink them
    assert tab.vertex_radius.minimum() == 3.5


def test_vertices_cant_be_made_smaller_than_the_edges_allow(qtbot: QtBot) -> None:
    tab = make(qtbot)
    least = least_vertex_radius(DEFAULT_STYLE.edge_width)
    tab.vertex_radius.setValue(least + 0.5)
    assert tab.style().vertex_radius == least + 0.5
    tab.vertex_radius.setValue(least - 0.5)
    assert tab.vertex_radius.value() == least and tab.style().vertex_radius == least


def test_restoring_the_vertices_keeps_them_large_enough(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = make(qtbot)
    tab.edge_width.setValue(15)
    monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda *_: True)
    tab.sections[VERTICES].restore_button.click()
    assert tab.style().vertex_radius == 10.5  # the default is too small for these edges
