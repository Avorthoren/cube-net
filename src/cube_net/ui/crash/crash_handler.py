# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CrashHandler`: what happens to an exception nothing caught.

Without it, PyQt aborts the application at once for one raised in a Qt callback (a slot, a paint or mouse event, a
timer), and one in a background thread is only printed. With it (`install`, from `sys.excepthook` and
`threading.excepthook`), the first such exception:
1. is printed, as before;
2. writes a crash report next to the session logs (`write_crash_report`, with the `sections` the main window gives);
3. ends the session recording, if it's on (`end_recording`: its last line says why);
4. tells the user where the report is (`show_crash_window`), and the application closes at once (`os._exit`): nothing
   else of it runs, so a state the error may have broken is never saved over a good file.

An exception in a background thread is handled the same way, in the main thread (a widget can't be shown from another
one). Anything that fails on the way is printed, and the rest goes on: the application closes in any case. An
exception raised while one is handled (the window waits for the user meanwhile) is only printed. Ctrl+C in the
terminal (`KeyboardInterrupt`) is left as it is.
"""

import os
import sys
import threading
import time
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from types import TracebackType

from PyQt6.QtCore import QObject, Qt, pyqtSignal

from cube_net.ui.crash.crash_report import CrashSection, write_crash_report
from cube_net.ui.crash.crash_window import show_crash_window

# An exception, as the hooks get it.
type Error = tuple[type[BaseException], BaseException, TracebackType | None]


class CrashHandler(QObject):
    # An exception of a background thread, for the main thread to handle (its type, value and traceback).
    _from_thread = pyqtSignal(object, object, object)

    def __init__(
        self,
        directory: Callable[[], Path],
        parent: QObject | None = None,
        show: Callable[[Path | None], None] = show_crash_window,
        close: Callable[[int], None] = os._exit,
    ) -> None:
        """`directory`: where the report goes (the session logs' folder). `show` and `close`: how the user is told and
        how the application closes (tests replace them)."""
        super().__init__(parent)
        self._directory = directory
        self._show = show
        self._close = close
        self._started = time.monotonic()
        self._handling = False
        self._hooks: tuple[object, object] | None = None
        # The parts of the report beyond the traceback and the environment (the main window's, once it's there).
        self.sections: Callable[[], Sequence[CrashSection]] = lambda: []
        # Ends the session recording, if it's on.
        self.end_recording: Callable[[], None] = lambda: None
        self._from_thread.connect(self._on_thread_error, Qt.ConnectionType.QueuedConnection)

    def install(self) -> None:
        """Take over `sys.excepthook` and `threading.excepthook` (`uninstall` gives them back)."""
        if self._hooks is None:
            self._hooks = sys.excepthook, threading.excepthook
            sys.excepthook = self._excepthook
            threading.excepthook = self._thread_hook

    def uninstall(self) -> None:
        if self._hooks is not None:
            sys.excepthook, threading.excepthook = self._hooks  # type: ignore[assignment]
            self._hooks = None

    def handle(self, kind: type[BaseException], value: BaseException, trace: TracebackType | None) -> None:
        """An exception nothing caught (in the main thread): see the module's docstring."""
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, trace)
            return
        if self._handling:
            print("Another exception while the first one is handled:", file=sys.stderr)
            traceback.print_exception(kind, value, trace)
            return
        self._handling = True
        try:
            traceback.print_exception(kind, value, trace)
            path = self._report((kind, value, trace))
            _attempt(self.end_recording)
            _attempt(lambda: self._show(path))
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            self._close(1)

    def _report(self, error: Error) -> Path | None:
        try:
            sections = list(self.sections())
        except Exception:
            traceback.print_exc()
            sections = []
        try:
            return write_crash_report(self._directory(), error, sections, self._started)
        except Exception:
            print("The crash report couldn't be saved:", file=sys.stderr)
            traceback.print_exc()
            return None

    def _excepthook(self, kind: type[BaseException], value: BaseException, trace: TracebackType | None) -> None:
        if threading.current_thread() is threading.main_thread():
            self.handle(kind, value, trace)
        else:
            self._from_thread.emit(kind, value, trace)

    def _thread_hook(self, args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, SystemExit):
            return  # a thread that ended itself
        value = args.exc_value if args.exc_value is not None else args.exc_type()
        self._from_thread.emit(args.exc_type, value, args.exc_traceback)

    def _on_thread_error(self, kind: type[BaseException], value: BaseException, trace: TracebackType | None) -> None:
        self.handle(kind, value, trace)


def _attempt(action: Callable[[], object]) -> None:
    """Do `action`; if it fails, print why and go on."""
    try:
        action()
    except Exception:
        traceback.print_exc()
