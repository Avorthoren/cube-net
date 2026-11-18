# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Templates: a body described by one of its nets, and making one (docs/template_plan.md, §4)."""

from cube_net.core.template.rules import (
    MIN_VERTICES,
    MIN_VERTICES_TO_CLOSE,
    TemplateProblem,
    TemplateRejection,
    on_the_sheet,
)
from cube_net.core.template.template import Fold, Label, LoopVertex, Template, TemplateFace, template_area
from cube_net.core.template.template_body import body_from_template
from cube_net.core.template.template_editor import TemplateEditor, TemplateSnapshot, TemplateState
from cube_net.core.template.validation import MIN_FACES, ValidationFailure, ValidationProblem, reindexed, validate
from cube_net.core.template.validation_status import ValidationStatus

__all__ = [
    "MIN_FACES",
    "MIN_VERTICES",
    "MIN_VERTICES_TO_CLOSE",
    "Fold",
    "Label",
    "LoopVertex",
    "Template",
    "TemplateEditor",
    "TemplateFace",
    "TemplateProblem",
    "TemplateRejection",
    "TemplateSnapshot",
    "TemplateState",
    "ValidationFailure",
    "ValidationProblem",
    "ValidationStatus",
    "body_from_template",
    "on_the_sheet",
    "reindexed",
    "template_area",
    "validate",
]
