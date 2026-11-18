# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Style tab: how the net and the sheet look (docs/idea.txt, settings). Every change takes effect at once.

All of it belongs to the open document (docs/template_plan.md, §8.3): the face colours to the project (one row per face
of its body; a template has its faces' own, given on the sheet), the rest to the project or the template. Restore
default brings back the body's colours, and the style files' values for the rest."""

from collections.abc import Sequence
from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from cube_net.core.style import DASHES_RANGE, EDGE_WIDTH_RANGE, GRID_WIDTH_RANGE, TILING_RANGE, VERTEX_RADIUS_RANGE
from cube_net.ui.decimal_box import DecimalBox
from cube_net.ui.i18n import bind, tr
from cube_net.ui.settings_panel.color_field import ColorField
from cube_net.ui.settings_panel.section import Section
from cube_net.ui.settings_panel.swatches import ColorSwatch, GridSwatch
from cube_net.ui.style import DEFAULT_STYLE, Style, fitted
from cube_net.ui.style.default_style import least_vertex_radius

# Between the two numbers of the tiling: the multiplication sign.
BY_SIGN = chr(0x00D7)

# The unit shown after a field in pixels.
PIXELS = "px"

# Shown after the tiling and the dashes.
PER_UNIT = "per unit"

# Sizes in pixels have this many decimals.
PIXEL_DECIMALS = 1

# The tiling and the dashes (per unit) have this many decimals.
COUNT_DECIMALS = 2

# The names of the sections, as shown (and as the confirmation names them).
FACE_COLORS = "Faces colors"
FACE_TILING = "Faces tiling"
CUTS_AND_FOLDS = "Cuts and folds"
VERTICES = "Vertices"
GRID = "Grid"

# Which values of the style each section restores (the face colours are the project's).
SECTION_FIELDS = {
    FACE_TILING: ("hatch_columns", "hatch_rows"),
    CUTS_AND_FOLDS: ("dashes_per_unit", "edge_width"),
    VERTICES: ("vertex_radius",),
    GRID: ("grid_color", "grid_width"),
}


def _count_box(allowed: tuple[float, float], parent: QWidget) -> DecimalBox:
    """A positive number of rectangles or dashes per unit: decimals allowed."""
    return DecimalBox(COUNT_DECIMALS, allowed, 1.0, parent)


def _pixels_box(allowed: tuple[float, float], parent: QWidget) -> DecimalBox:
    return DecimalBox(PIXEL_DECIMALS, allowed, 0.5, parent)


def _px(parent: QWidget) -> QLabel:
    """The unit, after a field in pixels."""
    label = QLabel(parent)
    bind(label, label.setText, PIXELS)
    return label


def _per_unit(parent: QWidget) -> QLabel:
    """After the tiling and the dashes: they're counted per unit of the grid."""
    label = QLabel(parent)
    bind(label, label.setText, PER_UNIT)
    return label


class StyleTab(QWidget):
    # The user changed the style.
    style_changed = pyqtSignal(object)

    # The user changed the project's face colours (a tuple of "#RRGGBB", face k: [k - 1]).
    face_colors_changed = pyqtSignal(object)

    def __init__(self, style: Style, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._style = style
        self._face_colors: tuple[str, ...] = ()
        self._default_face_colors: tuple[str, ...] = ()
        self._filling = False
        layout = QVBoxLayout(self)
        self.sections: dict[str, Section] = {}
        self.separators: list[QFrame] = []

        self._colors_section = self._section(FACE_COLORS)
        self._face_rows = QWidget(self._colors_section)
        self._face_rows_layout = QVBoxLayout(self._face_rows)
        self._face_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._colors_section.body.addWidget(self._face_rows)
        self.face_swatches: list[ColorSwatch] = []
        self.face_fields: list[ColorField] = []
        self.face_numbers: list[QLabel] = []

        tiling = self._section(FACE_TILING)
        self.hatch_columns, self.hatch_rows = _count_box(TILING_RANGE, tiling), _count_box(TILING_RANGE, tiling)
        tiling.add_row(self.hatch_columns, QLabel(BY_SIGN, tiling), self.hatch_rows, _per_unit(tiling))

        cuts = self._section(CUTS_AND_FOLDS)
        self.dashes = _count_box(DASHES_RANGE, cuts)
        self.edge_width = _pixels_box(EDGE_WIDTH_RANGE, cuts)
        cuts.add_labelled_row("Dashes", self.dashes, _per_unit(cuts))
        cuts.add_labelled_row("Thickness", self.edge_width, _px(cuts))

        vertices = self._section(VERTICES)
        self.vertex_radius = _pixels_box(VERTEX_RADIUS_RANGE, vertices)
        vertices.add_labelled_row("Radius", self.vertex_radius, _px(vertices))

        grid = self._section(GRID)
        self.grid_swatch = GridSwatch(style.grid_color, style.grid_width, grid)
        self.grid_color = ColorField(style.grid_color, grid)
        self.grid_width = _pixels_box(GRID_WIDTH_RANGE, grid)
        self.grid_color.changed.connect(lambda color: self._change(grid_color=color))
        grid.add_row(self.grid_swatch, self.grid_color, self.grid_width, _px(grid))
        layout.addStretch()

        self._fill(style)
        self.hatch_columns.valueChanged.connect(lambda v: self._change(hatch_columns=v))
        self.hatch_rows.valueChanged.connect(lambda v: self._change(hatch_rows=v))
        self.dashes.valueChanged.connect(lambda v: self._change(dashes_per_unit=v))
        self.edge_width.valueChanged.connect(lambda v: self._change(edge_width=v))
        self.vertex_radius.valueChanged.connect(lambda v: self._change(vertex_radius=v))
        self.grid_width.valueChanged.connect(lambda v: self._change(grid_width=v))

    def style(self) -> Style:
        return self._style

    def set_style(self, style: Style) -> None:
        """Show the open document's style (without taking that for a change by the user)."""
        self._style = style
        self._fill(style)

    def set_face_colors_shown(self, shown: bool) -> None:
        """Faces colors, and the line under it, shown or not (not while a template is made: its faces have their own
        colours, given on the sheet)."""
        self.sections[FACE_COLORS].setVisible(shown)
        self.separators[0].setVisible(shown)

    def face_colors(self) -> tuple[str, ...]:
        return self._face_colors

    def set_face_colors(self, colors: Sequence[str], defaults: Sequence[str]) -> None:
        """Show the open project's face colours (without taking that for a change by the user); `defaults` are what
        Restore default brings back. A row per face: rebuilt if the number of faces differs."""
        self._face_colors, self._default_face_colors = tuple(colors), tuple(defaults)
        if len(self.face_fields) != len(colors):
            self._build_face_rows(len(colors))
        self._filling = True
        try:
            for i, color in enumerate(colors):
                self.face_swatches[i].set_color(color)
                self.face_fields[i].set_color(color)
        finally:
            self._filling = False

    def _build_face_rows(self, count: int) -> None:
        while (item := self._face_rows_layout.takeAt(0)) is not None:
            row = item.widget()
            if row is not None:
                row.deleteLater()
        self.face_swatches, self.face_fields, self.face_numbers = [], [], []
        width = self._face_rows.fontMetrics().horizontalAdvance(str(count))  # the widest number: the last one
        for face in range(1, count + 1):
            row = QWidget(self._face_rows)
            number = QLabel(f"{face}", row)
            number.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # units under units
            number.setFixedWidth(width)
            swatch = ColorSwatch("#FFFFFF", row)
            field = ColorField("#FFFFFF", row, lambda face=face: tr("Face {face} color", face=face))
            field.changed.connect(lambda color, face=face: self._on_face_color(face, color))
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            for widget in (number, swatch, field):
                line.addWidget(widget)
            line.addStretch()
            self._face_rows_layout.addWidget(row)
            self.face_swatches.append(swatch)
            self.face_fields.append(field)
            self.face_numbers.append(number)

    def _section(self, title: str) -> Section:
        section = Section(title, self)
        section.restore_requested.connect(lambda: self._restore(title))
        layout = self.layout()
        assert layout is not None
        if self.sections:  # a thin line between this section and the one above
            separator = QFrame(self)
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            layout.addWidget(separator)
            self.separators.append(separator)
        layout.addWidget(section)
        self.sections[title] = section
        return section

    def _fill(self, style: Style) -> None:
        """Show `style` in the fields (without taking that for a change by the user)."""
        self._filling = True
        try:
            self.hatch_columns.setValue(style.hatch_columns)
            self.hatch_rows.setValue(style.hatch_rows)
            self.dashes.setValue(style.dashes_per_unit)
            self.edge_width.setValue(style.edge_width)
            # A vertex circle is at least 140% of the edge width across.
            self.vertex_radius.setMinimum(least_vertex_radius(style.edge_width))
            self.vertex_radius.setValue(style.vertex_radius)
            self.grid_swatch.set_color(style.grid_color)
            self.grid_swatch.set_line_width(style.grid_width)
            self.grid_color.set_color(style.grid_color)
            self.grid_width.setValue(style.grid_width)
        finally:
            self._filling = False

    def _on_face_color(self, face: int, color: str) -> None:
        if self._filling:
            return
        colors = list(self._face_colors)
        colors[face - 1] = color
        self._change_face_colors(tuple(colors))

    def _change_face_colors(self, colors: tuple[str, ...]) -> None:
        self.set_face_colors(colors, self._default_face_colors)  # the swatches follow
        self.face_colors_changed.emit(colors)

    def _change(self, **values: object) -> None:
        if self._filling:
            return
        # Thicker edges may need larger vertices: they grow with them, just as much as needed.
        self._style = fitted(replace(self._style, **values))  # type: ignore[arg-type]
        self._fill(self._style)  # the swatches follow
        self.style_changed.emit(self._style)

    def _restore(self, title: str) -> None:
        if title == FACE_COLORS:
            self._change_face_colors(self._default_face_colors)
        else:
            self._change(**{name: getattr(DEFAULT_STYLE, name) for name in SECTION_FIELDS[title]})
