"""Edit -> Preferences...: settings of the application as a whole (not of a project)."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QWidget

from cube_net.ui.sheet.zoom import MAX_ZOOM_RANGE

# How much the arrows of the maximum zoom's field change it.
MAX_ZOOM_STEP = 100


class PreferencesDialog(QDialog):
    def __init__(self, max_zoom: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.max_zoom = QSpinBox(self)
        self.max_zoom.setRange(*MAX_ZOOM_RANGE)
        self.max_zoom.setSingleStep(MAX_ZOOM_STEP)
        self.max_zoom.setSuffix(" px per unit")
        self.max_zoom.setValue(max_zoom)
        self.max_zoom.setToolTip("How far in the sheet can be zoomed: how many pixels the edge of the cube takes")
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("Maximum zoom:", self.max_zoom)
        layout.addRow(self.buttons)


def ask_max_zoom(parent: QWidget | None, max_zoom: int) -> int | None:
    """Let the user edit the preferences. The new maximum zoom, or None if that was cancelled."""
    dialog = PreferencesDialog(max_zoom, parent)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    result = dialog.max_zoom.value() if accepted else None
    dialog.deleteLater()  # its parent would keep it for as long as the window lives
    return result
