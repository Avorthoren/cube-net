# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`NewProjectWindow`: File -> New (docs/template_idea.txt, "File -> New"; docs/template_plan.md, §7 and §8.3).

              [Cube | Cube with a hole | Custom template]
         [template file (.nettemplate)] [Browse...]
                        [Cancel] [Create]

The line with the file is only there for Custom template (empty otherwise, so that the window keeps its size). Create
with a custom template reads it and validates it quietly: a file that can't be read, or a project, is said so, and the
window stays; a template that isn't valid asks "Template is not valid. Open template?": Yes ends the window with that
template to open for editing, No goes back to it. Otherwise the window ends with the new project: the cube, or the body
of the template, with the template's style, colours and origin.
"""

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cube_net.core.project import Project, ProjectFileError, TemplateDocument, load_document, new_project
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.project.from_template import project_from_template
from cube_net.core.template import validate
from cube_net.ui.dialogs.message_window import MessageIcon, ask_yes_no, tell
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr
from cube_net.ui.i18n.errors import error_text
from cube_net.ui.style import DEFAULT_STYLE

# The file field's width beyond its placeholder text, in pixels (the field's frame and margins).
FILE_FIELD_EXTRA_PX = 16

# Between the window's three lines (what to start from, the file, the buttons), in pixels.
LINE_SPACING_PX = 14


class Start(Enum):
    """What a new project starts from (the dropdown's options, in its order)."""

    CUBE = "cube"
    CUBE_WITH_A_HOLE = "cube_with_a_hole"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class NewProjectChoice:
    """How the window ended (with Create): a new project, or a template that isn't valid, to open for editing."""

    start: Start

    # The custom template's file (None: a built-in one).
    path: Path | None

    project: Project | None = None
    template: TemplateDocument | None = None


def builtin_project(start: Start) -> Project:
    """A new project from a built-in template: the cube with the style files' style, or the Cube with a hole."""
    if start is Start.CUBE:
        project = new_project()
        return replace(project, settings=replace(project.settings, style=DEFAULT_STYLE))
    return project_from_template(cube_with_a_hole())


class NewProjectWindow(SmallWindow):
    def __init__(self, files_filter: str, folder: str = "", parent: QWidget | None = None) -> None:
        """`files_filter`: what the Browse window shows; `folder`: where it starts."""
        super().__init__(tr("New project"), parent)
        self._filter = files_filter
        self._folder = folder
        self._choice: NewProjectChoice | None = None
        self.start = QComboBox(self)
        self.start.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)  # as wide as its longest option
        self.start.addItem(tr("Cube"), Start.CUBE)
        self.start.addItem(tr("Cube with a hole"), Start.CUBE_WITH_A_HOLE)
        self.start.addItem(tr("Custom template"), Start.CUSTOM)
        self.file = QLineEdit(self)
        self.file.setPlaceholderText(tr("Template file (.nettemplate)"))
        self.file.setFixedWidth(
            self.file.fontMetrics().horizontalAdvance(self.file.placeholderText()) + FILE_FIELD_EXTRA_PX
        )
        self.browse = QPushButton(tr("Browse..."), self)
        self.browse.setAutoDefault(False)
        self.browse.clicked.connect(self._on_browse)
        starts = QHBoxLayout()
        starts.addStretch()
        starts.addWidget(self.start)
        starts.addStretch()
        file = QHBoxLayout()
        file.setContentsMargins(0, 0, 0, 0)
        file.addStretch()
        file.addWidget(self.file)
        file.addWidget(self.browse)
        file.addStretch()
        # The file's line: hidden unless it's Custom template, but its room stays.
        self.file_line = QWidget(self)
        self.file_line.setLayout(file)
        policy = self.file_line.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.file_line.setSizePolicy(policy)
        buttons = QDialogButtonBox(self)
        buttons.setCenterButtons(True)
        self.create_button = QPushButton(tr("Create"), self)
        buttons.addButton(self.create_button, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        assert cancel is not None
        self.cancel_button = cancel
        self.create_button.clicked.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(LINE_SPACING_PX)
        layout.addLayout(starts)
        layout.addWidget(self.file_line)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        self.start.currentIndexChanged.connect(self._update_file)
        self._update_file()
        self.create_button.setDefault(True)
        self.start.setFocus()

    def choice(self) -> NewProjectChoice | None:
        """What Create ended the window with (None: it was cancelled)."""
        return self._choice

    def selected(self) -> Start:
        start = self.start.currentData()
        assert isinstance(start, Start)
        return start

    def _update_file(self) -> None:
        self.file_line.setVisible(self.selected() is Start.CUSTOM)

    def _on_browse(self) -> None:
        folder = str(Path(self.file.text()).parent) if self.file.text() else self._folder
        name, _ = QFileDialog.getOpenFileName(self, tr("Choose template"), folder, self._filter)
        if name:
            self.file.setText(name)

    def _on_create(self) -> None:
        start = self.selected()
        if start is not Start.CUSTOM:
            self._choice = NewProjectChoice(start, None, builtin_project(start))
            self.accept()
            return
        if not self.file.text().strip():
            self.file.setFocus()
            return
        path = Path(self.file.text().strip())
        try:
            document = load_document(path)
        except ProjectFileError as e:
            tell(self, "Cube Net", error_text(e), icon=MessageIcon.ERROR)
            return
        if not isinstance(document, TemplateDocument):
            tell(self, "Cube Net", tr("{path} is a project, not a template.", path=path), icon=MessageIcon.ERROR)
            return
        template = document.state.template
        if not template.closed or validate(template) is not None:  # validating needs a closed loop
            if ask_yes_no(self, tr("Template is not valid. Open template?")):
                self._choice = NewProjectChoice(start, path, template=document)
                self.accept()
            return
        self._choice = NewProjectChoice(start, path, project_from_template(document))
        self.accept()


def choose_new_project(parent: QWidget, files_filter: str, folder: str) -> NewProjectChoice | None:
    """File -> New's window, until the user creates a project or cancels (None)."""
    window = NewProjectWindow(files_filter, folder, parent)
    try:
        window.exec()
        return window.choice()
    finally:
        window.deleteLater()
