import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.core.net import Net, default_net
from cube_net.core.sheet import sheet_box
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cut_hover import CutHover
from cube_net.ui.sheet.sheet_view import SheetView


@pytest.fixture
def setup(qtbot: QtBot) -> tuple[SheetView, CutHover, Net]:
    net = default_net()
    view = SheetView()
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.set_sheet(sheet_box(v.position for v in net.vertices))
    view.set_net(net)
    view.set_net_hit_test(lambda x, y: net.contains(Vec(round(x * 1000), round(y * 1000)) / 1000))
    view.show_initial_view(net.bounding_box())
    view.show()
    qtbot.waitExposed(view)
    return view, CutHover(view, net), net


def move(qtbot: QtBot, view: SheetView, target: QPoint) -> None:
    """QTest sends no move event if the cursor is already there (e.g. left there by another test): step aside first."""
    qtbot.mouseMove(view.viewport(), target + QPoint(1, 1))
    qtbot.mouseMove(view.viewport(), target)


# Half the hitbox: always inside it, whatever net_style says.
HALF_HITBOX = net_style.CUT_HITBOX_PX / 2


def near_cut(view: SheetView) -> float:
    """x (sheet units) half a hitbox inside face 4 from the cut A_2 - E_2 at x = 10."""
    return 10 + HALF_HITBOX / view.scale_factor()


def px_inside(view: SheetView, x: float, y: float, dx_px: float) -> QPoint:
    """Viewport pixel at sheet (x, y), shifted dx_px pixels to the right."""
    return (view.from_sheet(QPointF(x, y)) + QPointF(dx_px, 0)).toPoint()


def test_moving_near_a_cut_highlights_it(setup: tuple[SheetView, CutHover, Net], qtbot: QtBot) -> None:
    view, hover, _ = setup
    move(qtbot, view, px_inside(view, 10, 12.5, HALF_HITBOX))  # inside face 4, within the hitbox of A_2 - E_2
    cut = hover.hovered()
    assert cut is not None
    assert {cut.origin.position, cut.destination.position} == {Vec(10, 13), Vec(10, 12)}


def test_moving_away_or_leaving_clears(setup: tuple[SheetView, CutHover, Net], qtbot: QtBot) -> None:
    view, hover, _ = setup
    move(qtbot, view, px_inside(view, 10, 12.5, HALF_HITBOX))
    assert hover.hovered() is not None
    move(qtbot, view, px_inside(view, 11.5, 12.5, 0))  # middle of face 2
    assert hover.hovered() is None
    move(qtbot, view, px_inside(view, 10, 12.5, HALF_HITBOX))
    view.mouse_left.emit()
    assert hover.hovered() is None


def test_hitbox_is_inside_the_face_only(setup: tuple[SheetView, CutHover, Net], qtbot: QtBot) -> None:
    view, hover, _ = setup
    move(qtbot, view, px_inside(view, 10, 12.5, -HALF_HITBOX))  # just outside the net
    assert hover.hovered() is None


def test_no_highlight_while_panning(setup: tuple[SheetView, CutHover, Net], qtbot: QtBot) -> None:
    view, hover, _ = setup
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=px_inside(view, 7, 7, 0))
    hover.update_at(near_cut(view), 12.5)
    assert hover.hovered() is None
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=px_inside(view, 7, 7, 0))
    hover.update_at(near_cut(view), 12.5)
    assert hover.hovered() is not None


def test_set_net_clears(setup: tuple[SheetView, CutHover, Net]) -> None:
    view, hover, net = setup
    hover.update_at(near_cut(view), 12.5)
    hover.set_net(net)
    assert hover.hovered() is None


def test_vertex_is_highlighted_instead_of_its_cuts(setup: tuple[SheetView, CutHover, Net]) -> None:
    view, hover, _ = setup
    near = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    hover.update_at(11 + near, 14 - near)  # inside the circle of A_1, also inside the hitboxes of its cuts
    vertex = hover.hovered_vertex()
    assert vertex is not None and vertex.position == Vec(11, 14)
    assert hover.hovered() is None
    hover.update_at(11.5, 12.5)
    assert hover.hovered_vertex() is None
