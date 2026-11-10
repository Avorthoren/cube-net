# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every text the user can see has its Russian translation (docs/idea.txt: every text, now and in the future)."""

import ast
import pathlib
import string

import cube_net
from cube_net.ui.i18n.russian import RUSSIAN

SOURCE = pathlib.Path(cube_net.__file__).parent

# Calls whose argument at this position is a text to translate.
TEXT_ARGUMENTS = {
    "tr": 0,
    "bind": 2,
    "_section": 0,
    "Section": 0,
    "add_labelled_row": 0,
    "ProjectFileError": 0,
    "_paragraph": 0,
    "_title": 0,
    "_caption": 0,
}


def _constants(tree: ast.Module) -> dict[str, str]:
    """The module's string constants (NAME = "text")."""
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value.value
    return found


def texts_in_the_source() -> dict[str, str]:
    """Every text given to `tr`, `bind` and the like, with where it is."""
    found: dict[str, str] = {}
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = _constants(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
            position = TEXT_ARGUMENTS.get(name or "")
            if position is None or len(node.args) <= position:
                continue
            argument = node.args[position]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                found[argument.value] = f"{path.relative_to(SOURCE)}:{node.lineno}"
            elif isinstance(argument, ast.Name) and argument.id in constants:
                found[constants[argument.id]] = f"{path.relative_to(SOURCE)}:{node.lineno}"
    return found


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_the_scan_finds_texts() -> None:
    texts = texts_in_the_source()
    assert "&File" in texts and "Faces colors" in texts and "Can't open {path}. {problem}" in texts
    assert len(texts) > 60


def test_every_text_has_a_translation() -> None:
    missing = {text: where for text, where in texts_in_the_source().items() if text not in RUSSIAN}
    assert missing == {}


def test_no_translation_of_a_text_that_is_gone() -> None:
    texts = texts_in_the_source()
    assert sorted(set(RUSSIAN) - set(texts)) == []


def test_the_same_placeholders() -> None:
    wrong = {text: russian for text, russian in RUSSIAN.items() if placeholders(text) != placeholders(russian)}
    assert wrong == {}


def test_menu_texts_keep_their_shortcut_letter() -> None:
    wrong = {text: russian for text, russian in RUSSIAN.items() if ("&" in text) != ("&" in russian)}
    assert wrong == {}
