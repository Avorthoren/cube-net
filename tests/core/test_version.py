# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from cube_net.core.version import BELOW_EVERY_VERSION, newer, order_of, parse_version


def test_a_version_and_its_parts() -> None:
    version = parse_version("1.2.3-beta.2")
    assert version is not None
    assert (version.major, version.minor, version.patch, version.pre) == (1, 2, 3, "beta.2")
    assert version.tag == "v1.2.3-beta.2"


@pytest.mark.parametrize("text", ["1.0", "1.02.0", "1.2.0-gamma", "v1.2.0", "", "abc1234"])
def test_not_versions(text: str) -> None:
    assert parse_version(text) is None
    assert order_of(text) == BELOW_EVERY_VERSION


@pytest.mark.parametrize(
    ("candidate", "than", "is_newer"),
    [
        ("1.0.1", "1.0.0", True),
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "1.0.1", False),  # never older
        ("1.0.0", "1.0.0-alpha", True),  # the release after its pre-release
        ("1.0.0-beta", "1.0.0-alpha", False),  # pre-releases of a version are equal
        ("1.0.0-rc.1", "0.9.9", True),
        ("1.10.0", "1.9.0", True),  # numbers, not text
        ("1.0.0", "1.0", True),  # a development copy's version: lower than any
        ("0.0.1-alpha", "anything", True),
        ("garbage", "1.0", False),  # what isn't a version is never newer
    ],
)
def test_newer(candidate: str, than: str, is_newer: bool) -> None:
    assert newer(candidate, than) is is_newer
