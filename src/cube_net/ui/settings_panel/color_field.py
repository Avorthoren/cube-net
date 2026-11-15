# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ColorField`: a colour as RGB hex digits, after a `#` that's already there; optionally with a button after them that
opens a colour picker (`QColorDialog`, Qt's own: the same everywhere, and in the application's language).

While the picker is open, the colour it shows is taken at once (the sheet shows it); OK keeps the last one, Cancel,
Escape and the close button go back to the colour there was before. It opens with its right edge on the application's
right edge, so that the net stays in sight on the left (`place_at_right_edge`); not on Wayland, where the system places
windows and an application can't.
"""

from collections.abc import Callable

from PyQt6.QtCore import QPoint, QRegularExpression, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QRegularExpressionValidator
from PyQt6.QtWidgets import QColorDialog, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QToolButton, QWidget

from cube_net.ui.i18n import bind


class ColorField(QWidget):
    # A complete colour was entered: "#RRGGBB".
    changed = pyqtSignal(str)

    def __init__(
        self, color: str, parent: QWidget | None = None, picker_title: Callable[[], str] | None = None
    ) -> None:
        """`picker_title`: the colour picker's title, in the current language (None: no picker)."""
        super().__init__(parent)
        self._color = color
        self._picker_title = picker_title

        # The colour picker, while it's open.
        self.picker: QColorDialog | None = None
        self.edit = QLineEdit(color[1:], self)
        self.edit.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9A-Fa-f]{0,6}"), self.edit))
        self.edit.setMaxLength(6)
        width = self.edit.fontMetrics().horizontalAdvance("DDDDDD") + 16
        self.edit.setFixedWidth(width)
        self.edit.textEdited.connect(self._on_edited)
        self.edit.editingFinished.connect(self._on_finished)
        self.hash = QLabel("#", self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.hash)
        layout.addWidget(self.edit)
        self.pick_button: QToolButton | None = None
        if picker_title is not None:
            self.pick_button = QToolButton(self)
            self.pick_button.setIcon(QIcon.fromTheme("color-select-symbolic", QIcon.fromTheme("color-select")))
            if self.pick_button.icon().isNull():
                self.pick_button.setText("…")  # no such icon in the system's theme
            bind(self.pick_button, self.pick_button.setToolTip, "Choose the color")
            self.pick_button.clicked.connect(self.pick)
            layout.addSpacing(4)
            layout.addWidget(self.pick_button)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # the # stays right next to the digits

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        """Show this colour (without telling anyone)."""
        self._color = color
        self.edit.setText(color[1:])

    def pick(self) -> None:
        """Open the colour picker, and wait for it (see the module's docstring)."""
        assert self._picker_title is not None
        before = self._color
        self.picker = QColorDialog(self)
        # Qt's own first, then the colour: given before, the colour goes to the system's dialog (GNOME has one), and
        # Qt's own would start empty (black, no digits).
        self.picker.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        self.picker.setCurrentColor(QColor(before))
        self.picker.setWindowTitle(self._picker_title())
        self.picker.currentColorChanged.connect(self._take)
        window = self.window()
        if window is not self and window is not None:
            picker = self.picker
            place_at_right_edge(picker, window)
            QTimer.singleShot(0, lambda: place_at_right_edge(picker, window))  # again, now that its frame is known
        try:
            accepted = self.picker.exec() == QColorDialog.DialogCode.Accepted
            self._take(self.picker.selectedColor() if accepted else QColor(before))
        finally:
            self.picker.deleteLater()
            self.picker = None

    def _take(self, color: QColor) -> None:
        """The picker's colour: shown, and told if it's another one."""
        name = color.name().upper()
        if name != self._color:
            self._color = name
            self.edit.setText(name[1:])
            self.changed.emit(name)

    def _on_edited(self, text: str) -> None:
        if len(text) == 6:
            self._color = "#" + text.upper()
            self.changed.emit(self._color)

    def _on_finished(self) -> None:
        self.edit.setText(self._color[1:])  # an unfinished colour goes back to the one in use


def place_at_right_edge(dialog: QWidget, window: QWidget) -> None:
    """Move `dialog` so that its right edge is on `window`'s, halfway down it (and all of it on the screen). Nothing on
    Wayland: there, the system places windows, and Qt can't even tell where they are."""
    if QGuiApplication.platformName() == "wayland" or not dialog.isWindow():
        return
    dialog.adjustSize()
    frame, size = window.frameGeometry(), dialog.frameGeometry().size()
    x = frame.right() + 1 - size.width()
    y = frame.top() + (frame.height() - size.height()) // 2
    screen = window.screen()
    if screen is not None:
        area = screen.availableGeometry()
        x = max(area.left(), min(x, area.right() + 1 - size.width()))
        y = max(area.top(), min(y, area.bottom() + 1 - size.height()))
    dialog.move(QPoint(x, y))
