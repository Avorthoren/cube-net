from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QImage, QPainter

from cube_net.ui import palette
from cube_net.ui.sheet.sheet_item import SheetItem


def render(item: SheetItem, scale: float) -> QImage:
    r = item.boundingRect()
    image = QImage(int(r.width() * scale) + 1, int(r.height() * scale) + 1, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    painter = QPainter(image)
    painter.scale(scale, scale)
    painter.translate(-r.left(), -r.top())
    item.paint(painter, None)
    painter.end()
    return image


def test_bounding_rect_is_sheet_rect() -> None:
    item = SheetItem(QRectF(5, 5, 13, 14))
    assert item.boundingRect() == QRectF(5, 5, 13, 14)
    item.set_rect(QRectF(0, 0, 2, 3))
    assert item.rect() == QRectF(0, 0, 2, 3)


def test_white_sheet_with_grid_on_integer_lines() -> None:
    item = SheetItem(QRectF(5, 5, 13, 14))
    image = render(item, 20)  # 20 px per unit; sheet x=5 is pixel 0
    assert image.pixelColor(30, 30) == palette.SHEET  # (6.5, 6.5): middle of a grid cell
    assert image.pixelColor(40, 30) == palette.GRID  # x = 7: a grid line


def test_empty_sheet_paints_nothing() -> None:
    SheetItem().paint(None, None)
