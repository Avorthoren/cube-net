# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The test release is one the update check reads like GitHub's, and its package downloads and checks out."""

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from scripts.make_test_release import make

from cube_net.ui.updates.latest_release import fetch_latest_release
from cube_net.ui.updates.package_download import PackageDownload


def test_a_release_the_check_reads_and_the_download_trusts(qtbot: QtBot, tmp_path: Path) -> None:
    package = tmp_path / "CubeNet-abc1234-linux-x86_64.AppImage"
    package.write_bytes(b"an AppImage" * 1000)
    latest = make(package, "9.9.9")
    release = fetch_latest_release(latest.as_uri())
    assert release is not None and release.version == "9.9.9"
    found = release.package("linux")
    assert found is not None and found[0] == package.name
    download = PackageDownload(found[0], found[1], release.checksums(), tmp_path / "into")
    with qtbot.waitSignal(download.finished, timeout=5000) as blocker:
        download.start()
    assert blocker.args[0].read_bytes() == package.read_bytes()


def test_only_a_version(tmp_path: Path) -> None:
    package = tmp_path / "p"
    package.write_text("x")
    with pytest.raises(ValueError, match="isn't a version"):
        make(package, "1.0")
