# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The core package must never depend on Qt (docs/plan.md, section 1)."""

import pathlib

import cube_net.core

CORE_DIR = pathlib.Path(cube_net.core.__file__).parent


def test_core_does_not_import_qt() -> None:
    offenders = [
        path.name
        for path in CORE_DIR.rglob("*.py")
        if "PyQt" in path.read_text(encoding="utf-8") or "PySide" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
