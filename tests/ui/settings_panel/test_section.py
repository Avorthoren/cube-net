import pytest
from pytestqt.qtbot import QtBot

from cube_net.ui.settings_panel.section import Section


def test_restore_only_after_yes(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    section = Section("Grid")
    qtbot.addWidget(section)
    asked: list[str] = []

    def answer(_parent: object, name: str) -> bool:
        asked.append(name)
        return len(asked) == 2

    monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", answer)
    with qtbot.assertNotEmitted(section.restore_requested):
        section.restore_button.click()
    with qtbot.waitSignal(section.restore_requested):
        section.restore_button.click()
    assert asked == ["Grid", "Grid"]
    assert section.restore_button.text() == "Restore default"
