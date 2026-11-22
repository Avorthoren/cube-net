# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The author's torus project (`torus.cubenet`, a copy of their own): a net of the Cube with a hole, in its own style.
Help's Advanced features animation and the README's animation start from it. Their scenes are written for its net:
after replacing the file, write them anew."""

from functools import cache
from importlib.resources import files

from cube_net.core.project import Project, project_from_bytes

# The project's file, in this package.
TORUS_FILE = "torus.cubenet"


@cache
def torus_project() -> Project:
    return project_from_bytes((files("cube_net.ui.help.demo") / TORUS_FILE).read_bytes())
