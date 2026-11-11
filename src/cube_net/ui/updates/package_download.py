# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`PackageDownload`: downloads this system's package of a release, in the background, and makes sure it's the one
the release published.

1. The release's SHA256SUMS: the package's checksum (a release without one isn't installed: what was downloaded
   couldn't be told from something broken or changed on the way).
2. The package, a piece at a time, into "<name>.part" next to where it goes: the progress is told as it goes, and
   `cancel` stops it. Its SHA-256 is worked out on the way.
3. Only if it's the published one, it gets its name; otherwise it's deleted, and the download fails saying why.
"""

import hashlib
import ssl
import threading
import urllib.error
import urllib.request
from pathlib import Path

import certifi
from PyQt6.QtCore import QObject, pyqtSignal

from cube_net import __version__
from cube_net.ui.updates.latest_release import CHECKSUMS, ReleaseFile

# How much is read at a time (bytes), and how long to wait for an answer (s).
CHUNK = 256 * 1024
TIMEOUT_S = 30


class DownloadError(Exception):
    """The package couldn't be downloaded, or isn't the published one: the message says why."""


class DownloadCancelled(Exception):
    pass


def expected_checksum(sums: str, name: str) -> str:
    """The SHA-256 of `name` in a SHA256SUMS file ("<hex>  <name>" lines, as `sha256sum` writes them)."""
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == name:
            return parts[0].lower()
    raise DownloadError(f"{CHECKSUMS} has no checksum of {name}")


class PackageDownload(QObject):
    # Bytes downloaded so far, of how many (0: not known).
    progress = pyqtSignal(int, int)

    # The downloaded package, checked.
    finished = pyqtSignal(object)

    # Why it didn't work.
    failed = pyqtSignal(str)

    # It was cancelled (nothing is left of it).
    cancelled = pyqtSignal()

    def __init__(
        self,
        name: str,
        package: ReleaseFile,
        checksums: ReleaseFile | None,
        folder: Path,
        parent: QObject | None = None,
    ) -> None:
        """`name` and `package`: what to download; `checksums`: the release's SHA256SUMS; `folder`: where it goes."""
        super().__init__(parent)
        self._name, self._package, self._checksums, self._folder = name, package, checksums, folder
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="update download", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._stop.set()

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        try:
            path = self.download()
        except DownloadCancelled:
            self.cancelled.emit()
        except DownloadError as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")
        else:
            self.finished.emit(path)

    def download(self) -> Path:
        """The whole download, in this thread: the package's path, checked."""
        if self._checksums is None:
            raise DownloadError(f"the release has no {CHECKSUMS}: the download couldn't be checked")
        with _open(self._checksums.url) as response:
            expected = expected_checksum(response.read().decode("utf-8", "replace"), self._name)
        self._folder.mkdir(parents=True, exist_ok=True)
        target = self._folder / self._name
        partial = self._folder / (self._name + ".part")
        digest = hashlib.sha256()
        try:
            with _open(self._package.url) as response, open(partial, "wb") as out:
                total = int(response.headers.get("Content-Length") or self._package.size or 0)
                done = 0
                while chunk := response.read(CHUNK):
                    if self._stop.is_set():
                        raise DownloadCancelled
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    self.progress.emit(done, total)
            if digest.hexdigest() != expected:
                raise DownloadError("the downloaded file isn't the published one (its checksum differs): try again")
            partial.replace(target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        return target


def _open(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": f"Cube-Net/{__version__}"})
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        return urllib.request.urlopen(request, timeout=TIMEOUT_S, context=context)
    except urllib.error.HTTPError as error:
        raise DownloadError(f"the download answered {error.code} ({error.reason})") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise DownloadError(str(getattr(error, "reason", error))) from None
