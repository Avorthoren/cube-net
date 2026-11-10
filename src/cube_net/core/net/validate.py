# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`validate_net`: everything that must hold for a finished cube net (docs/plan.md, section 3.4). Raises
`NetInvariantError` with a readable message. For use after a structural change, not in anything called often."""

from fractions import Fraction

from cube_net.core.cube import VERTICES, SurfacePoint
from cube_net.core.geometry import signed_area
from cube_net.core.net.elements import EdgeKind
from cube_net.core.net.net import Net, NetInvariantError


def validate_net(net: Net) -> None:
    _check_links(net)
    _check_regions(net)
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
            if region.placement.apply(he.origin.point.local_in(region.face)) != he.origin.position:
                _fail(f"{he.origin} isn't where the placement of {region} puts it")
    if total != 6:
        _fail(f"the net's area is {total}, expected 6")


def _check_perimeter(net: Net) -> None:
    cycles = net.perimeters()
    if len(cycles) != 1:
        _fail(f"the net has {len(cycles)} perimeter cycles, expected 1")
    on_perimeter = {he.origin for he in cycles[0]}
    for vertex in net.vertices:
        if vertex not in on_perimeter:
            _fail(f"{vertex} is inside the net")
    for label in VERTICES:
        if not net.images(SurfacePoint.at_vertex(label)):
            _fail(f"cube vertex {label} has no image on the perimeter")


def _check_cuts(net: Net) -> None:
    for he in net.half_edges:
        if he.kind is EdgeKind.SEAM:
            _fail(f"{he} is a seam: seams must not remain in a finished net")
    net.reindex()  # every cut has exactly two images
    for he in net.boundary_edges():
        other = net.counterpart(he)
        d1 = he.destination.position - he.origin.position
        d2 = other.destination.position - other.origin.position
        if d1.length_squared() != d2.length_squared():
            _fail(f"{he} and its counterpart {other} differ in length")
