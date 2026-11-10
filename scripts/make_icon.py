# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Draw the application's icon: the default cube net, each face filled with its default colour, transparent around it.

`python scripts/make_icon.py` writes, from the net and the colours themselves (run it again if they ever change; a
test says when the files are out of date):
- `src/cube_net/ui/icons/cube_net.png`: the window icon (256 px), also the Linux build's icon;
- `packaging/icons/cube_net.ico`: Windows, 16 to 256 px in one file;
- `packaging/icons/cube_net.icns`: macOS, 16 to 1024 px in one file.
Both multi-size files hold PNG pictures, which every Windows since Vista and every macOS since 10.7 read.
"""

import struct
import sys
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

from cube_net.core.net import Net, default_net
from cube_net.ui.style import DEFAULT_STYLE

ROOT = Path(__file__).resolve().parent.parent
WINDOW_ICON = ROOT / "src/cube_net/ui/icons/cube_net.png"
WINDOWS_ICON = ROOT / "packaging/icons/cube_net.ico"
MAC_ICON = ROOT / "packaging/icons/cube_net.icns"

# The window icon's size, and the sizes in the Windows and macOS files.
WINDOW_SIZE = 256
WINDOWS_SIZES = (16, 24, 32, 48, 64, 128, 256)

# macOS's icon types, by the size of their picture (the @2x ones are those of the next size, sharper).
MAC_TYPES = (
    (b"icp4", 16),
    (b"icp5", 32),
    (b"icp6", 64),
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024),
    (b"ic11", 32),
    (b"ic12", 64),
    (b"ic13", 256),
    (b"ic14", 512),
)

# Up to this size the net fills the whole height (every pixel counts); larger icons leave a margin, as icons do.
FULL_HEIGHT_UP_TO = 48
MARGIN = 0.06


def draw(size: int) -> QImage:
    """The icon, `size` x `size` pixels: the faces as squares of whole pixels, so that their edges are sharp."""
    net = default_net()
    box = net.bounding_box()
    width, height = int(box.width), int(box.height)  # in faces: 3 x 4
    space = size if size <= FULL_HEIGHT_UP_TO else size * (1 - 2 * MARGIN)
    unit = int(space // max(width, height))
    left = (size - width * unit) // 2
    top = (size - height * unit) // 2
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setPen(Qt.PenStyle.NoPen)
    for region in net.regions:
        corners = [he.origin.position for he in Net.region_cycle(region)]
        x = int(min(c.x for c in corners) - box.lo.x)
        y = int(box.hi.y - max(c.y for c in corners))  # the sheet's y goes up, the picture's down
        painter.setBrush(QColor(DEFAULT_STYLE.face_colors[region.face - 1]))
        painter.drawRect(QRect(left + x * unit, top + y * unit, unit, unit))
    painter.end()
    return image


def png(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def ico(sizes: tuple[int, ...]) -> bytes:
    """A Windows icon file with a picture of each size."""
    pictures = [png(draw(size)) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = len(header) + 16 * len(sizes)
    entries, data = b"", b""
    for size, picture in zip(sizes, pictures, strict=True):
        side = 0 if size >= 256 else size  # 0 means 256 there
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(picture), offset + len(data))
        data += picture
    return header + entries + data


def icns() -> bytes:
    """A macOS icon file with a picture of each type."""
    body = b"".join(kind + struct.pack(">I", 8 + len(p)) + p for kind, p in ((k, png(draw(s))) for k, s in MAC_TYPES))
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def icons() -> dict[Path, bytes]:
    """Every icon file and what it holds."""
    return {WINDOW_ICON: png(draw(WINDOW_SIZE)), WINDOWS_ICON: ico(WINDOWS_SIZES), MAC_ICON: icns()}


def main() -> int:
    for path, content in icons().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"{path.relative_to(ROOT)}: {len(content)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
