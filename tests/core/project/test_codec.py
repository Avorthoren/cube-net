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

from cube_net.core.editor import Editor, EditorState
from cube_net.core.labels import PointLabels
from cube_net.core.net import validate_net
from cube_net.core.project import FORMAT_VERSION, ProjectFileError, decode_project, encode_project
from cube_net.core.project_settings import ProjectSettings

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

    def test_the_threshold_is_a_decimal_string(self) -> None:
        assert encode_project(project_of(editing()))["settings"] == {"area_threshold": "7.100"}

    @pytest.mark.parametrize("make", [editing, a_second_cut_in_progress], ids=["first", "second"])
    def test_point_names_stay_the_same(self, make: Callable[[], Editor]) -> None:
        editor = make()
        labels = named_labels(editor)
        assert labels.saved()[0]
        loaded = round_trip(project_of(editor, labels)).labels
        assert loaded.saved() == labels.saved()
        assert loaded.upcoming() == labels.upcoming()

    def test_a_new_point_gets_the_next_free_name(self) -> None:
        labels = PointLabels()
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
    data["settings"]["area_threshold"] = "99.000"


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
