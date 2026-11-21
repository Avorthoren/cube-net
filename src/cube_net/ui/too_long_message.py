# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the user is told when an action is refused because a point it would make has a number longer than
`MAX_NUMBER_DIGITS` digits (`core/cutting/too_long.py`, `core/template/too_long.py`): which point (its kind, the segment
or the fold it's on, by the names of their ends, and where it is, from the origin), which coordinate, which of its
numbers, how many digits."""

from cube_net.core.cutting import TooLong, TooLongKind
from cube_net.core.geometry import MAX_NUMBER_DIGITS, LongNumber, Part, Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, NetVertex
from cube_net.core.origin import Origin
from cube_net.core.template import Fold, Template
from cube_net.core.template.too_long import TemplateTooLong, TemplateTooLongKind
from cube_net.ui.i18n import tr
from cube_net.ui.template.validation_messages import NON_BREAKING_HYPHEN, shown_name

REJECTED = "Your action was rejected."
NUMERATOR_TOO_LONG = (
    "The application supports numbers up to {max} digits long, while you tried to create {object}, whose {axis} "
    "coordinate would require a numerator {n} digits long."
)
DENOMINATOR_TOO_LONG = (
    "The application supports numbers up to {max} digits long, while you tried to create {object}, whose {axis} "
    "coordinate would require a denominator {n} digits long."
)

# Where the point is, from the origin.
AT = "x ≈ {x}, y ≈ {y}"

# The points, in projects and in templates.
A_VERTEX = "a vertex ({at})"
CROSSING = "the point where the cut crosses segment {segment} ({at})"
END = "the cut's end on segment {segment} ({at})"
FOLD_CROSSING = "the point where the cut crosses fold {segment} ({at})"
GLUED = "vertex {name} of the glued half ({at})"
ORIGIN = "the origin ({at})"
HOLE_CROSSING = "the point where the hole's side crosses fold {segment} ({at})"


def too_long_text(point: str, number: LongNumber) -> str:
    """The whole message (rich text) about the point described by `point`."""
    values = {"max": MAX_NUMBER_DIGITS, "object": point, "axis": number.axis.value, "n": number.digits}
    numerator = number.part is Part.NUMERATOR
    details = tr(NUMERATOR_TOO_LONG, **values) if numerator else tr(DENOMINATOR_TOO_LONG, **values)
    return f"{tr(REJECTED)}<br>{details}"


def project_too_long_text(found: TooLong, net: Net, labels: PointLabels, origin: Origin) -> str:
    """The message about a project's point: `net` is the net the action started from (`found.net` for a glued one)."""
    names = vertex_labels(found.net or net, labels)

    def name(vertex: NetVertex) -> str:
        label = names.get(vertex)
        return shown_name(f"{label.name}{label.index}") if label is not None else _place(vertex.position, origin)

    def segment(edge: HalfEdge | None) -> str:
        return "?" if edge is None else f"{name(edge.origin)}{NON_BREAKING_HYPHEN}{name(edge.destination)}"

    at = _at(found.position, origin)
    match found.kind:
        case TooLongKind.VERTEX:
            point = tr(A_VERTEX, at=at)
        case TooLongKind.CROSSING:
            point = tr(CROSSING, segment=segment(found.edge), at=at)
        case TooLongKind.END:
            point = tr(END, segment=segment(found.edge), at=at)
        case TooLongKind.FOLD_CROSSING:
            point = tr(FOLD_CROSSING, segment=segment(found.edge), at=at)
        case TooLongKind.GLUED:
            point = tr(GLUED, name=name(found.vertex) if found.vertex is not None else "?", at=at)
        case TooLongKind.ORIGIN:
            point = tr(ORIGIN, at=at)
    return too_long_text(point, found.number)


def template_too_long_text(found: TemplateTooLong, template: Template, origin: Origin) -> str:
    """The message about a template's point (`template`: the one the action started from)."""
    at = _at(found.position, origin)
    match found.kind:
        case TemplateTooLongKind.VERTEX:
            point = tr(A_VERTEX, at=at)
        case TemplateTooLongKind.HOLE_CROSSING:
            point = tr(HOLE_CROSSING, segment=_fold(found.fold, template, origin), at=at)
        case TemplateTooLongKind.ORIGIN:
            point = tr(ORIGIN, at=at)
    return too_long_text(point, found.number)


def _fold(fold: Fold | None, template: Template, origin: Origin) -> str:
    """A fold by the labels of its ends (where one has none: by where it is, `_place`)."""
    if fold is None:
        return "?"

    def name(vertex_id: int) -> str:
        label = template.vertex(vertex_id).label
        return shown_name(str(label)) if label is not None else _place(template.position(vertex_id), origin)

    return f"{name(fold.start)}{NON_BREAKING_HYPHEN}{name(fold.end)}"


def _at(p: Vec, origin: Origin) -> str:
    """Where `p` is, as the coordinates hint shows it (from the origin), to 3 decimals."""
    shown = origin.shown(p)
    return tr(AT, x=f"{float(shown.x):.3f}", y=f"{float(shown.y):.3f}")


def _place(p: Vec, origin: Origin) -> str:
    """A vertex without a name, by where it is (from the origin): "(1.500, 3.667)"."""
    shown = origin.shown(p)
    return f"({float(shown.x):.3f}, {float(shown.y):.3f})"
