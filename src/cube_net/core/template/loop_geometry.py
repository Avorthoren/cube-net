# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The geometry of a loop that may touch itself (docs/template_plan.md, §8.1), exactly.

Around a point the loop passes through, its sides leave as rays. Between consecutive rays (counter-clockwise) are the
gaps; each gap is inside the net or outside it, and which one is told by the loop's winding number at a point in it,
just next to the point: 1 inside, 0 outside (the loop of a valid template goes counter-clockwise). Anything else means
the net overlaps itself there. That needs no pairing of the rays into passes, which a slit's tip on a point the loop
passes again would make ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise

from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment, signed_area, strictly_within
from cube_net.core.template.template import Template


@dataclass(frozen=True, slots=True)
class Ray:
    """A side of the loop leaving a point: which way, the vertex there it's a side of (None: it passes through the
    point), and the side (its vertex ids, in the loop's direction)."""

    direction: Vec
    vertex: int | None
    side: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Gap:
    """The counter-clockwise arc from one direction of rays to the next one (the same one: all the way round), the rays
    each way (several, where sides lie on each other), and the loop's winding number just inside the arc."""

    start: tuple[Ray, ...]
    end: tuple[Ray, ...]
    winding: int

    @property
    def start_direction(self) -> Vec:
        return self.start[0].direction

    @property
    def end_direction(self) -> Vec:
        return self.end[0].direction

    def contains(self, direction: Vec) -> bool:
        return strictly_within(self.start_direction, direction, self.end_direction)


def rays_at(template: Template, q: Vec) -> list[Ray]:
    """The rays of the loop's sides at `q`, counter-clockwise (rays the same way, in the loop's order)."""
    rays = []
    for a, b in template.loop_sides():
        pa, pb = template.position(a), template.position(b)
        if pa == q:
            rays.append(Ray(pb - q, a, (a, b)))
        elif pb == q:
            rays.append(Ray(pa - q, b, (a, b)))
        elif on_segment(q, pa, pb):
            rays.append(Ray(pb - q, None, (a, b)))
            rays.append(Ray(pa - q, None, (a, b)))
    return sorted(rays, key=lambda ray: _angle_key(ray.direction))


def gaps_at(template: Template, q: Vec) -> list[Gap]:
    """The gaps around `q` (a point of the closed loop), each with the winding number just inside it."""
    groups: list[list[Ray]] = []
    for ray in rays_at(template, q):
        if groups and _same_way(groups[-1][0].direction, ray.direction):
            groups[-1].append(ray)
        else:
            groups.append([ray])
    gaps = []
    for i, group in enumerate(groups):
        following = groups[(i + 1) % len(groups)]
        u = _inside(group[0].direction, following[0].direction)
        sample = q + u * _step(template, q, u)
        gaps.append(Gap(tuple(group), tuple(following), winding_number(template, sample)))
    return gaps


def inside_gaps(template: Template, q: Vec) -> list[Gap]:
    """The gaps around `q` that are inside the net."""
    return [gap for gap in gaps_at(template, q) if gap.winding == 1]


def vertex_gaps(template: Template, vertex_id: int) -> list[Gap]:
    """The gaps inside the net next to the vertex: those one of its own sides bounds (most often the one between its
    two sides; at a point the loop passes more than once, it may share a gap with another vertex there)."""
    q = template.position(vertex_id)
    return [gap for gap in inside_gaps(template, q) if any(ray.vertex == vertex_id for ray in (*gap.start, *gap.end))]


def winding_number(template: Template, p: Vec) -> int:
    """How many times the closed loop goes counter-clockwise round `p` (which must not be on it)."""
    total = 0
    for a, b in template.loop_sides():
        pa, pb = template.position(a), template.position(b)
        if pa.y <= p.y < pb.y and (pb - pa).cross(p - pa) > 0:
            total += 1
        elif pb.y <= p.y < pa.y and (pb - pa).cross(p - pa) < 0:
            total -= 1
    return total


def pieces(template: Template) -> int:
    """How many pieces of paper the closed loop makes. Its sides, cut at every point where it touches itself, make a
    plane graph; each bounded face of it the loop goes round with the net on its left is a piece. Pieces meeting only
    at points are separate; a slit with a free end lies inside one; a slit from edge to edge parts two; a face with the
    net on its right is a hole (a "C" whose tips touch)."""
    sides = template.loop_sides()
    contacts: set[Vec] = set()
    for i, (a, b) in enumerate(sides):
        pa, pb = template.position(a), template.position(b)
        for c, d in sides[i + 1 :]:
            hit = classify_segments(pa, pb, template.position(c), template.position(d))
            if hit.kind is not IntersectionKind.DISJOINT:
                contacts.update(hit.points)
    # How many times the loop goes along each piece of a side, each way.
    along: dict[tuple[Vec, Vec], int] = {}
    for a, b in sides:
        pa, pb = template.position(a), template.position(b)
        direction = pb - pa
        inner = sorted(
            (q for q in contacts if q not in (pa, pb) and on_segment(q, pa, pb)), key=lambda q: (q - pa).dot(direction)
        )
        stops = [pa, *inner, pb]
        for u, v in pairwise(stops):
            along[(u, v)] = along.get((u, v), 0) + 1
    leaving: dict[Vec, list[Vec]] = {}
    for u, v in {*along, *((v, u) for u, v in along)}:
        leaving.setdefault(u, []).append(v)
    for u, ends in leaving.items():
        ends.sort(key=lambda v: _angle_key(v - u))
    count = 0
    seen: set[tuple[Vec, Vec]] = set()
    for start in [*along, *((v, u) for u, v in along)]:
        if start in seen:
            continue
        cycle = []
        edge = start
        while edge not in seen:
            seen.add(edge)
            cycle.append(edge)
            u, v = edge
            ends = leaving[v]
            edge = (
                v,
                ends[ends.index(u) - 1],
            )  # the face on the left: from v, the next way clockwise from the way back
        if signed_area([u for u, _ in cycle]) <= 0:
            continue  # the outside, or no area
        forward = any(along.get(e, 0) and not along.get((e[1], e[0]), 0) for e in cycle)
        backward = any(along.get((e[1], e[0]), 0) and not along.get(e, 0) for e in cycle)
        if forward or not backward:  # the loop goes round it with the net on its left (or only slits bound it)
            count += 1
    return count


def _same_way(d1: Vec, d2: Vec) -> bool:
    return d1.cross(d2) == 0 and d1.dot(d2) > 0


def _angle_key(d: Vec) -> tuple[int, Fraction]:
    """Sorts directions counter-clockwise from the positive x axis, exactly."""
    if d.y == 0 and d.x > 0:
        return 0, Fraction(0)
    if d.y > 0:
        return 1, -d.x / d.y
    if d.y == 0:
        return 2, Fraction(0)
    return 3, -d.x / d.y


def _inside(d1: Vec, d2: Vec) -> Vec:
    """A direction strictly inside the counter-clockwise arc from `d1` to `d2` (all the way round if they're the
    same)."""
    turn = d1.cross(d2)
    if turn > 0:
        return d1 * d2.length_squared() + d2 * d1.length_squared()  # equal lengths: between them
    if turn == 0 and d1.dot(d2) < 0:
        return Vec(-d1.y, d1.x)
    if turn == 0:
        return -d1
    return -(d1 * d2.length_squared() + d2 * d1.length_squared())


def _step(template: Template, q: Vec, u: Vec) -> Fraction:
    """How far along `u` to go from `q` to be nearer to `q` than to any side that doesn't pass through it (half as near,
    at most): there, the winding number is the gap's."""
    nearest: Fraction | None = None
    for a, b in template.loop_sides():
        pa, pb = template.position(a), template.position(b)
        if pa == q or pb == q or on_segment(q, pa, pb):
            continue
        d2 = _distance_squared(q, pa, pb)
        nearest = d2 if nearest is None or d2 < nearest else nearest
    limit = nearest if nearest is not None else Fraction(1)
    step = Fraction(1)
    while step * step * u.length_squared() * 4 >= limit:
        step /= 2
    return step


def _distance_squared(p: Vec, a: Vec, b: Vec) -> Fraction:
    d = b - a
    t = max(Fraction(0), min(Fraction(1), (p - a).dot(d) / d.length_squared()))
    closest = a + d * t
    return (p - closest).length_squared()
