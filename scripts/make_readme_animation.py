# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make the README's animation: `python scripts/make_readme_animation.py` (about 20 s) writes `README_ANIMATION`.

RUN IT AGAIN WHENEVER THE APPLICATION'S DEFAULT LOOK CHANGES: the default style (`cube_net.ui.style.DEFAULT_STYLE`,
from `net_style` and `palette`), how the sheet, the net, the cut line and the approve button are drawn, and how the
mouse pointer looks over them (`cursors.py`, and the arrow of `ui/help/demo/pointer.py`). A test fails when the
animation's first picture no longer matches how the app draws it.

It's the app itself: the cut is played with the real net, editor and tools (Help -> Help's animation engine,
`ui/help/demo`), in the default style, without the vertex labels but with the bounding rectangle (as the Bounds
button shows it), and recorded as it plays. The file is an animated
PNG (APNG): GitHub shows it like any picture and browsers play it, in full colour (a GIF has 256 colours); each frame
keeps only the part of the picture that changed, so it stays small. Where animations aren't played, its first
picture shows: the default net.
"""

import struct
import sys
import time
import zlib
from collections.abc import Sequence
from fractions import Fraction as F
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QRect, QSize, QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from cube_net.core.geometry import Box, Vec
from cube_net.ui.help.demo.demo_sheet import DemoSheet
from cube_net.ui.help.demo.steps import Move, Step, Wait, click

ROOT = Path(__file__).resolve().parent.parent
README_ANIMATION = ROOT / "docs/media/cube-net.png"

# The picture's size, and what it shows: the default net, the net the cut makes, and the bounding rectangles of both
# (the new one reaches further left, right and down), with a little room around.
SIZE = QSize(600, 600)
SHOWN = Box(Vec(F(87, 10), F(77, 10)), Vec(F(153, 10), F(143, 10)))

# How often a frame is taken (ms), and how long the first and the last picture stay before the animation starts again.
FRAME_MS = 40
FIRST_MS = 1200
LAST_MS = 2500

# A little inside a cut (units): within its hitbox at this size.
INSIDE = 0.03

# The cut: from A_1 through the right arm (face 3) and the left arm (face 4) to F_1; the half with the counterpart of
# F_1-B_3 is glued onto it, and the rearrangement is approved (its button is in the middle of F_1-B_3).
SCENE: list[Step] = [
    Move((13.4, 10.6), 0),
    Wait(400),
    Move((11.0, 14.0), 1000),
    Wait(250),
    *click(),
    Wait(300),
    Move((12.2, 12.4), 900),
    Wait(250),
    *click(),
    Wait(300),
    Move((10.8, 12.6), 1000),
    Wait(250),
    *click(),
    Wait(300),
    Move((12.0, 11.0), 900),
    Wait(250),
    *click(),
    Wait(600),
    Move((12.0 - INSIDE, 10.5), 900),
    Wait(800),  # its counterpart blinks
    *click(),
    Wait(1200),
    Move((12.0, 10.5), 500),
    Wait(400),
    *click(),
    Wait(400),
    Move((13.9, 9.4), 800),
]


def sheet() -> DemoSheet:
    """The animation's sheet, with the mouse where the scene starts."""
    demo = DemoSheet(SIZE, SHOWN, labels=False, bounds=True)
    first = SCENE[0]
    assert isinstance(first, Move)
    demo.place(first.to)
    return demo


def record(app: QApplication) -> list[tuple[QImage, int]]:
    """Play the scene in real time (the app's own timers run: blinking, the rings of clicks) and take a frame every
    `FRAME_MS`: the frames and how long each one shows (ms)."""
    demo = sheet()
    demo.show()
    app.processEvents()
    frames: list[tuple[QImage, float]] = []
    run = demo.play(SCENE)
    done = False

    def step() -> None:
        nonlocal done
        try:
            QTimer.singleShot(next(run), step)
        except StopIteration:
            done = True

    def take() -> None:
        frames.append((demo.grab().toImage().convertToFormat(QImage.Format.Format_ARGB32), time.monotonic()))

    camera = QTimer()
    camera.setInterval(FRAME_MS)
    camera.timeout.connect(take)
    take()
    first_until = time.monotonic() + FIRST_MS / 1000
    while time.monotonic() < first_until:
        app.processEvents()
    camera.start()
    step()
    while not done:
        app.processEvents()
        time.sleep(0.002)
    last_until = time.monotonic() + LAST_MS / 1000
    while time.monotonic() < last_until:
        app.processEvents()
        time.sleep(0.002)
    camera.stop()
    take()
    timed = []
    for (image, at), (_, following) in zip(frames, [*frames[1:], (None, frames[-1][1] + LAST_MS / 1000)], strict=True):
        timed.append((image, max(1, round((following - at) * 1000))))
    return timed


# --- the animated PNG --------------------------------------------------------------------------------------------

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def apng(frames: Sequence[tuple[QImage, int]]) -> bytes:
    """An animated PNG of `frames` (pictures of one size, and how long each shows in ms), played again and again.
    A frame the same as the one before only makes that one last longer; any other keeps just the rectangle of what
    changed, drawn over what was there."""
    merged: list[tuple[QImage, QRect, int]] = []
    previous: QImage | None = None
    for image, ms in frames:
        changed = QRect(0, 0, image.width(), image.height()) if previous is None else _changed(previous, image)
        if changed.isEmpty():
            last_image, last_rect, last_ms = merged[-1]
            merged[-1] = (last_image, last_rect, last_ms + ms)
        else:
            merged.append((image, changed, ms))
            previous = image
    first = _chunks(_png(merged[0][0]))
    out = [SIGNATURE, _chunk(b"IHDR", first[b"IHDR"][0]), _chunk(b"acTL", struct.pack(">II", len(merged), 0))]
    sequence = 0
    for i, (image, rect, ms) in enumerate(merged):
        control = struct.pack(">IIIIIHHBB", sequence, rect.width(), rect.height(), rect.x(), rect.y(), ms, 1000, 0, 0)
        out.append(_chunk(b"fcTL", control))
        sequence += 1
        parts = _chunks(_png(image.copy(rect)))
        assert parts[b"IHDR"][0][8:] == first[b"IHDR"][0][8:], "every frame is RGBA, 8 bits a channel"
        for data in parts[b"IDAT"]:
            if i == 0:
                out.append(_chunk(b"IDAT", data))
            else:
                out.append(_chunk(b"fdAT", struct.pack(">I", sequence) + data))
                sequence += 1
    out.append(_chunk(b"IEND", b""))
    return b"".join(out)


def _changed(before: QImage, after: QImage) -> QRect:
    """The smallest rectangle with every pixel that differs (an empty one if none does)."""
    line = after.bytesPerLine()
    a, b = (
        bytes(before.constBits().asstring(before.sizeInBytes())),
        bytes(after.constBits().asstring(line * after.height())),
    )
    rows = [y for y in range(after.height()) if a[y * line : (y + 1) * line] != b[y * line : (y + 1) * line]]
    if not rows:
        return QRect()
    left, right = line, 0
    for y in rows:
        row_a, row_b = a[y * line : (y + 1) * line], b[y * line : (y + 1) * line]
        left = min(left, _first_difference(row_a, row_b))
        right = max(right, line - _first_difference(row_a[::-1], row_b[::-1]))
    return QRect(left // 4, rows[0], (right + 3) // 4 - left // 4, rows[-1] - rows[0] + 1)


def _first_difference(a: bytes, b: bytes) -> int:
    """The first index where `a` and `b` differ (they differ somewhere): halving, comparing whole slices at once."""
    low, high = 0, len(a)
    while high - low > 1:
        middle = (low + high) // 2
        if a[low:middle] != b[low:middle]:
            high = middle
        else:
            low = middle
    return low


def _png(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def _chunks(png: bytes) -> dict[bytes, list[bytes]]:
    """The chunks of a PNG, by type."""
    found: dict[bytes, list[bytes]] = {}
    position = len(SIGNATURE)
    while position < len(png):
        length, kind = struct.unpack(">I4s", png[position : position + 8])
        found.setdefault(kind, []).append(png[position + 8 : position + 8 + length])
        position += 12 + length
    return found


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def main() -> int:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    frames = record(app)
    data = apng(frames)
    README_ANIMATION.parent.mkdir(parents=True, exist_ok=True)
    README_ANIMATION.write_bytes(data)
    total = sum(ms for _, ms in frames) / 1000
    print(f"{README_ANIMATION.relative_to(ROOT)}: {len(frames)} frames, {total:.1f} s, {len(data) / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
