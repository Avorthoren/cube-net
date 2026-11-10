"""What to do when the last project can't be reopened at start (docs/idea.txt): a new project, or another file."""

from enum import Enum

from PyQt6.QtWidgets import QMessageBox, QWidget

from cube_net.ui.i18n import tr


class AfterLoadFailed(Enum):
    NEW_PROJECT = "new project"
    OPEN_ANOTHER = "open another"


def ask_after_load_failed(parent: QWidget | None, message: str) -> AfterLoadFailed:
    """Tell why it failed, and suggest a new project. Closing the question means just that."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("Can't open the project"))
    box.setText(message)
    box.setInformativeText(tr("Start a new project, or open another one?"))
    new_project = box.addButton(tr("New project"), QMessageBox.ButtonRole.AcceptRole)
    open_another = box.addButton(tr("&Open..."), QMessageBox.ButtonRole.ActionRole)
    box.setDefaultButton(new_project)
    box.setEscapeButton(new_project)
    box.exec()
    clicked = box.clickedButton()
    box.deleteLater()  # its parent would keep it for as long as the window lives
    return AfterLoadFailed.OPEN_ANOTHER if clicked is open_another else AfterLoadFailed.NEW_PROJECT
