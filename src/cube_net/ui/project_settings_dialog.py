"""File -> Project settings...: the settings that belong to the project (docs/idea.txt)."""

from fractions import Fraction

from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QWidget

from cube_net.core.project_settings import MAX_AREA_THRESHOLD, MIN_AREA_THRESHOLD, ProjectSettings

# The threshold has at most this many decimals (docs/idea.txt).
THRESHOLD_DECIMALS = 3

# How much the arrows of the threshold's field change it.
THRESHOLD_STEP = 0.1


class ProjectSettingsDialog(QDialog):
    def __init__(self, settings: ProjectSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project settings")
        self.threshold = QDoubleSpinBox(self)
        self.threshold.setLocale(QLocale.c())  # always 7.100, never 7,100
        self.threshold.setDecimals(THRESHOLD_DECIMALS)
        self.threshold.setRange(float(MIN_AREA_THRESHOLD), float(MAX_AREA_THRESHOLD))
        self.threshold.setSingleStep(THRESHOLD_STEP)
        self.threshold.setValue(float(settings.area_threshold))
        self.threshold.setToolTip("A net whose smallest bounding rectangle has a smaller area than this is a success")
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("Area threshold:", self.threshold)
        layout.addRow(self.buttons)

    def settings(self) -> ProjectSettings:
        """What the fields say. They allow only valid values, and exact ones: they have just 3 decimals."""
        scale = 10**THRESHOLD_DECIMALS
        return ProjectSettings(Fraction(round(self.threshold.value() * scale), scale))


def ask_project_settings(parent: QWidget | None, settings: ProjectSettings) -> ProjectSettings | None:
    """Let the user edit the settings. None if that was cancelled."""
    dialog = ProjectSettingsDialog(settings, parent)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    result = dialog.settings() if accepted else None
    dialog.deleteLater()  # its parent would keep it for as long as the window lives
    return result
