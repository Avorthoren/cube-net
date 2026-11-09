import gc
from collections.abc import Iterator

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent


@pytest.fixture(autouse=True)
def collect_garbage_only_between_tests() -> Iterator[None]:
    """Qt crashes when Python's collector frees what's left of dead windows in the middle of another window's paint.

    It takes many windows: a real session has one, which lives as long as the app, and that one is fine with the
    collector running all the time. Tests leave dead windows behind, so in tests the collector works only here, while
    nothing is being painted. pytest-qt closes a test's windows before this fixture ends, so that's covered too.
    """
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
    gc.disable()
    yield
    gc.enable()


@pytest.fixture(autouse=True)
def default_style() -> Iterator[None]:
    """A test may change the style (it's global): the next one starts with the defaults again."""
    from cube_net.ui.style import DEFAULT_STYLE, apply_style

    apply_style(DEFAULT_STYLE)
    yield
    apply_style(DEFAULT_STYLE)
