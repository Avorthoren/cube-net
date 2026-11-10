# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Splitting a line into dashes of alternating colours (float arithmetic: drawing only)."""

import math


def dash_pieces(length: float, offset: float, dash: float) -> list[tuple[float, float, int]]:
    """Split [0, length] into dashes of size `dash` of a pattern that has position `offset` at 0.

    Returns (start, end, parity) triples: parity 0 for even dashes of the pattern, 1 for odd ones. The first and last
    pieces may be shorter than `dash`.
    """
    if length <= 0 or dash <= 0:
        return []
    pieces = []
    s = 0.0
    index = math.floor(offset / dash + 1e-9)
    while s < length - 1e-12:
        boundary = (index + 1) * dash - offset
        end = min(boundary, length)
        if end > s:
            pieces.append((s, end, index % 2))
        s = end
        index += 1
    return pieces
