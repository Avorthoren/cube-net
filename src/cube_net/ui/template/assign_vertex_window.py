# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`AssignVertexWindow`: which vertex of the body a vertex of the template is an image of (docs/template_idea.txt:
right click -> Assign label).

    Name (1-2 Latin letters) and index (1-99):
    [name] [index]

The name takes capital Latin letters (typed small ones become capital); empty, the vertex has no label. A vertex with
no label yet starts with no name and index 1. Assign gives the label, unless another vertex has it: then a second window
asks "Such label already exists. Assign first free index?" Yes gives the smallest index no vertex of that name has, and
both windows close; No goes back to the first one. Cancel, Escape and the close button change nothing.
"""

from collections.abc import Callable

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cube_net.core.template import Label
from cube_net.core.template.template import MAX_INDEX, MIN_INDEX
from cube_net.ui.dialogs.message_window import ask_yes_no
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr


class AssignVertexWindow(SmallWindow):
    def __init__(
        self,
        label: Label | None,
        owner_of: Callable[[Label], bool],
        first_free_index: Callable[[str], int],
        parent: QWidget | None = None,
    ) -> None:
        """`label`: the vertex's label now; `owner_of`: whether another vertex has a label; `first_free_index`: the
        smallest index of a name that no vertex has."""
        super().__init__(tr("Assign label"), parent)
        self._taken = owner_of
        self._first_free_index = first_free_index
        self._label: Label | None = label
        prompt = QLabel(tr("Name (1-2 Latin letters) and index (1-99):"), self)
        self.name = QLineEdit(self)
        self.name.setValidator(QRegularExpressionValidator(QRegularExpression("[A-Za-z]{0,2}"), self.name))
        self.name.setMaxLength(2)
        self.name.textEdited.connect(lambda text: self.name.setText(text.upper()))
        width = self.name.fontMetrics().horizontalAdvance("WW") + 16
        self.name.setFixedWidth(width)
        self.index = QSpinBox(self)
        self.index.setRange(MIN_INDEX, MAX_INDEX)
        if label is not None:
            self.name.setText(label.name)
            self.index.setValue(label.index)
        else:
            self.index.setValue(MIN_INDEX)
        fields = QHBoxLayout()
        fields.addWidget(self.name)
        fields.addWidget(self.index)
        fields.addStretch()
        buttons = QDialogButtonBox(self)
        self.assign_button = QPushButton(tr("Assign"), self)
        buttons.addButton(self.assign_button, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        assert cancel is not None
        self.cancel_button = cancel
        self.assign_button.clicked.connect(self._on_assign)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(prompt)
        layout.addLayout(fields)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        self.assign_button.setDefault(True)
        self.name.setFocus()
        self.name.selectAll()

    def label(self) -> Label | None:
        """The label given (None: no label)."""
        return self._label

    def typed(self) -> Label | None:
        """The label in the fields (None: no name)."""
        name = self.name.text().upper()
        return Label(name, self.index.value()) if name else None

    def _on_assign(self) -> None:
        label = self.typed()
        if label is not None and self._taken(label):
            if not ask_yes_no(self, tr("Such label already exists. Assign first free index?")):
                return  # back to the fields
            label = Label(label.name, self._first_free_index(label.name))
        self._label = label
        self.accept()
