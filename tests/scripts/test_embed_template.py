# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Embedding a template file as a built-in one keeps what a project needs, and only a good template."""

from dataclasses import replace
from pathlib import Path

import pytest
from scripts.embed_template import main

from cube_net.core.history import History
from cube_net.core.project import TemplateDocument, document_from_bytes, save_project, save_template
from cube_net.core.project.builtin_templates import CUBE_WITH_A_HOLE_FILE, cube_with_a_hole
from cube_net.core.project.project import new_project
from cube_net.core.template import TemplateEditor, TemplateSnapshot


def with_history() -> TemplateDocument:
    """The built-in Cube with a hole, with something in its history (as the author's file has)."""
    editor = TemplateEditor()
    editor.load(cube_with_a_hole().state, History())
    editor.set_face_color(0, "#123456")
    return TemplateDocument(editor.snapshot(), editor.history, cube_with_a_hole().style)


def test_the_template_its_origin_and_style_without_history(tmp_path: Path) -> None:
    source = tmp_path / "torus.nettemplate"
    document = with_history()
    save_template(document, source)
    assert main([str(source)], builtin=tmp_path) == 0
    embedded = document_from_bytes((tmp_path / CUBE_WITH_A_HOLE_FILE).read_bytes())
    assert isinstance(embedded, TemplateDocument)
    assert embedded.state == document.state and embedded.style == document.style
    assert embedded.history.done_count == 0 and embedded.history.undone_count == 0


def test_another_name(tmp_path: Path) -> None:
    source = tmp_path / "torus.nettemplate"
    save_template(with_history(), source)
    assert main([str(source), "--to", "other.nettemplate"], builtin=tmp_path) == 0
    assert (tmp_path / "other.nettemplate").exists() and not (tmp_path / CUBE_WITH_A_HOLE_FILE).exists()


@pytest.mark.parametrize("problem", ["no style", "open", "project", "missing"])
def test_nothing_is_written_for_a_bad_one(tmp_path: Path, capsys: pytest.CaptureFixture[str], problem: str) -> None:
    source = tmp_path / "x.nettemplate"
    if problem == "no style":
        save_template(replace(with_history(), style=None), source)
    elif problem == "open":
        save_template(TemplateDocument(TemplateSnapshot(TemplateEditor().template), History()), source)
    elif problem == "project":
        save_project(new_project(), source)
    assert main([str(source)], builtin=tmp_path) == 1
    assert not (tmp_path / CUBE_WITH_A_HOLE_FILE).exists()
    assert "Not embedded" in capsys.readouterr().err


def test_usage(tmp_path: Path) -> None:
    assert main([], builtin=tmp_path) == 2
    assert main(["a", "--to"], builtin=tmp_path) == 2


def test_nothing_is_written_for_one_with_a_number_too_long(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from fractions import Fraction

    from cube_net.core.geometry import MAX_NUMBER_DIGITS, Vec
    from cube_net.core.origin import Origin

    document = with_history()
    long = Vec(Fraction(1, 10**MAX_NUMBER_DIGITS), 0)  # its denominator: one digit too many
    source = tmp_path / "x.nettemplate"
    save_template(replace(document, state=replace(document.state, origin=Origin(long, long))), source)
    assert main([str(source)], builtin=tmp_path) == 1
    assert not (tmp_path / CUBE_WITH_A_HOLE_FILE).exists()
    error = capsys.readouterr().err
    assert f"a number {MAX_NUMBER_DIGITS + 1} digits long" in error and f"up to {MAX_NUMBER_DIGITS} digits" in error
