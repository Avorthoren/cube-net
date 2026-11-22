# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Projects and templates: the whole state of the user's work, and how it's kept in a file (docs/plan.md, 5.3)."""

from cube_net.core.project.codec import FORMAT_VERSION, decode_project, encode_project
from cube_net.core.project.file import (
    PROJECT_SUFFIX,
    TEMPLATE_SUFFIX,
    document_from_bytes,
    load_document,
    load_project,
    project_from_bytes,
    project_to_bytes,
    restorable,
    restore_document,
    save_project,
    save_template,
    template_to_bytes,
)
from cube_net.core.project.project import Project, ProjectFileError, new_project
from cube_net.core.project.template_codec import TemplateDocument, decode_template, encode_template

__all__ = [
    "FORMAT_VERSION",
    "PROJECT_SUFFIX",
    "TEMPLATE_SUFFIX",
    "Project",
    "ProjectFileError",
    "TemplateDocument",
    "decode_project",
    "decode_template",
    "document_from_bytes",
    "encode_project",
    "encode_template",
    "load_document",
    "load_project",
    "new_project",
    "project_from_bytes",
    "project_to_bytes",
    "restorable",
    "restore_document",
    "save_project",
    "save_template",
    "template_to_bytes",
]
