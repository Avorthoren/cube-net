import gc

import pytest


@pytest.fixture(autouse=True)
def collect_old_windows() -> None:
    """Free what's left of the previous test's windows now, while nothing is being painted.

    A real session has one window, which lives as long as the app. Tests leave many dead ones behind, and when the
    collector gets to them in the middle of another window's paint, Qt crashes.
    """
    gc.collect()
