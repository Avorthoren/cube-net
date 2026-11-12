# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Section`: a titled part of a settings tab, with a button that restores its defaults (after asking)."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow
from cube_net.ui.i18n import bind, tr


def confirm_restore(parent: QWidget | None, section: str) -> bool:
    """Ask before the section's values are replaced by the defaults."""
    window = MessageWindow(
        tr("Restore default"),
        tr('Restore the default values of "{section}"?', section=tr(section)),
        icon=MessageIcon.QUESTION,
        parent=parent,
    )
    yes = window.add_standard(QDialogButtonBox.StandardButton.Yes)
    no = window.add_standard(QDialogButtonBox.StandardButton.No)
    window.set_default(no)
    window.set_escape(no)
    return window.ask() is yes


class Section(QWidget):
    # The user asked for the defaults, and said yes when asked again.
    restore_requested = pyqtSignal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
        header = QHBoxLayout()
        name = QLabel(self)
        bind(name, lambda text: name.setText(f"<b>{text}</b>"), title)
        self.restore_button = QPushButton(self)
        bind(self.restore_button, self.restore_button.setText, "Restore default")
        self.restore_button.clicked.connect(self._on_restore)
        header.addWidget(name)
        header.addStretch()
        header.addWidget(self.restore_button)
        self._form: QGridLayout | None = None
        self.body = QVBoxLayout()
        self.body.setContentsMargins(8, 0, 0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.addLayout(header)
        layout.addLayout(self.body)

    def add_labelled_row(self, label: str, *widgets: QWidget) -> None:
        """A row whose widgets start at the same place as those of the section's other labelled rows."""
        if self._form is None:
            self._form = QGridLayout()
            self._form.setColumnStretch(2, 1)
            self.body.addLayout(self._form)
        row = self._form.rowCount()
        text = QLabel(self)
        bind(text, text.setText, label)
        self._form.addWidget(text, row, 0)
        fields = QHBoxLayout()
        for widget in widgets:
            fields.addWidget(widget)
        fields.addStretch()
        self._form.addLayout(fields, row, 1)

    def add_row(self, *widgets: QWidget) -> None:
        row = QHBoxLayout()
        for widget in widgets:
            row.addWidget(widget)
        row.addStretch()
        self.body.addLayout(row)

    def _on_restore(self) -> None:
        if confirm_restore(self, self.title):
            self.restore_requested.emit()
