"""`Project`: everything that gets saved (docs/idea.txt): the current state, the history, settings, point names."""

from dataclasses import dataclass

from cube_net.core.editor import EditorSnapshot
from cube_net.core.history import History
from cube_net.core.labels import PointLabels
from cube_net.core.net import default_net
from cube_net.core.project_settings import ProjectSettings


class ProjectFileError(Exception):
    """A project can't be saved or loaded. The message is meant for the user."""


@dataclass(frozen=True, slots=True)
class Project:
    # The editor's state, including a cut line in progress, if any.
    state: EditorSnapshot

    # What can be undone and redone.
    history: History[EditorSnapshot]

    settings: ProjectSettings

    # The names of the points created by cuts, so that they stay the same after reopening.
    labels: PointLabels


def new_project() -> Project:
    """A new project starts with the default net (docs/idea.txt)."""
    return Project(EditorSnapshot(default_net(), None, None, 0), History(), ProjectSettings(), PointLabels())
