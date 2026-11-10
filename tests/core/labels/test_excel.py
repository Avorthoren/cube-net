# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import itertools

import pytest

from cube_net.core.labels import excel_label


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, "A"),
        (7, "H"),
        (8, "I"),
        (25, "Z"),
        (26, "AA"),
        (27, "AB"),
        (51, "AZ"),
        (52, "BA"),
        (701, "ZZ"),
        (702, "AAA"),
    ],
)
def test_names(index: int, expected: str) -> None:
    assert excel_label(index) == expected


def test_unique_and_increasing_length() -> None:
    names = [excel_label(i) for i in range(1000)]
    assert len(set(names)) == 1000
    assert all(len(a) <= len(b) for a, b in itertools.pairwise(names))


def test_negative_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        excel_label(-1)
