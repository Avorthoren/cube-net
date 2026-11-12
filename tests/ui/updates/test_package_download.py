# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Downloading a package (from local files: urllib reads file:// URLs too, so no network is needed)."""

import hashlib
import re
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from cube_net.ui.updates import package_download
from cube_net.ui.updates.latest_release import ReleaseFile
from cube_net.ui.updates.package_download import DownloadError, PackageDownload, expected_checksum

NAME = "CubeNet-1.2.0-linux-x86_64.AppImage"


def published(tmp_path: Path, content: bytes, checksum: str | None = None) -> tuple[ReleaseFile, ReleaseFile]:
    """The package and SHA256SUMS of a release, as files."""
    source = tmp_path / "release"
    source.mkdir(exist_ok=True)
    (source / NAME).write_bytes(content)
    sums = source / "SHA256SUMS"
    digest = checksum or hashlib.sha256(content).hexdigest()
    sums.write_text(f"{digest}  {NAME}\nabc  CubeNet-1.2.0-macos-arm64.dmg\n")
    return ReleaseFile(len(content), (source / NAME).as_uri()), ReleaseFile(100, sums.as_uri())


def test_the_checksum_of_a_file() -> None:
    assert expected_checksum("ABC  a.dmg\ndef  *b.exe\n", "b.exe") == "def"
    assert expected_checksum("ABC  a.dmg\n", "a.dmg") == "abc"
    with pytest.raises(DownloadError, match=re.escape("no checksum of c.exe")):
        expected_checksum("abc  a.dmg\n", "c.exe")


def test_downloaded_and_checked(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(package_download, "CHUNK", 1000)
    content = bytes(range(256)) * 20
    package, sums = published(tmp_path, content)
    download = PackageDownload(NAME, package, sums, tmp_path / "into")
    seen: list[tuple[int, int]] = []
    download.progress.connect(lambda done, total: seen.append((done, total)))
    with qtbot.waitSignal(download.finished, timeout=5000) as blocker:
        download.start()
    path = blocker.args[0]
    assert path == tmp_path / "into" / NAME and path.read_bytes() == content
    qtbot.waitUntil(lambda: len(seen) == 6)  # its pieces of 1000 bytes
    assert seen[-1] == (len(content), len(content))
    assert not (tmp_path / "into" / (NAME + ".part")).exists()


def test_not_the_published_one(qtbot: QtBot, tmp_path: Path) -> None:
    package, sums = published(tmp_path, b"changed on the way", checksum="0" * 64)
    download = PackageDownload(NAME, package, sums, tmp_path / "into")
    with qtbot.waitSignal(download.failed, timeout=5000) as blocker:
        download.start()
    assert "isn't the published one" in blocker.args[0]
    assert list((tmp_path / "into").iterdir()) == []  # nothing left


def test_no_checksums_no_install(qtbot: QtBot, tmp_path: Path) -> None:
    package, _ = published(tmp_path, b"package")
    download = PackageDownload(NAME, package, None, tmp_path / "into")
    with qtbot.waitSignal(download.failed, timeout=5000) as blocker:
        download.start()
    assert "has no SHA256SUMS" in blocker.args[0]


class HeldBack:
    """A package that comes a piece at a time, and after its first piece waits until the download is cancelled: the
    cancel always comes in the middle of the download (a local file would be read to its end before the test's
    cancel, sent through the window's thread, reached the download)."""

    def __init__(self, download: PackageDownload) -> None:
        self.headers = {"Content-Length": "1000"}
        self.download = download
        self.pieces = 0

    def __enter__(self) -> HeldBack:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def read(self, size: int) -> bytes:
        self.pieces += 1
        if self.pieces > 1:
            assert self.download._stop.wait(timeout=5), "never cancelled"
        return b"x" * size


def test_cancelled(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr(package_download, "CHUNK", 10)
    package, sums = published(tmp_path, b"x" * 1000)
    download = PackageDownload(NAME, package, sums, tmp_path / "into")
    real_open = package_download._open
    monkeypatch.setattr(
        package_download,
        "_open",
        lambda url: HeldBack(download) if url == package.url else io.BytesIO(real_open(url).read()),
    )
    download.progress.connect(lambda done, total: download.cancel())
    with qtbot.waitSignal(download.cancelled, timeout=5000):
        download.start()
    qtbot.waitUntil(lambda: not download.running())
    assert list((tmp_path / "into").iterdir()) == []  # nothing left of it


def test_a_missing_file_says_so(qtbot: QtBot, tmp_path: Path) -> None:
    _, sums = published(tmp_path, b"package")
    gone = ReleaseFile(7, (tmp_path / "nowhere").as_uri())
    download = PackageDownload(NAME, gone, sums, tmp_path / "into")
    with qtbot.waitSignal(download.failed, timeout=5000) as blocker:
        download.start()
    assert blocker.args[0]
