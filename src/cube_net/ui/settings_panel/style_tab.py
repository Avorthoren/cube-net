"""The Style tab: how the net and the sheet look (docs/idea.txt, settings). Every change takes effect at once."""

from dataclasses import replace

from PyQt6.QtCore import QLocale, pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QFrame, QLabel, QSpinBox, QVBoxLayout, QWidget

from cube_net.ui.i18n import bind
from cube_net.ui.settings_panel.color_field import ColorField
from cube_net.ui.settings_panel.section import Section
from cube_net.ui.settings_panel.swatches import ColorSwatch, GridSwatch
from cube_net.ui.style import DEFAULT_STYLE, Style
from cube_net.ui.style.style import (
    DASHES_RANGE,
    EDGE_WIDTH_RANGE,
    GRID_WIDTH_RANGE,
    TILING_RANGE,
    VERTEX_RADIUS_RANGE,
    least_vertex_radius,
)

# Between the two numbers of the tiling: the multiplication sign.
BY_SIGN = chr(0x00D7)

# The unit shown after a field in pixels.
PIXELS = "px"

# Sizes in pixels have this many decimals.
PIXEL_DECIMALS = 1

# The names of the sections, as shown (and as the confirmation names them).
FACE_COLORS = "Faces colors"
FACE_TILING = "Faces tiling"
CUTS_AND_FOLDS = "Cuts and folds"
VERTICES = "Vertices"
GRID = "Grid"

# Which values each section restores.
SECTION_FIELDS = {
    FACE_COLORS: ("face_colors",),
    FACE_TILING: ("hatch_columns", "hatch_rows"),
    CUTS_AND_FOLDS: ("dashes_per_edge", "edge_width"),
    VERTICES: ("vertex_radius",),
    GRID: ("grid_color", "grid_width"),
}


def _count_box(allowed: tuple[int, int], parent: QWidget) -> QSpinBox:
    box = QSpinBox(parent)
    box.setRange(*allowed)
    return box


def _pixels_box(allowed: tuple[float, float], parent: QWidget) -> QDoubleSpinBox:
    box = QDoubleSpinBox(parent)
    box.setLocale(QLocale.c())  # 1.5, never 1,5
    box.setDecimals(PIXEL_DECIMALS)
    box.setRange(*allowed)
    box.setSingleStep(0.5)
    return box


def _px(parent: QWidget) -> QLabel:
    """The unit, after a field in pixels."""
    label = QLabel(parent)
    bind(label, label.setText, PIXELS)
    return label


class StyleTab(QWidget):
    # The user changed the style.
    style_changed = pyqtSignal(object)

    def __init__(self, style: Style, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._style = style
        self._filling = False
        layout = QVBoxLayout(self)
        self.sections: dict[str, Section] = {}
        self.separators: list[QFrame] = []

        colors = self._section(FACE_COLORS)
        self.face_swatches: list[ColorSwatch] = []
        self.face_fields: list[ColorField] = []
        for face in range(1, 7):
            swatch, field = (
                ColorSwatch(style.face_colors[face - 1], colors),
                ColorField(style.face_colors[face - 1], colors),
            )
            field.changed.connect(lambda color, face=face: self._on_face_color(face, color))
            colors.add_row(QLabel(f"{face}", colors), swatch, field)
            self.face_swatches.append(swatch)
            self.face_fields.append(field)

        tiling = self._section(FACE_TILING)
        self.hatch_columns, self.hatch_rows = _count_box(TILING_RANGE, tiling), _count_box(TILING_RANGE, tiling)
        tiling.add_row(self.hatch_columns, QLabel(BY_SIGN, tiling), self.hatch_rows)

        cuts = self._section(CUTS_AND_FOLDS)
        self.dashes = _count_box(DASHES_RANGE, cuts)
        self.edge_width = _pixels_box(EDGE_WIDTH_RANGE, cuts)
        cuts.add_labelled_row("Dashes", self.dashes)
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
        self.dashes.valueChanged.connect(lambda v: self._change(dashes_per_edge=v))
        self.edge_width.valueChanged.connect(lambda v: self._change(edge_width=v))
        self.vertex_radius.valueChanged.connect(lambda v: self._change(vertex_radius=v))
        self.grid_width.valueChanged.connect(lambda v: self._change(grid_width=v))

    def style(self) -> Style:
        return self._style

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
            for i, color in enumerate(style.face_colors):
                self.face_swatches[i].set_color(color)
                self.face_fields[i].set_color(color)
            self.hatch_columns.setValue(style.hatch_columns)
            self.hatch_rows.setValue(style.hatch_rows)
            self.dashes.setValue(style.dashes_per_edge)
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
        colors = list(self._style.face_colors)
        colors[face - 1] = color
        self._change(face_colors=tuple(colors))

    def _change(self, **values: object) -> None:
        if self._filling:
            return
        # Thicker edges may need larger vertices: they grow with them, just as much as needed.
        self._style = replace(self._style, **values).fitted()  # type: ignore[arg-type]
        self._fill(self._style)  # the swatches follow
        self.style_changed.emit(self._style)

    def _restore(self, title: str) -> None:
        self._change(**{name: getattr(DEFAULT_STYLE, name) for name in SECTION_FIELDS[title]})
