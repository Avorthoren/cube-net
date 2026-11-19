# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`TemplateMode`: what the main window has for making a template (docs/template_idea.txt): its own sheet view (the
fixed 100 x 100 template sheet), the editor and the tool on it, the cursor and the right click's menu, the file, and
validation. The main window shows it instead of the project's view while a template is open, and passes it the
actions that mean something for a template (undo, redo, save, Validate, Escape).
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QWidget

from cube_net.core.geometry import Box, Vec
from cube_net.core.history import History
from cube_net.core.project import TemplateDocument, save_template
from cube_net.core.sheet import TEMPLATE_SHEET_HEIGHT, TEMPLATE_SHEET_WIDTH
from cube_net.core.template import (
    Template,
    TemplateEditor,
    TemplateSnapshot,
    TemplateState,
    ValidationProblem,
    ValidationStatus,
    template_area,
    validate,
)
from cube_net.ui import palette
from cube_net.ui.dialogs.message_window import MessageIcon, ask_yes_no, tell
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.sheet_context_menu import SheetContextMenu
from cube_net.ui.sheet.sheet_cursor import SheetCursor
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.style import DEFAULT_STYLE, Style
from cube_net.ui.template.assign_vertex_window import AssignVertexWindow
from cube_net.ui.template.template_tool import TemplateTool
from cube_net.ui.template.validation_messages import failure_text, no_problems_text, reindexed_text

# The template sheet.
SHEET = Box(Vec(0, 0), Vec(TEMPLATE_SHEET_WIDTH, TEMPLATE_SHEET_HEIGHT))

# What a new template's view shows at first: this much of the sheet around its middle (as a project shows its net).
FIRST_VIEW = Box(Vec(45, 45), Vec(55, 55))


class TemplateMode(QObject):
    # The template, its origin or its history changed (the window's title, the area, the actions follow).
    changed = pyqtSignal()

    def __init__(self, parent: QWidget, note: Callable[..., None]) -> None:
        """`note`: writes a line to the session log, if one is being recorded."""
        super().__init__(parent)
        self._parent = parent
        self._note = note
        self.view = SheetView(parent)
        self.view.set_sheet(SHEET)
        self.editor = TemplateEditor()
        self.tool = TemplateTool(self.view, self.editor)
        self.cursor = SheetCursor(self.view, self.tool, None)
        self.context_menu = SheetContextMenu(self.view, self.tool, assign=self._assign_vertex_at)
        self.context_menu.point_name = self._label_at
        # The template's file, once it has one; the history's revision when it was last saved (or opened).
        self.path: Path | None = None
        self._saved_revision = 0

        # Settings -> Style while this template is shown (saved with it), and as it was when last saved (or opened).
        self.style: Style = DEFAULT_STYLE
        self._saved_style = self.style

        # The template the last explicit Validate was about, and what it said; and the status when last saved (or
        # opened). Any other template is Undefined.
        self._validated: tuple[Template, ValidationStatus] | None = None
        self._saved_status = ValidationStatus.UNDEFINED
        self.tool.changed.connect(self.changed)
        self.tool.acted.connect(lambda action, p: self._note("template", action, _point(p)))
        self.tool.rejected.connect(lambda p, problem: self._note("template", "rejected", problem.value, _point(p)))
        self.tool.face_double_clicked.connect(self._pick_face_color)
        self.tool.warned.connect(lambda text: tell(parent, "Cube Net", text, icon=MessageIcon.WARNING))
        self.view.show_initial_view(FIRST_VIEW)

    # --- the document -------------------------------------------------------------------------------------------------

    def document(self) -> TemplateDocument:
        return TemplateDocument(self.editor.snapshot(), self.editor.history, self.style, self.status())

    def show(self, document: TemplateDocument | None, path: Path | None, style: Style) -> None:
        """Make `document` (None: a new, empty template) the one shown, from the file `path` (None: none yet), with
        `style` (the document's own, or the one filled in where it has none: not a change)."""
        if document is None:
            document = TemplateDocument(TemplateSnapshot(TemplateEditor().template), History())
        self.tool.cancel()
        self.editor.load(document.state, document.history)
        self.path = path
        self._saved_revision = document.history.revision
        self.style = self._saved_style = style
        self._validated = (document.state.template, document.validation)
        self._saved_status = document.validation
        self.tool.refresh()
        self.tool.origin_changed.emit()
        vertices = self.editor.template.vertices
        self.view.show_initial_view(Box.around(v.position for v in vertices).expanded(1) if vertices else FIRST_VIEW)
        self.changed.emit()

    def mark_unsaved(self) -> None:
        """What's shown isn't what the file holds (a damaged file restored): it has changes to save."""
        self._saved_revision = -1
        self.changed.emit()

    @property
    def is_dirty(self) -> bool:
        return (
            self.editor.history.revision != self._saved_revision
            or self.style != self._saved_style
            or self.status() != self._saved_status
        )

    def set_style(self, style: Style) -> None:
        """Settings -> Style changed while the template is shown (not undoable, like a project's style)."""
        self.style = style
        self.changed.emit()

    def save_to(self, path: Path) -> None:
        """Save to `path` (raises `ProjectFileError` if it can't be): from now on that's the template's file."""
        save_template(self.document(), path)
        self.path = path
        self._saved_revision = self.editor.history.revision
        self._saved_style = self.style
        self._saved_status = self.status()
        self.changed.emit()

    def area(self) -> Fraction | None:
        return template_area(self.editor.template)

    # --- validation ---------------------------------------------------------------------------------------------------

    def status(self) -> ValidationStatus:
        """What the last explicit Validate said about the template as it is now (Undefined if it changed since)."""
        if self._validated is None or self._validated[0] != self.editor.template:
            return ValidationStatus.UNDEFINED
        return self._validated[1]

    def can_validate(self) -> bool:
        """A closed loop, nothing being dragged, and not Validated already (an Invalid one may be validated again,
        to see what's wrong)."""
        return (
            self.editor.state is TemplateState.FINALIZATION
            and self.editor.template.complete
            and not self.tool.drawing_hole
            and not self.tool.busy()
            and self.status() is not ValidationStatus.VALID
        )

    def validate(self) -> None:
        """Validate (V): the first problem found, in a message (Invalid); gaps in indices, the last check, may be
        closed (Yes: Valid then); or that there's no problem (Valid)."""
        if not self.can_validate():
            return
        template = self.editor.template
        failure = validate(template)
        if failure is None:
            self.tool.align_hatches()  # the pieces of each face hatched alike
            self._set_status(self.editor.template, ValidationStatus.VALID)
            self._note("template", "validate", "ok")
            tell(self._parent, "Cube Net", no_problems_text())
            return
        self._set_status(template, ValidationStatus.INVALID)
        self._note("template", "validate", failure.problem.value, *failure.names, *failure.colors)
        if failure.problem is not ValidationProblem.INDEX_GAPS:
            tell(self._parent, "Cube Net", failure_text(failure), icon=MessageIcon.WARNING)
            return
        if not ask_yes_no(self._parent, failure_text(failure)):
            return
        self.tool.reindex()
        self.tool.align_hatches()
        self._set_status(self.editor.template, ValidationStatus.VALID)  # nothing else was wrong
        self._note("template", "reindexed")
        tell(self._parent, "Cube Net", reindexed_text())

    def _set_status(self, template: Template, status: ValidationStatus) -> None:
        self._validated = (template, status)
        self.changed.emit()

    # --- the windows --------------------------------------------------------------------------------------------------

    def _assign_vertex_at(self, position: Vec) -> None:
        vertex = next(v for v in self.editor.template.all_vertices if v.position == position)
        template = self.editor.template
        window = AssignVertexWindow(
            vertex.label,
            lambda label: (owner := template.label_owner(label)) is not None and owner.id != vertex.id,
            template.first_free_index,
            self.view.window(),
        )
        self.view.follow_cursor(window)
        try:
            accepted = window.exec() == AssignVertexWindow.DialogCode.Accepted
        finally:
            self.view.follow_cursor(None)
        label = window.label()
        window.deleteLater()
        if accepted:
            self.tool.set_label(vertex.id, label)
            self._note("template", "label", _point(position), "-" if label is None else str(label))

    def _pick_face_color(self, face: int) -> None:
        picker = QColorDialog(self.view.window())
        picker.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)  # before the colour: see `ColorField`
        picker.setCurrentColor(QColor(self.editor.template.faces[face].color or palette.WHITE.name()))
        picker.setWindowTitle(tr("Face color"))
        try:
            accepted = picker.exec() == QColorDialog.DialogCode.Accepted
            color = picker.selectedColor().name().upper()
        finally:
            picker.deleteLater()
        if accepted:
            self.tool.set_face_color(face, color)
            self._note("template", "color", face + 1, color)

    def _label_at(self, position: Vec) -> str | None:
        vertex = next((v for v in self.editor.template.all_vertices if v.position == position), None)
        return None if vertex is None or vertex.label is None else str(vertex.label)


def _point(p: Vec) -> str:
    return f"{float(p.x):.3f},{float(p.y):.3f}"
