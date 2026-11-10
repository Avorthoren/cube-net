# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The icon: the default net in the default colours, transparent around it, in the files each system needs."""

import struct

import pytest
from PyQt6.QtGui import QColor, QImage
from pytestqt.qtbot import QtBot

from cube_net.ui.style import DEFAULT_STYLE
from scripts import make_icon


@pytest.mark.parametrize("size", [16, 32, 256, 1024])
def test_the_faces_in_their_colours_and_nothing_around(qtbot: QtBot, size: int) -> None:
    image = make_icon.draw(size)
    assert (image.width(), image.height()) == (size, size)
    assert image.pixelColor(0, 0).alpha() == 0  # a corner: outside the net
    assert image.pixelColor(size - 1, size - 1).alpha() == 0
    # The cross is 3 x 4 faces: the middle of its column is face 2 (orange), its top face 1 (blue).
    colours = {face: QColor(DEFAULT_STYLE.face_colors[face - 1]) for face in range(1, 7)}
    middle = image.pixelColor(size // 2, int(size * 0.42))
    assert middle == colours[2]
    used = {image.pixelColor(x, y).name().upper() for x in range(0, size, max(1, size // 64)) for y in range(size)}
    assert {c.name().upper() for c in colours.values()} <= used  # all six faces, nothing else but transparency
    assert used <= {c.name().upper() for c in colours.values()} | {"#000000"}


def test_small_sizes_have_sharp_edges(qtbot: QtBot) -> None:
    image = make_icon.draw(16)
    alphas = {image.pixelColor(x, y).alpha() for x in range(16) for y in range(16)}
    assert alphas == {0, 255}  # no blurred pixels


def test_the_windows_file_holds_every_size(qtbot: QtBot) -> None:
    data = make_icon.ico(make_icon.WINDOWS_SIZES)
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind, count) == (0, 1, len(make_icon.WINDOWS_SIZES))
    for i, size in enumerate(make_icon.WINDOWS_SIZES):
        width, _, _, _, _, _, length, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i : 22 + 16 * i])
        assert width == (0 if size == 256 else size)
        picture = QImage.fromData(data[offset : offset + length], "PNG")
        assert picture.width() == size


def test_the_mac_file_holds_every_type(qtbot: QtBot) -> None:
    data = make_icon.icns()
    assert data[:4] == b"icns" and struct.unpack(">I", data[4:8])[0] == len(data)
    position, found = 8, {}
    while position < len(data):
        kind, length = data[position : position + 4], struct.unpack(">I", data[position + 4 : position + 8])[0]
        found[kind] = QImage.fromData(data[position + 8 : position + length], "PNG").width()
        position += length
    assert found == dict(make_icon.MAC_TYPES)


def pictures(path_bytes: bytes) -> list[QImage]:
    """The pictures of an icon file (PNG, ICO or ICNS), in order."""
    if path_bytes[:4] == b"icns":
        found, position = [], 8
        while position < len(path_bytes):
            length = struct.unpack(">I", path_bytes[position + 4 : position + 8])[0]
            found.append(QImage.fromData(path_bytes[position + 8 : position + length], "PNG"))
            position += length
        return found
    if path_bytes[:4] == b"\x00\x00\x01\x00":
        count = struct.unpack("<H", path_bytes[4:6])[0]
        entries = [struct.unpack("<BBBBHHII", path_bytes[6 + 16 * i : 22 + 16 * i]) for i in range(count)]
        return [QImage.fromData(path_bytes[offset : offset + length], "PNG") for *_, length, offset in entries]
    return [QImage.fromData(path_bytes, "PNG")]


def same(a: QImage, b: QImage) -> bool:
    form = QImage.Format.Format_ARGB32
    return a.convertToFormat(form) == b.convertToFormat(form)


def test_the_files_are_up_to_date(qtbot: QtBot) -> None:
    """If the net or the default colours change, run `python scripts/make_icon.py`. (The pictures are compared, not
    the bytes: another machine's PNG encoder may write the same picture differently.)"""
    for path, content in make_icon.icons().items():
        stored, fresh = pictures(path.read_bytes()), pictures(content)
        assert len(stored) == len(fresh), path
        assert all(same(a, b) for a, b in zip(stored, fresh, strict=True)), path
