# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from collections.abc import Callable
from fractions import Fraction as F
from typing import Any

import pytest
from project_checks import (
    EDITORS,
    a_second_cut_in_progress,
    after_a_cut,
    approving,
    editing,
    editor_of,
    entry_contents,
    named_labels,
    net_contents,
    project_of,
    round_trip,
    starts_at_a_vertex_and_crosses_a_fold,
    state_contents,
    with_something_to_redo,
)

from cube_net.core.body import CUBE, Body, SurfacePoint
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.labels import PointLabels
from cube_net.core.net import starting_net, validate_net
from cube_net.core.project import FORMAT_VERSION, ProjectFileError, TemplateDocument, decode_project, encode_project
from cube_net.core.project_settings import ProjectSettings
from cube_net.core.style import Style

# A style, not the default one.
STYLE = Style(3, 4, 7, 2.5, 5.0, "#ABCDEF", 0.5)

ALL_EDITORS = pytest.mark.parametrize("make", EDITORS.values(), ids=EDITORS.keys())


class TestRoundTrip:
    @ALL_EDITORS
    def test_the_state(self, make: Callable[[], Editor]) -> None:
        project = project_of(make())
        assert state_contents(round_trip(project).state) == state_contents(project.state)

    @ALL_EDITORS
    def test_the_history(self, make: Callable[[], Editor]) -> None:
        project = project_of(make())
        loaded = round_trip(project)
        for entries, loaded_entries in (
            (project.history.done_entries(), loaded.history.done_entries()),
            (project.history.undone_entries(), loaded.history.undone_entries()),
        ):
            assert [entry_contents(e) for e in loaded_entries] == [entry_contents(e) for e in entries]

    @ALL_EDITORS
    def test_undo_and_redo_go_through_the_same_states(self, make: Callable[[], Editor]) -> None:
        original = make()
        loaded = editor_of(round_trip(project_of(original)))
        for step in ("undo", "redo"):
            for _ in range(20):
                done = getattr(original, step)()
                assert getattr(loaded, step)() == done
                assert state_contents(loaded.snapshot()) == state_contents(original.snapshot())
                assert loaded.state is original.state

    @ALL_EDITORS
    def test_its_points_are_elements_of_its_net(self, make: Callable[[], Editor]) -> None:
        state = round_trip(project_of(make())).state
        for point in state.points or ():
            assert point.edge is None or point.edge in state.net.half_edges
            assert point.fold is None or point.fold in state.net.half_edges
            assert point.vertex is None or point.vertex in state.net.vertices

    def test_a_vertex_and_a_fold_stay_what_they_were(self) -> None:
        state = round_trip(project_of(starts_at_a_vertex_and_crosses_a_fold())).state
        assert state.points is not None
        assert state.points[0].vertex is not None
        assert state.points[1].fold is not None

    def test_the_rearrangement_is_shown_the_same(self) -> None:
        state = round_trip(project_of(approving())).state
        assert state.rearranged is not None
        assert state.rearranged.kept in state.rearranged.net.half_edges
        assert state.rearranged.moved in state.rearranged.net.half_edges


class TestGoingOn:
    def test_approve_after_loading(self) -> None:
        original = approving()
        loaded = editor_of(round_trip(project_of(original)))
        loaded.approve()
        original.approve()
        assert loaded.state is EditorState.DEFAULT
        validate_net(loaded.net)
        assert net_contents(loaded.net) == net_contents(original.net)

    def test_undo_an_approval_after_loading_takes_the_rearrangement_too(self) -> None:
        loaded = editor_of(round_trip(project_of(after_a_cut())))
        assert loaded.undo()
        assert loaded.state is EditorState.CUT_EDITING
        assert loaded.redo()
        assert loaded.state is EditorState.CUT_APPROVING
        assert loaded.redo()
        assert loaded.state is EditorState.DEFAULT
        assert loaded.approved_cuts == 1

    def test_a_new_action_forgets_the_redo_stack_after_loading(self) -> None:
        loaded = editor_of(round_trip(project_of(with_something_to_redo())))
        assert loaded.history.can_redo
        loaded.insert_midpoint(0)
        assert not loaded.history.can_redo

    def test_editing_a_loaded_line_does_not_change_what_was_saved(self) -> None:
        loaded = editor_of(round_trip(project_of(editing())))
        before = loaded.snapshot()
        loaded.insert_midpoint(0)
        loaded.undo()
        assert state_contents(loaded.snapshot()) == state_contents(before)

    def test_a_loaded_project_can_be_saved_again(self) -> None:
        project = project_of(a_second_cut_in_progress())
        once = encode_project(round_trip(project))
        assert encode_project(round_trip(round_trip(project))) == once


class TestSharing:
    def test_one_net_for_all_the_actions_on_it(self) -> None:
        editor = editing()
        for _ in range(500):
            editor.insert_midpoint(0)
            editor.delete_point(1)
        project = project_of(editor)
        data = encode_project(project)
        assert len(data["nets"]) == 1
        loaded = round_trip(project)
        assert len({entry.before.net for entry in loaded.history.done_entries()}) == 1
        assert len(json.dumps(data)) < 1_000_000

    def test_what_undo_brings_back_is_the_same_net(self) -> None:
        loaded = editor_of(round_trip(project_of(after_a_cut())))
        now = loaded.net
        loaded.undo()
        before = loaded.net
        assert before is not now
        loaded.redo()
        loaded.redo()
        assert loaded.net is now


class TestTheRest:
    def test_settings(self) -> None:
        project = project_of(editing(), settings=ProjectSettings(F(6789, 1000)))
        assert round_trip(project).settings.area_threshold == F(6789, 1000)

    def test_the_style(self) -> None:
        project = project_of(editing(), settings=ProjectSettings(style=STYLE))
        assert round_trip(project).settings.style == STYLE
        assert encode_project(project)["settings"]["style"]["hatch_rows"] == STYLE.hatch_rows

    def test_a_project_saved_without_a_style_has_none(self) -> None:
        data = json.loads(json.dumps(encode_project(project_of(editing(), settings=ProjectSettings(style=STYLE)))))
        del data["settings"]["style"]
        assert decode_project(data).settings.style is None

    @pytest.mark.parametrize(
        "damage",
        [
            lambda style: style.__setitem__("edge_width", 99.0),
            lambda style: style.__setitem__("hatch_rows", "2"),
            lambda style: style.pop("grid_color"),
        ],
    )
    def test_a_damaged_style(self, damage: Callable[[dict[str, Any]], None]) -> None:
        data = json.loads(json.dumps(encode_project(project_of(editing(), settings=ProjectSettings(style=STYLE)))))
        damage(data["settings"]["style"])
        with pytest.raises(ProjectFileError, match="damaged"):
            decode_project(data)

    def test_the_threshold_is_a_decimal_string(self) -> None:
        assert encode_project(project_of(editing()))["settings"] == {
            "area_threshold": "7.100",
            "face_colors": None,
            "style": None,
        }

    @pytest.mark.parametrize("make", [editing, a_second_cut_in_progress], ids=["first", "second"])
    def test_point_names_stay_the_same(self, make: Callable[[], Editor]) -> None:
        editor = make()
        labels = named_labels(editor)
        assert labels.saved()[0]
        loaded = round_trip(project_of(editor, labels)).labels
        assert loaded.saved() == labels.saved()
        assert loaded.upcoming() == labels.upcoming()

    def test_a_new_point_gets_the_next_free_name(self) -> None:
        labels = PointLabels(CUBE)
        editor = editing()
        points = [v_.point for v_ in editor.split().net.vertices]
        named = {labels.register(point) for point in points}
        loaded = round_trip(project_of(editor, labels)).labels
        assert loaded.upcoming() not in named

    def test_it_is_plain_json(self) -> None:
        for make in EDITORS.values():
            json.dumps(encode_project(project_of(make())))


def damage_net_ref(data: dict[str, Any]) -> None:
    data["states"][0]["net"] = 99


def damage_duplicate_id(data: dict[str, Any]) -> None:
    data["nets"][0]["vertices"][1]["id"] = data["nets"][0]["vertices"][0]["id"]


def damage_dangling_edge(data: dict[str, Any]) -> None:
    data["nets"][0]["edges"][0]["twin"] = 99999


def damage_next_link(data: dict[str, Any]) -> None:
    edges = data["nets"][0]["edges"]
    edges[0]["next"] = edges[0]["id"]


def damage_vertex_position(data: dict[str, Any]) -> None:
    data["nets"][0]["vertices"][0]["at"] = ["0", "0"]


def damage_number(data: dict[str, Any]) -> None:
    data["nets"][0]["vertices"][0]["at"] = ["abc", "0"]


def damage_float_number(data: dict[str, Any]) -> None:
    data["nets"][0]["vertices"][0]["at"] = [1.5, "0"]


def damage_zero_denominator(data: dict[str, Any]) -> None:
    data["nets"][0]["vertices"][0]["at"] = ["1/0", "0"]


def damage_surface_point(data: dict[str, Any]) -> None:
    data["nets"][0]["vertices"][0]["point"]["face"] = 7


def damage_edge_kind(data: dict[str, Any]) -> None:
    data["nets"][0]["edges"][0]["kind"] = "glue"


def damage_action_kind(data: dict[str, Any]) -> None:
    data["history"]["done"][0]["kind"] = "dance"


def damage_state_ref(data: dict[str, Any]) -> None:
    data["state"] = 99999


def damage_threshold_too_big(data: dict[str, Any]) -> None:
    data["settings"]["area_threshold"] = "10000.001"


def damage_threshold_too_precise(data: dict[str, Any]) -> None:
    data["settings"]["area_threshold"] = "7.1234"


def damage_same_name_twice(data: dict[str, Any]) -> None:
    names = data["labels"]["names"]
    names[1][1] = names[0][1]


def damage_name_of_a_vertex(data: dict[str, Any]) -> None:
    data["labels"]["names"][0][1] = "A"


def damage_next_name(data: dict[str, Any]) -> None:
    data["labels"]["next"] = 0


class TestDamagedFiles:
    def data(self) -> dict[str, Any]:
        editor = with_something_to_redo()
        data: dict[str, Any] = json.loads(json.dumps(encode_project(project_of(editor, named_labels(editing())))))
        return data

    @pytest.mark.parametrize("data", [None, 3, "text", [], {}], ids=repr)
    def test_not_a_project_at_all(self, data: object) -> None:
        with pytest.raises(ProjectFileError):
            decode_project(data)

    def test_a_newer_version(self) -> None:
        data = self.data()
        data["format_version"] = FORMAT_VERSION + 1
        with pytest.raises(ProjectFileError, match="newer version"):
            decode_project(data)

    @pytest.mark.parametrize("version", [None, 0, "1", 1.5])
    def test_an_unknown_version(self, version: object) -> None:
        data = self.data()
        data["format_version"] = version
        with pytest.raises(ProjectFileError, match="unknown format version"):
            decode_project(data)

    @pytest.mark.parametrize("key", ["settings", "labels", "nets", "rearranged", "states", "state", "history"])
    def test_something_is_missing(self, key: str) -> None:
        data = self.data()
        del data[key]
        with pytest.raises(ProjectFileError, match="damaged"):
            decode_project(data)

    @pytest.mark.parametrize(
        "damage",
        [
            damage_net_ref,
            damage_duplicate_id,
            damage_dangling_edge,
            damage_next_link,
            damage_vertex_position,
            damage_number,
            damage_float_number,
            damage_zero_denominator,
            damage_surface_point,
            damage_edge_kind,
            damage_action_kind,
            damage_state_ref,
            damage_threshold_too_big,
            damage_threshold_too_precise,
            damage_same_name_twice,
            damage_name_of_a_vertex,
            damage_next_name,
        ],
    )
    def test_something_is_wrong(self, damage: Callable[[dict[str, Any]], None]) -> None:
        data = self.data()
        damage(data)
        with pytest.raises(ProjectFileError, match="damaged"):
            decode_project(data)

    def test_the_undamaged_one_is_fine(self) -> None:
        decode_project(self.data())


def test_any_coordinates_can_be_saved() -> None:
    """More digits than Python turns into text by default (old projects may have them): a project must always save."""
    from fractions import Fraction

    from cube_net.core.geometry import Rigid90, Vec
    from cube_net.core.net import default_net
    from cube_net.core.project import Project

    huge = Fraction(1, 3**12000)
    assert len(str(huge.denominator)) > 4300
    net = default_net().copy().net
    motion = Rigid90.translation(Vec(huge, 0))
    for vertex in net.vertices:
        vertex.position = motion.apply(vertex.position)
    for region in net.regions:
        region.placement = motion @ region.placement
    project = project_of(Editor(net))
    assert isinstance(project, Project)
    assert net_contents(round_trip(project).state.net) == net_contents(net)


class TestOrigin:
    @staticmethod
    def moved() -> Editor:
        from cube_net.core.geometry import Vec
        from cube_net.core.origin import DEFAULT_ORIGIN

        editor = editing()
        editor.move_origin(DEFAULT_ORIGIN.moved(Vec(11, 13), Vec(F(1, 3), -2), "C_1"))
        return editor

    def test_saved_with_every_state_and_the_history(self) -> None:
        editor = self.moved()
        loaded = round_trip(project_of(editor))
        assert loaded.state.origin == editor.origin
        entries = [entry_contents(e) for e in loaded.history.done_entries()]
        assert entries == [entry_contents(e) for e in editor.history.done_entries()]

    def test_version_1_has_the_default_one(self) -> None:
        from cube_net.core.origin import DEFAULT_ORIGIN

        data = json.loads(json.dumps(encode_project(project_of(editing()))))
        data["format_version"] = 1
        for state in data["states"]:
            del state["origin"]
        loaded = decode_project(data)
        assert loaded.state.origin == DEFAULT_ORIGIN

    def test_a_name_that_isnt_text_is_damage(self) -> None:
        data = json.loads(json.dumps(encode_project(project_of(self.moved()))))
        data["states"][-1]["origin"]["name"] = 7
        with pytest.raises(ProjectFileError, match="damaged"):
            decode_project(data)


class TestBodies:
    def test_a_project_of_the_cube(self) -> None:
        data = encode_project(project_of(editing()))
        assert (data["format_version"], data["kind"], data["body"]) == (3, "project", "cube")
        assert round_trip(project_of(editing())).state.net.body is CUBE

    @pytest.mark.parametrize("body_name", ["long_box", "pinwheel_box", "pillow", "flat_pillow"])
    def test_a_project_of_another_body(self, body_name: str, request: pytest.FixtureRequest) -> None:
        """The body goes into the file: the project doesn't need anything else to be opened."""
        body: Body = request.getfixturevalue(body_name)
        editor = Editor(starting_net(body))
        colors = tuple(f"#0000{n:02X}" for n in body.face_numbers)
        project = project_of(editor, PointLabels(body), ProjectSettings(face_colors=colors))
        loaded = round_trip(project)
        again = loaded.state.net.body
        assert again is not body
        assert again.face_numbers == body.face_numbers
        assert all(again.face(n) == body.face(n) for n in body.face_numbers)
        assert again.start == body.start and again.colors == body.colors and again.area == body.area
        assert loaded.settings.face_colors == colors
        assert loaded.labels.name(SurfacePoint.at_vertex(again, body.vertex_names[0])) == body.vertex_names[0]
        assert state_contents(loaded.state) == state_contents(project.state)

    def test_a_body_with_rings_and_faces_in_pieces(self, slit_torus: TemplateDocument) -> None:
        """The torus with a slit: two faces with a hole, each in two pieces in the starting net."""
        from cube_net.core.project.from_template import project_from_template

        project = project_from_template(slit_torus)
        body = project.state.net.body
        data = encode_project(project)
        assert sum("holes" in face for face in data["body"]["faces"]) == 2
        # The rings' 4 pieces, and 2 faces whose sides R, S, T, U (no vertices of the body: straight) divide.
        assert sum("corners" in piece for piece in data["body"]["start"]) == 6
        again = round_trip(project).state.net.body
        assert all(again.face(n) == body.face(n) for n in body.face_numbers)
        assert again.start == body.start and again.area == body.area

    def test_a_cut_of_another_body_after_loading(self, l_prism: Body) -> None:
        editor = Editor(starting_net(l_prism))
        loaded = round_trip(project_of(editor, PointLabels(l_prism)))
        again = Editor(loaded.state.net)
        # Across side face 4, the square from (2, 0) to (3, 1): from the middle of its bottom to that of its right.
        for p in (Vec(F(5, 2), 0), Vec(3, F(1, 2))):
            cut = next(
                he for he in again.net.boundary_edges() if on_segment(p, he.origin.position, he.destination.position)
            )
            assert again.click(p, cut) is None
        assert again.state is EditorState.CUT_EDITING

    def test_version_2_is_the_cube_with_no_colours(self) -> None:
        data = json.loads(json.dumps(encode_project(project_of(editing()))))
        data["format_version"] = 2
        for key in ("kind", "body"):
            del data[key]
        del data["settings"]["face_colors"]
        loaded = decode_project(data)
        assert loaded.state.net.body is CUBE and loaded.settings.face_colors is None

    @pytest.mark.parametrize("kind", [None, "template", "something"])
    def test_not_a_project(self, kind: object) -> None:
        data = json.loads(json.dumps(encode_project(project_of(editing()))))
        data["kind"] = kind
        with pytest.raises(ProjectFileError, match="isn't a Cube Net project"):
            decode_project(data)

    @pytest.mark.parametrize(
        "damage",
        [
            lambda data: data["settings"].__setitem__("face_colors", ["#000000"] * 5),
            lambda data: data["settings"].__setitem__("face_colors", ["#00000X"] * 6),
            lambda data: data.__setitem__("body", "sphere"),
            lambda data: data.__setitem__("body", {"faces": [], "start": [], "colors": []}),
        ],
        ids=["5 colours", "bad colour", "unknown body", "empty body"],
    )
    def test_damaged(self, damage: Callable[[dict[str, Any]], None]) -> None:
        data = json.loads(json.dumps(encode_project(project_of(editing()))))
        damage(data)
        with pytest.raises(ProjectFileError, match="damaged"):
            decode_project(data)
