# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make the README's animation: `python scripts/make_readme_animation.py` (about 30 s) writes `README_ANIMATION`.

RUN IT AGAIN WHENEVER THE APPLICATION'S LOOK CHANGES: how the sheet, the net, the cut line, the approve button, the
right click's menu and Place a vertex's window are drawn, and how the mouse pointer looks over them (`cursors.py`, and
the arrow of `ui/help/demo/pointer.py`). A test fails when the animation's first picture no longer matches how the app
draws it.

It starts from the author's project `BASIS` (a copy of their torus project: a net of the Cube with a hole, with its
own style): to start from another one, copy the project file there and write the scene anew (its points are that
net's). It's the app itself: the cut is played with the real net, editor and tools (Help -> Help's animation engine,
`ui/help/demo`), in the project's style, without the vertex labels but with the bounding rectangle (as the Bounds
button shows it), and recorded as it plays. The menu and the window are the real ones too, shown in the picture of
the sheet. The file is an animated PNG (APNG): GitHub shows it like any picture and browsers play it, in full colour
(a GIF has 256 colours); each frame keeps only the part of the picture that changed, so it stays small. Where
animations aren't played, its first picture shows: the project's net.
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
from cube_net.core.project import Project, load_project
from cube_net.ui import palette
from cube_net.ui.help.demo.demo_sheet import DemoSheet
from cube_net.ui.help.demo.steps import Move, RightClick, Step, ToItem, Type, Wait, click
from cube_net.ui.sheet.sheet_context_menu import PLACE_VERTEX
from cube_net.ui.style import apply_style

ROOT = Path(__file__).resolve().parent.parent
README_ANIMATION = ROOT / "docs/media/readme-animation-net.png"

# The project the animation starts from.
BASIS = ROOT / "scripts/readme_animation.cubenet"

# The picture's size, and what it shows: the project's net, the net the cut makes, and the bounding rectangles of both
# (the new one reaches further left), with a little room around.
SIZE = QSize(600, 720)
SHOWN = Box(Vec(F(354, 10), F(438, 10)), Vec(F(557, 10), F(681, 10)))

# How often a frame is taken (ms), and how long the first and the last picture stay before the animation starts again.
FRAME_MS = 40
FIRST_MS = 1200
LAST_MS = 2500

# A little inside a cut (units): within its hitbox at this size.
INSIDE = 0.08

# The cut: from the top of the blue face, by clicks, to (45, 61) and (47, 57); its end is typed in Place a vertex's
# window, at (37, 63) from the origin's (44, 50): off the net, so the line ends where it leaves the net.
CUT: list[Step] = [
    Move((53.0, 67.0), 0),
    Wait(400),
    Move((48.0, 66.0), 1000),
    Wait(250),
    *click(),
    Wait(300),
    Move((45.0, 61.0), 900),
    Wait(250),
    *click(),
    Wait(300),
    Move((47.0, 57.0), 900),
    Wait(250),
    *click(),
    Wait(300),
    Move((37.1, 62.9), 1100),
    Wait(400),
    RightClick(),
    Wait(600),
    ToItem(PLACE_VERTEX, 500),
    Wait(250),
    *click(),
    Wait(700),
    Type("13"),
    Wait(300),
    Type("\t\t", 300),
    Type("-7"),
    Wait(700),
    Type("\n"),
    Wait(900),
]

# The rearrangement: the half with the counterpart of the cut left of the origin, (44, 50.8)-(44, 50), is glued onto
# it, and approved (the button is in its middle).
GLUE: list[Step] = [
    Move((44.0 + INSIDE, 50.5), 1000),
    Wait(800),  # its counterpart blinks
    *click(),
    Wait(1200),
    Move((44.0, 50.4), 500),
    Wait(400),
    *click(),
    Wait(400),
    Move((51.5, 64.0), 800),
]

SCENE: list[Step] = [*CUT, *GLUE]


def basis() -> Project:
    """The project the animation starts from, its style and face colours put in place (they're global)."""
    project = load_project(BASIS)
    style, colors = project.settings.style, project.settings.face_colors
    assert style is not None and colors is not None, "the basis is saved with its style and colours"
    apply_style(style)
    palette.set_face_colors(colors, project.state.net.body)
    return project


def sheet() -> DemoSheet:
    """The animation's sheet, with the mouse where the scene starts."""
    demo = DemoSheet(SIZE, SHOWN, labels=False, bounds=True, project=basis())
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
