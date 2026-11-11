# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from cube_net.ui.updates.windows_update import SILENT, start_installer


def test_the_installer_runs_silently_on_its_own() -> None:
    started: list[list[str]] = []
    start_installer(Path("C:/Temp/CubeNet-1.2.0-windows-x64-setup.exe"), lambda command, **_: started.append(command))
    assert started == [["C:/Temp/CubeNet-1.2.0-windows-x64-setup.exe", *SILENT]]
    assert "/SILENT" in SILENT and "/CLOSEAPPLICATIONS" in SILENT
