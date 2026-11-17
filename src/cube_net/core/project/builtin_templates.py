# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The templates built into the application (docs/template_plan.md, §8.3), read from the package's own files
(`cube_net.core.project.builtin`). The cube needs none: it's the application's body from the start (`new_project`)."""

from functools import cache
from importlib.resources import files

from cube_net.core.project.file import document_from_bytes
from cube_net.core.project.template_codec import TemplateDocument

# The file of the built-in Cube with a hole (scripts/embed_template.py writes it).
CUBE_WITH_A_HOLE_FILE = "cube_with_a_hole.nettemplate"


@cache
def cube_with_a_hole() -> TemplateDocument:
    """The built-in Cube with a hole: a valid template, with its style and origin (the tests make sure of that)."""
    return builtin_template(CUBE_WITH_A_HOLE_FILE)


def builtin_template(name: str) -> TemplateDocument:
    document = document_from_bytes((files("cube_net.core.project.builtin") / name).read_bytes())
    if not isinstance(document, TemplateDocument):
        raise TypeError(f"the built-in {name} isn't a template")
    return document
