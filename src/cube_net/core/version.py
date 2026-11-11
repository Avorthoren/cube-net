# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Versions of Cube Net, and their order: what a release may be called (`release.sh` checks it) and which of two is
newer (the update check compares the app's own with the latest release's).

A version is MAJOR.MINOR.PATCH, without leading zeros (but a lone 0), optionally with -alpha, -beta or -rc and a
number: 1.2.0, 1.2.0-beta, 1.2.0-rc.2 (all of them are versions Python's packaging accepts, PEP 440). Pre-releases of
a version are all equal, and lower than the version itself: 1.2.0-alpha == 1.2.0-beta.2 < 1.2.0 < 1.2.1. Anything
else (a development copy's "1.0", say) is lower than every version.
"""

import re
from dataclasses import dataclass

# A version: numbers without leading zeros (but a lone 0), and an optional pre-release suffix.
VERSION_PATTERN = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-(alpha|beta|rc)(\.?(0|[1-9]\d*))?)?")

# Where text that isn't a version comes in the order: below every version.
BELOW_EVERY_VERSION: tuple[int, ...] = (-1,)


@dataclass(frozen=True)
class Version:
    text: str
    major: int
    minor: int
    patch: int

    # The pre-release suffix (without the dash), if there's one: "beta.2".
    pre: str | None

    @property
    def tag(self) -> str:
        """Its release's tag."""
        return f"v{self.text}"

    @property
    def order(self) -> tuple[int, int, int, int]:
        """What versions are compared by: the numbers, then a pre-release below the version itself (pre-releases of
        the same version are equal to each other)."""
        return self.major, self.minor, self.patch, 0 if self.pre is not None else 1


def parse_version(text: str) -> Version | None:
    """The version written as `text`, or None if it isn't one."""
    match = VERSION_PATTERN.fullmatch(text)
    if match is None:
        return None
    major, minor, patch, suffix = match.group(1), match.group(2), match.group(3), match.group(4)
    return Version(text, int(major), int(minor), int(patch), suffix[1:] if suffix else None)


def order_of(text: str) -> tuple[int, ...]:
    """Where `text` comes among versions: as itself if it's one, below all of them if it isn't."""
    version = parse_version(text)
    return version.order if version is not None else BELOW_EVERY_VERSION


def newer(candidate: str, than: str) -> bool:
    """Is `candidate` a version, and strictly higher than `than` (a version or not)?"""
    return parse_version(candidate) is not None and order_of(candidate) > order_of(than)
