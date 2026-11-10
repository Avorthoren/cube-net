# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.project_settings import (
    DEFAULT_AREA_THRESHOLD,
    MAX_AREA_THRESHOLD,
    ProjectSettings,
    ProjectSettingsError,
    format_threshold,
)


def test_default_is_7_100() -> None:
    assert ProjectSettings().area_threshold == DEFAULT_AREA_THRESHOLD == F(71, 10)
    assert format_threshold(DEFAULT_AREA_THRESHOLD) == "7.100"


@pytest.mark.parametrize("value", [F(0), F(1, 1000), F(6), F(12), MAX_AREA_THRESHOLD])
def test_valid(value: F) -> None:
    assert ProjectSettings(value).area_threshold == value


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (F(-1, 1000), "can't be negative"),
        (F(-1), "can't be negative"),
        (F(20001, 1000), "can't exceed 20.000"),
        (F(71001, 10000), "at most 3 decimals"),
        (F(1, 3), "at most 3 decimals"),
    ],
)
def test_invalid(value: F, message: str) -> None:
    with pytest.raises(ProjectSettingsError, match=message):
        ProjectSettings(value)


def test_wrong_type() -> None:
    with pytest.raises(ProjectSettingsError, match="must be a Fraction"):
        ProjectSettings(7.1)  # type: ignore[arg-type]
