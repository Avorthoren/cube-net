from collections.abc import Iterator
from pathlib import Path

import pytest

from cube_net.core.project import ProjectFileError, load_project
from cube_net.ui.i18n import TRANSLATIONS, Language
from cube_net.ui.i18n.errors import error_text


@pytest.fixture
def russian() -> Iterator[None]:
    TRANSLATIONS.set_language(Language.RUSSIAN)
    yield
    TRANSLATIONS.set_language(Language.ENGLISH)


def test_english_is_the_error_itself(tmp_path: Path) -> None:
    path = tmp_path / "bad.cubenet"
    path.write_text("Hello!")
    with pytest.raises(ProjectFileError) as caught:
        load_project(path)
    assert error_text(caught.value) == str(caught.value)


def test_russian_with_its_reason(tmp_path: Path, russian: None) -> None:
    path = tmp_path / "bad.cubenet"
    path.write_text("Hello!")
    with pytest.raises(ProjectFileError) as caught:
        load_project(path)
    assert error_text(caught.value) == f"Не удалось открыть {path}. Это не проект Cube Net."


def test_what_the_system_says_stays(tmp_path: Path, russian: None) -> None:
    error = ProjectFileError("Can't save {path}: {reason}.", path="/x", reason="No space left on device")
    assert error_text(error) == "Не удалось сохранить /x: No space left on device."
