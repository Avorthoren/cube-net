# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""A new project from a template (docs/template_plan.md, §7 and §8.3): the body the template describes, its starting
net where the template has it, and the template's face colours, style and origin. Nothing refers to the template
afterwards."""

from cube_net.core.editor import EditorSnapshot
from cube_net.core.history import History
from cube_net.core.labels import PointLabels
from cube_net.core.net.default_net import starting_net
from cube_net.core.project.project import Project
from cube_net.core.project.template_codec import TemplateDocument
from cube_net.core.project_settings import ProjectSettings
from cube_net.core.template.template_body import body_and_point_names


def project_from_template(document: TemplateDocument) -> Project:
    """The new project. The template must be a valid one (`validate` finds no problem)."""
    body, names = body_and_point_names(document.state.template)
    state = EditorSnapshot(starting_net(body), None, None, 0, document.state.origin)
    settings = ProjectSettings(face_colors=body.colors, style=document.style)
    return Project(state, History(), settings, PointLabels.named(body, names))  # X_1 where the template has X_1
