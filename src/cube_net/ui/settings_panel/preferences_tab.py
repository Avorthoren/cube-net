"""The Preferences tab: language, vertex labels, session logs, blinking on success, how far the sheet can be zoomed
in."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QWidget

from cube_net.ui.i18n import Language, bind
from cube_net.ui.i18n.translator import in_every_language
from cube_net.ui.sheet.zoom import MAX_ZOOM_RANGE

# Room between the language's label and its list, after the label's longest text.
LANGUAGE_GAP_PX = 8

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

    # The user chose another language.
    language_changed = pyqtSignal(object)

    def __init__(
        self,
        labels: QAction,
        logs: QAction,
        blink: bool,
        max_zoom: int,
        language: Language = Language.ENGLISH,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.language_label = QLabel(self)
        bind(self.language_label, self.language_label.setText, "Language")
        # As wide as its text is in the widest language: the list next to it stays where it is when the language
        # changes.
        metrics = self.language_label.fontMetrics()
        width = max(metrics.horizontalAdvance(text) for text in in_every_language("Language"))
        self.language_label.setFixedWidth(width + LANGUAGE_GAP_PX)
        self.language = QComboBox(self)
        for known in Language:
            self.language.addItem(known.native_name, known)  # in its own language, whatever the current one is
        self.language.setCurrentIndex(list(Language).index(language))
        self.language.currentIndexChanged.connect(lambda i: self.language_changed.emit(self.language.itemData(i)))
        self.show_labels = QCheckBox(self)
        bind(self.show_labels, self.show_labels.setText, "Show vertex labels")
        _mirror(self.show_labels, labels)
        self.log_sessions = QCheckBox(self)
        bind(self.log_sessions, self.log_sessions.setText, "Log sessions")
        _mirror(self.log_sessions, logs)
        self.blink = QCheckBox(self)
        bind(self.blink, self.blink.setText, "Blink when target area achieved")
        self.blink.setChecked(blink)
        self.blink.toggled.connect(self.blink_changed)
        self.max_zoom = QSpinBox(self)
        self.max_zoom.setRange(*MAX_ZOOM_RANGE)
        self.max_zoom.setSingleStep(MAX_ZOOM_STEP)
        self.max_zoom.setKeyboardTracking(False)  # a value is taken when it's entered, not at every digit typed
        self.max_zoom.setValue(max_zoom)
        bind(
            self.max_zoom,
            self.max_zoom.setToolTip,
            "How far in the sheet can be zoomed: how many pixels the edge of the cube takes",
        )
        self.max_zoom.valueChanged.connect(self.max_zoom_changed)
        layout = QFormLayout(self)
        language_row = QHBoxLayout()
        language_row.setSpacing(0)
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language)
        language_row.addStretch()
        layout.addRow(language_row)
        layout.addRow(self.show_labels)
        layout.addRow(self.log_sessions)
        layout.addRow(self.blink)
        zoom = QHBoxLayout()
        zoom.addWidget(self.max_zoom)
        unit = QLabel(self)
        bind(unit, unit.setText, "px per unit")
        zoom.addWidget(unit)
        zoom.addStretch()
        zoom_label = QLabel(self)
        bind(zoom_label, zoom_label.setText, "Maximum zoom:")
        layout.addRow(zoom_label, zoom)
