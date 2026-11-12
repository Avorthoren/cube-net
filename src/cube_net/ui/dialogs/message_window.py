# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`MessageWindow`: a message or a question, with its buttons, in a `SmallWindow` (only a close button in its title
bar, never minimize or maximize).

The keys: Tab goes from button to button; Enter and Space press the one that has the focus (the default one, at
first); Escape, like the close button in the title bar, chooses the window's "escape" button (cancel, or the only
one there is). Standard buttons (OK, Cancel, Yes, Save...) are Qt's own: their texts are translated by Qt, and they
come in the order the system wants them.
"""

from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from cube_net.ui.dialogs.small_window import SmallWindow

# The icon's size, and the widest the text gets before it wraps (px).
ICON_PX = 48
TEXT_WIDTH_PX = 420


class MessageIcon(Enum):
    INFORMATION = QStyle.StandardPixmap.SP_MessageBoxInformation
    WARNING = QStyle.StandardPixmap.SP_MessageBoxWarning
    QUESTION = QStyle.StandardPixmap.SP_MessageBoxQuestion
    ERROR = QStyle.StandardPixmap.SP_MessageBoxCritical


class MessageWindow(SmallWindow):
    def __init__(
        self,
        title: str,
        text: str,
        details: str = "",
        icon: MessageIcon = MessageIcon.INFORMATION,
        parent: QWidget | None = None,
    ) -> None:
        """`text`: the message (the question); `details`: what it means, under it, in plain text."""
        super().__init__(title, parent)
        style = self.style()
        assert style is not None
        self.icon_label = QLabel(self)
        self.icon_label.setPixmap(style.standardIcon(icon.value).pixmap(ICON_PX, ICON_PX))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.text_label = _label(text, self)
        font = self.text_label.font()
        font.setBold(True)
        self.text_label.setFont(font)
        self.details_label = _label(details, self)
        self.details_label.setVisible(bool(details))
        words = QVBoxLayout()
        words.addWidget(self.text_label)
        words.addWidget(self.details_label)
        words.addStretch()
        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(self.icon_label)
        top.addLayout(words, 1)
        self.button_box = QDialogButtonBox(self)
        self.button_box.clicked.connect(self._on_clicked)
        content = QVBoxLayout()
        content.setContentsMargins(20, 16, 20, 14)
        content.setSpacing(14)
        content.addLayout(top)
        content.addWidget(self.button_box)
        self.body.addLayout(content)
        self._clicked: QPushButton | None = None
        self._escape: QPushButton | None = None

    def add_standard(self, button: QDialogButtonBox.StandardButton, text: str | None = None) -> QPushButton:
        """One of Qt's standard buttons (its text translated by Qt, unless `text` is given)."""
        added = self.button_box.addButton(button)
        assert added is not None
        if text is not None:
            added.setText(text)
        return added

    def add(self, text: str, role: QDialogButtonBox.ButtonRole) -> QPushButton:
        """A button of the application's own (`role`: where the system puts it among the others)."""
        added = self.button_box.addButton(text, role)
        assert added is not None
        return added

    def set_default(self, button: QPushButton) -> None:
        """The button that has the focus at first (Enter and Space press it)."""
        for other in self.button_box.buttons():
            if isinstance(other, QPushButton):
                other.setDefault(other is button)
        button.setFocus()

    def set_escape(self, button: QPushButton) -> None:
        """The button that Escape and the title bar's close button stand for."""
        self._escape = button

    def text(self) -> str:
        return self.text_label.text()

    def informativeText(self) -> str:
        return self.details_label.text()

    def buttons(self) -> list[QPushButton]:
        """The buttons, in the order they're shown."""
        return [b for b in self.button_box.buttons() if isinstance(b, QPushButton)]

    def button(self, which: QDialogButtonBox.StandardButton) -> QPushButton | None:
        found = self.button_box.button(which)
        return found if isinstance(found, QPushButton) else None

    def defaultButton(self) -> QPushButton | None:
        return next((b for b in self.buttons() if b.isDefault()), None)

    def escape_button(self) -> QPushButton | None:
        return self._escape

    def clicked(self) -> QPushButton | None:
        """The button chosen (the escape button if the window was closed)."""
        return self._clicked

    def ask(self) -> QPushButton | None:
        """Show it, and wait for the choice."""
        self.adjustSize()
        self.exec()
        self.deleteLater()  # its parent would keep it for as long as the window lives
        return self._clicked

    def reject(self) -> None:
        """Escape, or the title bar's close button: the escape button's choice."""
        if self._clicked is None:
            self._clicked = self._escape
        super().reject()

    def _on_clicked(self, button: object) -> None:
        self._clicked = button if isinstance(button, QPushButton) else None
        self.accept()


def _label(text: str, parent: QWidget) -> QLabel:
    label = QLabel(text, parent)
    label.setWordWrap(True)
    label.setMaximumWidth(TEXT_WIDTH_PX)
    label.setMinimumWidth(min(TEXT_WIDTH_PX, label.fontMetrics().horizontalAdvance(text) + 2))
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def tell(
    parent: QWidget | None,
    title: str,
    text: str,
    details: str = "",
    icon: MessageIcon = MessageIcon.INFORMATION,
) -> None:
    """A message with only OK (Enter, Space, Escape and the close button all mean it)."""
    window = MessageWindow(title, text, details, icon, parent)
    ok = window.add_standard(QDialogButtonBox.StandardButton.Ok)
    window.set_default(ok)
    window.set_escape(ok)
    window.ask()
