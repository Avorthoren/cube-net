# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.core.net import default_net
from cube_net.core.sheet import sheet_box
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.sheet.workspace import Workspace


def make(qtbot: QtBot, mouse_cursor: bool = True) -> tuple[SheetView, Workspace]:
    net = default_net()
    view = SheetView()
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.set_sheet(sheet_box(v.position for v in net.vertices))
    view.set_net(net)
    workspace = Workspace(view, net, mouse_cursor)
    view.show_initial_view(net.bounding_box())
    view.show()
    qtbot.waitExposed(view)
    return view, workspace


def corner_cut(view: SheetView) -> None:
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - inside)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside, 13.5)


def test_a_rearrangement_is_shown_and_announced(qtbot: QtBot) -> None:
    view, workspace = make(qtbot)
    corner_cut(view)
    assert workspace.editor.state is EditorState.CUT_EDITING
    with qtbot.waitSignal(workspace.net_changed):
        view.left_pressed.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
    assert workspace.editor.state is EditorState.CUT_APPROVING
    item = view.net_item()
    rearranged = workspace.editor.rearranged
    assert item is not None and rearranged is not None
    assert workspace.net is workspace.editor.display_net is rearranged.net
    assert item.glue() == (rearranged.kept, rearranged.moved)  # the glued cuts are marked


def test_in_cut_editing_the_divided_net_follows_the_mouse(qtbot: QtBot) -> None:
    view, workspace = make(qtbot)
    corner_cut(view)
    split = workspace.editor.split()
    view.mouse_moved.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
    hovered = workspace.cut_hover.hovered()
    assert hovered is not None and hovered in split.net.boundary_edges()


def test_the_mouse_cursor_is_optional(qtbot: QtBot) -> None:
    assert make(qtbot)[1].sheet_cursor is not None
    assert make(qtbot, mouse_cursor=False)[1].sheet_cursor is None


def test_labels_with_the_given_names_or_none(qtbot: QtBot) -> None:
    from cube_net.core.labels import PointLabels

    view, workspace = make(qtbot)
    workspace.show_labels(PointLabels())
    item = view.net_item()
    assert item is not None and item.labels() is not None
    workspace.show_labels(None)
    assert item.labels() is None
