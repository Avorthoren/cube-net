# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The README's animation: its scene works on the real editor, the animated PNG is a valid one, and the committed
file still shows the app as it draws itself now."""

import struct
import zlib

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.core.geometry import Vec
from scripts import make_readme_animation as animation


def chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """The chunks of a PNG, in order, each checked against its CRC."""
    assert data[:8] == animation.SIGNATURE
    found, position = [], 8
    while position < len(data):
        length, kind = struct.unpack(">I4s", data[position : position + 8])
        body = data[position + 8 : position + 8 + length]
        assert struct.unpack(">I", data[position + 8 + length : position + 12 + length])[0] == zlib.crc32(kind + body)
        found.append((kind, body))
        position += 12 + length
    return found


def image(colour: str, size: int = 20) -> QImage:
    picture = QImage(size, size, QImage.Format.Format_ARGB32)
    picture.fill(QColor(colour))
    return picture


def test_the_scene_cuts_glues_and_approves(qtbot: QtBot) -> None:
    demo = animation.sheet()
    qtbot.addWidget(demo)
    demo.show()
    qtbot.waitExposed(demo)
    rejected: list[Vec] = []
    demo.workspace.cut_tool.rejected.connect(rejected.append)
    editor = demo.workspace.editor
    for _ in demo.play(animation.SCENE[:-8], instant=True):  # up to the glue, its click included
        pass
    assert rejected == []
    assert editor.state is EditorState.CUT_APPROVING and editor.rearranged is not None and editor.rearranged.valid
    for _ in demo.play(animation.SCENE[-8:], instant=True):
        pass
    assert editor.state is EditorState.DEFAULT
    assert len(editor.net.vertices) > 14  # the new net


def test_the_whole_result_and_its_rectangle_are_in_the_picture(qtbot: QtBot) -> None:
    demo = animation.sheet()
    qtbot.addWidget(demo)
    for _ in demo.play(animation.SCENE, instant=True):
        pass
    assert demo.bounding_item is not None  # the bounding rectangle is shown too
    points = [v.position for v in demo.workspace.editor.net.vertices] + list(demo.bounding_item.corners())
    shown = animation.SHOWN
    assert all(shown.lo.x < p.x < shown.hi.x and shown.lo.y < p.y < shown.hi.y for p in points)


def test_only_what_changed() -> None:
    before, after = image("#FFFFFF"), image("#FFFFFF")
    assert animation._changed(before, after).isEmpty()
    after.setPixelColor(7, 3, QColor("#000000"))
    after.setPixelColor(12, 9, QColor("#000000"))
    assert animation._changed(before, after) == QRect(7, 3, 6, 7)


def test_an_animated_png(qtbot: QtBot) -> None:
    white, black = image("#FFFFFF"), image("#FFFFFF")
    black.setPixelColor(5, 5, QColor("#000000"))
    data = animation.apng([(white, 100), (white.copy(), 50), (black, 200)])
    kinds = [kind for kind, _ in chunks(data)]
    assert kinds == [b"IHDR", b"acTL", b"fcTL", b"IDAT", b"fcTL", b"fdAT", b"IEND"]
    body = dict(chunks(data))
    assert struct.unpack(">II", body[b"acTL"]) == (2, 0)  # two frames (the same one twice is one), played forever
    controls = [struct.unpack(">IIIIIHHBB", b) for k, b in chunks(data) if k == b"fcTL"]
    assert controls[0][1:7] == (20, 20, 0, 0, 150, 1000)  # the whole picture, for 100 + 50 ms
    assert controls[1][1:7] == (1, 1, 5, 5, 200, 1000)  # just the changed pixel
    assert [c[0] for c in controls] == [0, 1]  # sequence numbers (the fdAT is 2)
    assert QImage.fromData(data, "PNG").pixelColor(5, 5) == QColor("#FFFFFF")  # where it isn't played: the first


def test_the_committed_animation_shows_the_app_as_it_is(qtbot: QtBot) -> None:
    """If this fails, the app's default look has changed: run `python scripts/make_readme_animation.py`."""
    stored = QImage.fromData(animation.README_ANIMATION.read_bytes(), "PNG")
    demo = animation.sheet()
    qtbot.addWidget(demo)
    demo.show()
    qtbot.waitExposed(demo)
    QApplication.processEvents()
    fresh = demo.grab().toImage()
    form = QImage.Format.Format_ARGB32
    assert stored.convertToFormat(form) == fresh.convertToFormat(form)
