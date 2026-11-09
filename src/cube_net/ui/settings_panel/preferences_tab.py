"""The Preferences tab: vertex labels, session logs, blinking on success, how far the sheet can be zoomed in."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QWidget

from cube_net.ui.sheet.zoom import MAX_ZOOM_RANGE

# How much the arrows of the maximum zoom's field change it.
MAX_ZOOM_STEP = 100


def _mirror(box: QCheckBox, action: QAction) -> None:
    """The box and the action are the same switch: either one turns the other."""
    box.setChecked(action.isChecked())
    box.toggled.connect(action.setChecked)
    action.toggled.connect(box.setChecked)


class PreferencesTab(QWidget):
    # The user set another maximum zoom (pixels per unit).
    max_zoom_changed = pyqtSignal(int)

    # The user switched blinking on success on or off.
    blink_changed = pyqtSignal(bool)

    def __init__(
        self, labels: QAction, logs: QAction, blink: bool, max_zoom: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.show_labels = QCheckBox("Show vertex labels", self)
        _mirror(self.show_labels, labels)
        self.log_sessions = QCheckBox("Log sessions", self)
        _mirror(self.log_sessions, logs)
        self.blink = QCheckBox("Blink when target area achieved", self)
        self.blink.setChecked(blink)
        self.blink.toggled.connect(self.blink_changed)
        self.max_zoom = QSpinBox(self)
        self.max_zoom.setRange(*MAX_ZOOM_RANGE)
        self.max_zoom.setSingleStep(MAX_ZOOM_STEP)
        self.max_zoom.setKeyboardTracking(False)  # a value is taken when it's entered, not at every digit typed
        self.max_zoom.setValue(max_zoom)
        self.max_zoom.setToolTip("How far in the sheet can be zoomed: how many pixels the edge of the cube takes")
        self.max_zoom.valueChanged.connect(self.max_zoom_changed)
        layout = QFormLayout(self)
        layout.addRow(self.show_labels)
        layout.addRow(self.log_sessions)
        layout.addRow(self.blink)
        zoom = QHBoxLayout()
        zoom.addWidget(self.max_zoom)
        zoom.addWidget(QLabel("px per unit", self))
        zoom.addStretch()
        layout.addRow("Maximum zoom:", zoom)
