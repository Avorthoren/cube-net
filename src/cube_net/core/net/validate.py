# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`validate_net`: everything that must hold for a finished net (docs/plan.md, section 3.4). Raises
`NetInvariantError` with a readable message. For use after a structural change, not in anything called often."""

from fractions import Fraction

from cube_net.core.body import SurfacePoint
from cube_net.core.geometry import signed_area
from cube_net.core.net.elements import EdgeKind, NetVertex, Region
from cube_net.core.net.net import Net, NetInvariantError


def validate_net(net: Net) -> None:
    _check_links(net)
    _check_regions(net)
    _check_connected(net)
    _check_perimeter(net)
    _check_cuts(net)


def _fail(message: str) -> None:
    raise NetInvariantError(message)


def _check_links(net: Net) -> None:
    edges = set(net.half_edges)
    vertices = set(net.vertices)
    for he in net.half_edges:
        if he.next.prev is not he or he.prev.next is not he:
            _fail(f"next/prev of {he} don't match")
        if he.twin.twin is not he or he.twin is he:
            _fail(f"twin of {he} doesn't match")
        if he.next.origin is not he.twin.origin:
            _fail(f"{he} doesn't lead to its next half-edge")
        if he.next.region is not he.region:
            _fail(f"{he} and its next half-edge are in different regions")
        if not {he.next, he.prev, he.twin} <= edges or he.origin not in vertices:
            _fail(f"{he} refers to something that isn't in the net")
        if he.origin.position == he.destination.position:
            _fail(f"{he} has zero length")
    for vertex in net.vertices:
        if vertex.edge not in edges or vertex.edge.origin is not vertex:
            _fail(f"{vertex} refers to a wrong half-edge")


def _check_regions(net: Net) -> None:
    total = Fraction(0)
    for region in net.regions:
        if region.edge not in net.half_edges or region.edge.region is not region:
            _fail(f"{region} refers to a wrong half-edge")
        polygon = net.region_polygon(region)
        area = signed_area(polygon)
        if area <= 0:
            _fail(f"{region} is not counter-clockwise")
        total += area
        for he in net.region_cycle(region):
            if region.face not in he.origin.point.faces:
                _fail(f"{he.origin} doesn't belong to the face of {region}")
            positions = {region.placement.apply(local) for local in he.origin.point.locals_in(region.face)}
            if he.origin.position not in positions:
                _fail(f"{he.origin} isn't where the placement of {region} puts it")
    if total != net.body.area:
        _fail(f"the net's area is {total}, expected the body's {net.body.area}")


def _check_connected(net: Net) -> None:
    """One piece of paper: every region reached from the first through the vertices they share (parts may hang
    together by a point only). It may have holes: a perimeter cycle for each (docs/template_plan.md §8.2)."""
    regions_at: dict[NetVertex, set[Region]] = {}
    for region in net.regions:
        for he in net.region_cycle(region):
            regions_at.setdefault(he.origin, set()).add(region)
    found = {net.regions[0]}
    stack = [net.regions[0]]
    while stack:
        for he in net.region_cycle(stack.pop()):
            for other in regions_at[he.origin] - found:
                found.add(other)
                stack.append(other)
    if len(found) != len(net.regions):
        _fail(f"the net is in pieces: {len(found)} of its {len(net.regions)} regions hang together")


def _check_perimeter(net: Net) -> None:
    cycles = net.perimeters()
    if not cycles:
        _fail("the net has no perimeter")
    on_perimeter = {he.origin for cycle in cycles for he in cycle}
    for vertex in net.vertices:
        name = vertex.point.vertex
        if vertex not in on_perimeter and (name is None or net.body.vertex_angle(name) != 360):
            _fail(f"{vertex} is inside the net")
    for name in net.body.vertex_names:
        if not net.images(SurfacePoint.at_vertex(net.body, name)):
            _fail(f"vertex {name} has no image on the perimeter")


def _check_cuts(net: Net) -> None:
    for he in net.half_edges:
        if he.kind is EdgeKind.SEAM and he.region is not he.twin.region:
            _fail(f"{he} is a seam between two regions: such seams must not remain in a finished net")
    net.reindex()  # every cut has exactly two images
    for he in net.boundary_edges():
        other = net.counterpart(he)
        d1 = he.destination.position - he.origin.position
        d2 = other.destination.position - other.origin.position
        if d1.length_squared() != d2.length_squared():
            _fail(f"{he} and its counterpart {other} differ in length")
