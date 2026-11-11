# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""PyInstaller's recipe for the application (`scripts/build.py` runs it): one folder with the program and everything
it needs (Python, Qt, the icon, the license), "Cube Net.app" on macOS. No console window."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent  # noqa: F821 (PyInstaller gives it)
sys.path.insert(0, str(ROOT))
from scripts.build import NAME, numbers, version  # noqa: E402

VERSION = version()
ICON = {"win32": ROOT / "packaging/icons/cube_net.ico", "darwin": ROOT / "packaging/icons/cube_net.icns"}.get(
    sys.platform
)

a = Analysis(  # noqa: F821
    [str(ROOT / "main.py")],
    pathex=[str(ROOT / "src")],
    datas=[*collect_data_files("cube_net"), (str(ROOT / "LICENSE"), ".")],
    excludes=["tkinter", "unittest", "pytest", "hypothesis", "PyQt6.QtTest"],
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    console=False,
    icon=str(ICON) if ICON else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME)  # noqa: F821

if sys.platform == "darwin":
    plain = numbers(VERSION)
    app = BUNDLE(  # noqa: F821
        coll,
        name=f"{NAME}.app",
        icon=str(ICON),
        bundle_identifier="io.github.avorthoren.cubenet",
        version=plain,
        info_plist={
            "CFBundleShortVersionString": plain,
            "CFBundleVersion": plain,
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "Copyright © 2026 Viktor Podust. GNU GPL v3 or later.",
        },
    )
