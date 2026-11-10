# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The project is free software under the GNU GPL v3 or later: the license is there, and every source file says so."""

import pathlib
import tomllib

ROOT = pathlib.Path(__file__).parent.parent

# What every Python file of the project starts with.
HEADER = "# Copyright (C) 2026 Viktor Podust\n# SPDX-License-Identifier: GPL-3.0-or-later\n"


def test_the_license_text() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.lstrip().startswith("GNU GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007")
    assert "END OF TERMS AND CONDITIONS" in text


def test_the_package_says_so() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == "GPL-3.0-or-later"
    assert project["license-files"] == ["LICENSE"]


def test_every_python_file_starts_with_the_notice() -> None:
    files = [*ROOT.glob("*.py"), *(ROOT / "src").rglob("*.py"), *(ROOT / "tests").rglob("*.py")]
    missing = [str(f.relative_to(ROOT)) for f in files if not f.read_text(encoding="utf-8").startswith(HEADER)]
    assert len(files) > 200
    assert missing == []
