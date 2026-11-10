"""`Project`: everything that gets saved (docs/idea.txt): the current state, the history, settings, point names."""

from dataclasses import dataclass

from cube_net.core.editor import EditorSnapshot
from cube_net.core.history import History
from cube_net.core.labels import PointLabels
from cube_net.core.net import default_net
from cube_net.core.project_settings import ProjectSettings


class ProjectFileError(Exception):
    """A project can't be saved or loaded. The message is meant for the user.

    It's a template with {placeholders} and their values, so that the UI can show it in the user's language: the
    template is the English text (`str` gives it filled in). A value can be another `ProjectFileError` (the reason).
    """

    def __init__(self, template: str, **values: object) -> None:
        self.template = template
        self.values = values
        super().__init__(template.format(**{k: str(v) for k, v in values.items()}))


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
