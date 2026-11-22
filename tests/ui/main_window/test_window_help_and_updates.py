# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: the Help menu, the applications menu entry, updates."""

from fractions import Fraction as F
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from window_checks import settings_in

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import (
    MainWindow,
)
from cube_net.ui.save_changes_dialog import SaveChoice
from cube_net.ui.style import DEFAULT_STYLE


class TestHelpMenu:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        return window

    def test_after_settings_with_three_items(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        menu_bar = window.menuBar()
        assert menu_bar is not None
        assert [a.text() for a in menu_bar.actions()] == ["&File", "&Edit", "&Settings", "&Help"]
        help_menu = menu_bar.actions()[3].menu()
        assert help_menu is not None
        assert [a.text() for a in help_menu.actions()] == ["&About", "&Help", "Check for &updates"]

    def test_help_opens_one_window_with_f1(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.help_action.isEnabled()
        assert window.help_action.shortcut().toString() == "F1"
        window.help_action.trigger()
        first = window.help_window
        assert first is not None and first.isVisible()
        first.close()
        window.help_action.trigger()
        assert window.help_window is first and first.isVisible()  # the same one again

    def test_help_opens_the_tab_looked_at_last_even_last_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.help.help_tab import HelpTab

        window = self.make(qtbot, tmp_path)
        assert window.settings.help_tab == ""
        window.help_action.trigger()
        assert window.help_window is not None and window.help_window.tab() is HelpTab.NETWORK  # the first time
        window.help_window.show_tab(HelpTab.TEMPLATE)
        assert window.settings.help_tab == "template"
        again = MainWindow(settings=window.settings, session_dir=tmp_path)  # the next start
        qtbot.addWidget(again)
        again.help_action.trigger()
        assert again.help_window is not None and again.help_window.tab() is HelpTab.TEMPLATE

    def test_help_opens_with_its_default_size_every_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.help_action.trigger()
        help_window = window.help_window
        assert help_window is not None
        default = help_window.size()
        help_window.resize(default.width() - 200, default.height() - 300)
        window.help_action.trigger()  # open already: it stays as the user made it
        assert help_window.size() != default
        help_window.close()
        window.help_action.trigger()
        assert help_window.size() == default

    def test_opens_by_itself_at_the_first_start_only(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.settings.help_shown
        window.show_help_at_first_start()
        assert window.help_window is not None and window.help_window.isVisible()
        assert window.settings.help_shown
        window.help_window.close()
        again = MainWindow(settings=window.settings, session_dir=tmp_path)  # the next start, the same settings
        qtbot.addWidget(again)
        again.show_help_at_first_start()
        assert again.help_window is None

    def test_its_animations_keep_the_built_in_cubes_look(self, qtbot: QtBot, tmp_path: Path) -> None:
        from dataclasses import replace

        from cube_net.ui.style import DEFAULT_CUBE_LOOK
        from cube_net.ui.style.apply import style_in_place

        window = self.make(qtbot, tmp_path)
        other = replace(DEFAULT_STYLE, edge_width=1.5, hatch_columns=1.0)
        window._on_style_changed(other)
        window.help_action.trigger()
        help_window = window.help_window
        assert help_window is not None and help_window.network_players
        assert all(player.sheet.view.look() == DEFAULT_CUBE_LOOK for player in help_window.network_players[:-1])
        assert style_in_place() == other  # the project's, for everything else

    def test_its_animations_have_no_vertex_labels_even_when_they_are_on(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.show_labels_action.setChecked(True)
        window.help_action.trigger()
        help_window = window.help_window
        assert help_window is not None
        window.show_labels_action.setChecked(False)
        window.show_labels_action.setChecked(True)  # switched on again while Help is open
        for player in help_window.network_players:
            item = player.sheet.view.net_item()
            assert item is not None and item.labels() is None

    def test_about_and_updates_open_their_windows(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.help.about_dialog import AboutDialog

        window = self.make(qtbot, tmp_path)
        opened: list[str] = []
        monkeypatch.setattr(AboutDialog, "exec", lambda self: opened.append(type(self).__name__) or 0)
        monkeypatch.setattr(MainWindow, "check_for_updates", lambda self, manual: opened.append(f"check {manual}"))
        window.about_action.trigger()
        window.updates_action.trigger()
        assert opened == ["AboutDialog", "check True"]


class TestMenuEntry:
    """Linux, AppImage: Cube Net in the applications menu, asked about once (a throwaway data folder)."""

    def make(self, qtbot: QtBot, tmp_path: Path, appimage: object, settings: AppSettings | None = None) -> MainWindow:
        from cube_net.ui.desktop_integration import DesktopEntry

        window = MainWindow(
            settings=settings or settings_in(tmp_path, record=False),
            session_dir=tmp_path,
            appimage=appimage,  # type: ignore[arg-type]
            desktop_entry=DesktopEntry(tmp_path / "data"),
        )
        qtbot.addWidget(window)
        return window

    def appimage(self, tmp_path: Path, name: str = "Cube.AppImage") -> object:
        import shutil

        from cube_net.ui import desktop_integration
        from cube_net.ui.desktop_integration import AppImage

        root = Path(__file__).resolve().parents[3]
        appdir = tmp_path / "mounted"
        if not appdir.exists():
            (appdir / "usr/share/mime/packages").mkdir(parents=True)
            shutil.copy(root / "packaging/linux/cube-net.desktop", appdir / "cube-net.desktop")
            shutil.copy(root / "packaging/linux/cube-net.xml", appdir / "usr/share/mime/packages/cube-net.xml")
            shutil.copy(Path(desktop_integration.__file__).parent / "icons/cube_net.png", appdir / "cube-net.png")
        file = tmp_path / name
        file.write_text("an AppImage")
        return AppImage(file, appdir)

    def asked(self, monkeypatch: pytest.MonkeyPatch, answer: bool) -> list[bool]:
        questions: list[bool] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_menu_entry", lambda _parent: questions.append(answer) or answer
        )
        monkeypatch.setattr("cube_net.ui.desktop_integration.subprocess.run", lambda *_, **__: None)
        return questions

    def test_asked_once_and_added(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        questions = self.asked(monkeypatch, True)
        settings = settings_in(tmp_path, record=False)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path), settings)
        window.offer_menu_entry()
        assert questions == [True] and settings.menu_entry is True
        assert window.desktop_entry.installed_for() == tmp_path / "Cube.AppImage"
        assert window.settings_panel.preferences.menu_entry is not None
        assert window.settings_panel.preferences.menu_entry.isChecked()
        window.offer_menu_entry()  # the next start
        assert questions == [True]  # not asked again

    def test_no_is_remembered(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        questions = self.asked(monkeypatch, False)
        settings = settings_in(tmp_path, record=False)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path), settings)
        window.offer_menu_entry()
        window.offer_menu_entry()
        assert questions == [False] and settings.menu_entry is False
        assert window.desktop_entry.installed_for() is None

    def test_moved_it_follows_at_the_next_start(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.asked(monkeypatch, True)
        settings = settings_in(tmp_path, record=False)
        self.make(qtbot, tmp_path, self.appimage(tmp_path), settings).offer_menu_entry()
        moved = self.appimage(tmp_path, "Moved.AppImage")
        window = self.make(qtbot, tmp_path, moved, settings)
        window.offer_menu_entry()
        assert window.desktop_entry.installed_for() == tmp_path / "Moved.AppImage"

    def test_the_checkbox_adds_and_removes_it(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.asked(monkeypatch, False)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path))
        window.offer_menu_entry()
        box = window.settings_panel.preferences.menu_entry
        assert box is not None and not box.isChecked()
        box.setChecked(True)
        assert window.desktop_entry.installed_for() is not None and window.settings.menu_entry is True
        monkeypatch.setattr("cube_net.ui.main_window.confirm_menu_entry_removal", lambda _parent: True)
        box.setChecked(False)
        assert window.desktop_entry.installed_for() is None and window.settings.menu_entry is False

    def test_turning_it_off_is_confirmed_first(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.asked(monkeypatch, True)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path))
        window.offer_menu_entry()
        box = window.settings_panel.preferences.menu_entry
        assert box is not None and box.isChecked()
        confirmations: list[bool] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.confirm_menu_entry_removal", lambda _parent: confirmations.append(False) or False
        )
        box.setChecked(False)
        qtbot.waitUntil(box.isChecked)  # cancelled: it stays on
        assert confirmations == [False]
        assert window.desktop_entry.installed_for() is not None and window.settings.menu_entry is True

    def test_a_failure_says_so_and_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        warned: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: warned.append(text))
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path))
        monkeypatch.setattr(window.desktop_entry, "install", lambda appimage: (_ for _ in ()).throw(OSError("full")))
        box = window.settings_panel.preferences.menu_entry
        assert box is not None
        box.setChecked(True)
        qtbot.waitUntil(lambda: not box.isChecked())
        assert warned == ["Couldn't change the applications menu: full"]
        assert window.settings.menu_entry is None

    def test_nothing_of_it_without_an_appimage(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, None)
        window.offer_menu_entry()  # asks nothing
        assert window.settings_panel.preferences.menu_entry is None


class TestUpdates:
    """Help -> Check for updates, and the daily check (the latest release comes from a stand-in, never GitHub)."""

    def make(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, latest: object) -> MainWindow:
        from cube_net.ui.updates.latest_release import LatestRelease, UpdateCheckError

        def fetch() -> LatestRelease | None:
            if isinstance(latest, Exception):
                raise latest
            return None if latest is None else LatestRelease(str(latest), "notes", "https://example.com/release")

        assert UpdateCheckError  # what the failing stand-in raises
        monkeypatch.setattr("cube_net.ui.main_window.fetch_latest_release", fetch)
        monkeypatch.setattr("cube_net.ui.main_window.__version__", "1.0.0")
        self.offered: list[str] = []
        self.automatic: list[bool] = []
        self.told: list[str] = []
        self.opened: list[str] = []
        self.answer = "later"
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_update",
            lambda _parent, release, current, can_update=False, automatic=False: self._offer(
                release.version, automatic
            ),
        )
        monkeypatch.setattr("cube_net.ui.main_window.tell_up_to_date", lambda _parent, current: self.told.append("up"))
        monkeypatch.setattr(
            "cube_net.ui.main_window.tell_check_failed", lambda _parent, problem: self.told.append(f"failed {problem}")
        )
        monkeypatch.setattr(
            "cube_net.ui.main_window.QDesktopServices.openUrl", lambda url: self.opened.append(url.toString())
        )
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        return window

    def _offer(self, version: str, automatic: bool) -> object:
        from cube_net.ui.updates.update_dialogs import UpdateChoice

        self.offered.append(version)
        self.automatic.append(automatic)
        return UpdateChoice.DOWNLOAD if self.answer == "download" else UpdateChoice.LATER

    def check(self, qtbot: QtBot, window: MainWindow, manual: bool) -> None:
        window.check_for_updates(manual)
        assert window._update_check is not None
        qtbot.waitUntil(lambda: not window._update_check.running())  # type: ignore[union-attr]
        qtbot.wait(20)  # the answer's signal, delivered in the window's thread

    def test_a_newer_version_is_offered_and_its_page_opened(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.2.0")
        self.answer = "download"
        self.check(qtbot, window, manual=True)
        assert self.offered == ["1.2.0"] and self.opened == ["https://example.com/release"]

    def test_no_newer_version(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.0.0")
        self.check(qtbot, window, manual=True)
        assert self.offered == [] and self.told == ["up"]

    def test_no_release_at_all(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, None)
        self.check(qtbot, window, manual=True)
        assert self.told == ["up"]

    def test_a_failure_is_told_when_asked(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.updates.latest_release import UpdateCheckError

        window = self.make(qtbot, tmp_path, monkeypatch, UpdateCheckError("no network"))
        self.check(qtbot, window, manual=True)
        assert self.told == ["failed no network"]

    def test_not_now_from_the_menu_skips_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.2.0")
        self.check(qtbot, window, manual=True)
        assert window.settings.skipped_update is None

    def test_daily_check_and_a_turned_down_version(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import datetime

        window = self.make(qtbot, tmp_path, monkeypatch, "1.2.0")
        self.check(qtbot, window, manual=False)
        assert self.offered == ["1.2.0"]
        assert window.settings.skipped_update == "1.2.0"  # "Not now" from the daily check
        assert window.settings.last_update_check == datetime.date.today()
        self.check(qtbot, window, manual=False)  # tomorrow, say
        assert self.offered == ["1.2.0"]  # not again
        self.check(qtbot, window, manual=True)
        assert self.offered == ["1.2.0", "1.2.0"]  # the menu still offers it
        assert self.automatic == [True, False]  # the daily check's offer starts with no button selected

    def test_a_newer_one_than_the_turned_down_one(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.3.0")
        window.settings.skipped_update = "1.2.0"
        self.check(qtbot, window, manual=False)
        assert self.offered == ["1.3.0"]

    def test_a_daily_failure_is_silent_and_tried_again(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.updates.latest_release import UpdateCheckError

        window = self.make(qtbot, tmp_path, monkeypatch, UpdateCheckError("no network"))
        self.check(qtbot, window, manual=False)
        assert self.told == [] and window.settings.last_update_check is None  # not done today: again at the next start

    def test_at_start_once_a_day_if_on(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import datetime

        window = self.make(qtbot, tmp_path, monkeypatch, "1.0.0")
        started: list[bool] = []
        monkeypatch.setattr(MainWindow, "check_for_updates", lambda self, manual: started.append(manual))
        today = datetime.date(2026, 11, 12)
        window.check_for_updates_at_start(today)
        assert started == [False]
        window.settings.last_update_check = today
        window.check_for_updates_at_start(today)  # 00:05 after 23:55 would be another day; this is the same one
        assert started == [False]
        window.check_for_updates_at_start(today + datetime.timedelta(days=1))
        assert started == [False, False]
        window.settings_panel.preferences.check_updates.setChecked(False)
        window.check_for_updates_at_start(today + datetime.timedelta(days=2))
        assert started == [False, False] and window.settings.check_updates is False

    def test_the_checkbox(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.0.0")
        box = window.settings_panel.preferences.check_updates
        assert box.isChecked()  # on unless switched off
        assert box.text() == "Periodically check for updates" and box.toolTip() == "Once a day"
        assert window.settings.check_updates is True


class TestUpdating:
    """Download and update: the download stands in (it says done at once), installing and quitting are watched."""

    def make(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MainWindow:
        from PyQt6.QtCore import QObject, pyqtSignal

        from cube_net.ui.updates.installation import Installation, Kind
        from cube_net.ui.updates.latest_release import LatestRelease, ReleaseFile

        self.package = tmp_path / "CubeNet-1.2.0-linux-x86_64.AppImage"
        self.done: list[str] = []
        self.outcome = "finished"
        test = self

        class Download(QObject):
            progress = pyqtSignal(int, int)
            finished = pyqtSignal(object)
            failed = pyqtSignal(str)
            cancelled = pyqtSignal()

            def __init__(self, name: str, *_: object) -> None:
                super().__init__()
                test.done.append(f"download {name}")

            def start(self) -> None:
                if test.outcome == "finished":
                    self.finished.emit(test.package)
                else:
                    self.failed.emit("no network")

            def cancel(self) -> None:
                pass

        release = LatestRelease(
            "1.2.0",
            "notes",
            "https://example.com/release",
            {self.package.name: ReleaseFile(10, "https://dl/l"), "SHA256SUMS": ReleaseFile(1, "https://dl/s")},
        )
        installation = Installation(Kind.APPIMAGE, tmp_path / "Cube.AppImage")
        monkeypatch.setattr("cube_net.ui.updates.latest_release.sys.platform", "linux")
        monkeypatch.setattr("cube_net.ui.main_window.__version__", "1.0.0")
        monkeypatch.setattr("cube_net.ui.main_window.fetch_latest_release", lambda: release)
        monkeypatch.setattr("cube_net.ui.main_window.current_installation", lambda: installation)
        monkeypatch.setattr("cube_net.ui.main_window.download_folder", lambda installation: tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.PackageDownload", Download)
        monkeypatch.setattr("cube_net.ui.main_window.ask_update", self.ask)
        monkeypatch.setattr(
            "cube_net.ui.main_window.install_appimage",
            lambda new, current: self.done.append(f"install {new.name}") or new,
        )
        monkeypatch.setattr(
            "cube_net.ui.main_window.start_appimage", lambda path: self.done.append(f"start {path.name}")
        )
        monkeypatch.setattr(
            "cube_net.ui.main_window.QDesktopServices.openUrl", lambda url: self.done.append(f"open {url.toString()}")
        )
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def ask(
        self, _parent: object, release: object, current: str, can_update: bool = False, automatic: bool = False
    ) -> object:
        from cube_net.ui.updates.update_dialogs import UpdateChoice

        self.done.append(f"asked, can update: {can_update}")
        return UpdateChoice.DOWNLOAD

    def check(self, qtbot: QtBot, window: MainWindow) -> None:
        window.check_for_updates(manual=True)
        assert window._update_check is not None
        qtbot.waitUntil(lambda: not window._update_check.running())  # type: ignore[union-attr]
        qtbot.wait(20)

    def test_downloaded_installed_started_and_quit(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch)
        self.check(qtbot, window)
        assert self.done == [
            "asked, can update: True",
            "download CubeNet-1.2.0-linux-x86_64.AppImage",
            "install CubeNet-1.2.0-linux-x86_64.AppImage",
            "start CubeNet-1.2.0-linux-x86_64.AppImage",
        ]
        assert not window.isVisible()  # quit for the new version

    def test_unsaved_changes_first_and_not_again(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path, monkeypatch)
        window._on_target_changed(F(5))  # an unsaved change
        questions: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_save_changes", lambda *_: questions.append("asked") or SaveChoice.CANCEL
        )
        self.check(qtbot, window)
        assert questions == ["asked"] and "download CubeNet-1.2.0-linux-x86_64.AppImage" not in self.done  # cancelled
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_save_changes", lambda *_: questions.append("asked") or SaveChoice.DISCARD
        )
        self.check(qtbot, window)
        assert questions == ["asked", "asked"]  # once for this update, not again when it quits
        assert not window.isVisible()

    def test_a_failed_download_offers_the_page(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch)
        self.outcome = "failed"
        told: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.tell_update_failed", lambda _parent, problem: told.append(problem) or True
        )
        self.check(qtbot, window)
        assert told == ["no network"] and self.done[-1] == "open https://example.com/release"
        assert window.isVisible()

    def test_by_hand_when_it_cant_be_put_in_place(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.updates.installation import ManualStepNeeded

        window = self.make(qtbot, tmp_path, monkeypatch)

        def locked(new: Path, current: Path) -> Path:
            raise ManualStepNeeded(new, Path("/opt") / new.name)

        monkeypatch.setattr("cube_net.ui.main_window.install_appimage", locked)
        monkeypatch.setattr("cube_net.ui.main_window.tell_appimage_downloaded", lambda *_: False)  # "Close"
        self.check(qtbot, window)
        assert window.isVisible() and not any(step.startswith("start") for step in self.done)

    def test_run_from_the_source_it_opens_the_page(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch)
        monkeypatch.setattr("cube_net.ui.main_window.current_installation", lambda: None)
        self.check(qtbot, window)
        assert self.done == ["asked, can update: False", "open https://example.com/release"]
