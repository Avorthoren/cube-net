# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from pathlib import Path

import pytest

from cube_net.ui.updates.installation import ManualStepNeeded
from cube_net.ui.updates.macos_update import SWAP, install_macos, open_in_finder


def test_a_script_does_it_after_the_app_quit(tmp_path: Path) -> None:
    bundle = tmp_path / "Applications" / "Cube Net.app"
    bundle.mkdir(parents=True)
    dmg = tmp_path / "update" / "CubeNet-1.2.0-macos-arm64.dmg"
    dmg.parent.mkdir()
    dmg.write_text("dmg")
    started: list[list[str]] = []
    install_macos(dmg, bundle, 4321, lambda command, **_: started.append(command))
    script = dmg.parent / "update.sh"
    assert script.read_text() == SWAP
    assert started == [["/bin/sh", str(script), "4321", str(dmg), str(bundle)]]


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_by_hand_if_the_app_cant_be_replaced(tmp_path: Path) -> None:
    folder = tmp_path / "Applications"
    bundle = folder / "Cube Net.app"
    bundle.mkdir(parents=True)
    folder.chmod(0o555)
    try:
        with pytest.raises(ManualStepNeeded):
            install_macos(tmp_path / "x.dmg", bundle, 1, lambda command, **_: None)
    finally:
        folder.chmod(0o755)


def test_the_script_waits_swaps_and_restores() -> None:
    assert 'while kill -0 "$pid"' in SWAP  # waits for the app to quit
    assert 'mv "$bundle" "$bundle.old" && mv "$bundle.new" "$bundle"' in SWAP
    assert 'rm -rf "$bundle.new"' in SWAP  # a failed copy leaves the old one as it was
    assert SWAP.rstrip().endswith('open "$bundle"')


def test_finder_shows_the_dmg() -> None:
    started: list[list[str]] = []
    open_in_finder(Path("/tmp/x.dmg"), lambda command, **_: started.append(command))
    assert started == [["open", "/tmp/x.dmg"]]
