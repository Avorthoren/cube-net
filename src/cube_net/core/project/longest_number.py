# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""How long the longest number of a project or a template is, as its file keeps it (every coordinate, the origin, the
history's states): what an action may never exceed (`MAX_NUMBER_DIGITS`), so that files made before the limit, or by
hand, can be checked against it."""

import re

from cube_net.core.geometry import digits
from cube_net.core.project.codec import encode_project
from cube_net.core.project.project import Project
from cube_net.core.project.template_codec import TemplateDocument, encode_template

# A number as a file writes it: an integer, or a fraction ("-41333/1000").
NUMBER = re.compile(r"-?(\d+)(?:/(\d+))?")


def longest_number(document: Project | TemplateDocument) -> int:
    """The most digits of a numerator or a denominator anywhere in `document` (0 if it has no numbers)."""
    data = encode_template(document) if isinstance(document, TemplateDocument) else encode_project(document)
    return _longest(data)


def _longest(data: object) -> int:
    if isinstance(data, bool):
        return 0
    if isinstance(data, int):
        return digits(data)
    if isinstance(data, str):
        found = NUMBER.fullmatch(data)
        return 0 if found is None else max(len(part) for part in found.groups() if part is not None)
    if isinstance(data, dict):
        return max((_longest(value) for value in data.values()), default=0)
    if isinstance(data, list | tuple):
        return max((_longest(item) for item in data), default=0)
    return 0
