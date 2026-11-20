# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What validating a template says (docs/template_idea.txt, Validation): a `ValidationFailure` in words, in the user's
language. Lists read like "A-CT, AS-QC and Z-R"; cuts and their folds like "A1-B1 and A1-B3; S2-Q3 and S1-Q1, S3-Q5";
folds named the same like "A1-B1 and A2-B2; S1-Q1, S2-Q3 and S3-Q2"; faces as squares of their colours. Vertex
indices are subscripts, as on the sheet (A<sub>1</sub>-B<sub>1</sub>): a message that has them, or squares, is rich
text."""

import re
from collections.abc import Sequence

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
from PyQt6.QtGui import QColor, QFontMetrics, QImage, QPainter
from PyQt6.QtWidgets import QApplication

from cube_net.core.template import ValidationFailure, ValidationProblem
from cube_net.ui import palette
from cube_net.ui.i18n import tr

# After reindexing, when nothing else was wrong.
REINDEXED = "Vertices automatically reindexed.\nNo other problems found."

# When nothing was wrong.
NO_PROBLEMS = "No problems found."

# A vertex's label in a name: its name (1 or 2 capital letters), then its index.
LABEL = re.compile(r"\b([A-Z]{1,2})([0-9]+)\b")


def no_problems_text() -> str:
    return tr(NO_PROBLEMS)


def reindexed_text() -> str:
    return tr(REINDEXED)


def listed(items: Sequence[str]) -> str:
    """ "A", "A and B", "A, B and C"."""
    if len(items) == 1:
        return items[0]
    return tr("{items} and {last}", items=", ".join(items[:-1]), last=items[-1])


def subscripted(text: str) -> str:
    """Every label in a name ("A1-GF12") with its index a subscript, in rich text ("A<sub>1</sub>-GF<sub>12</sub>");
    names without indices ("A-CT") as they are. Names have nothing else that HTML would take."""
    return LABEL.sub(r"\1<sub>\2</sub>", text)


def color_square(color: str) -> str:
    """A square of the colour, outlined, as high as a capital letter of the messages' font, in rich text."""
    size = QFontMetrics(QApplication.font()).capHeight() + 2
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(palette.COLOR_SQUARE_OUTLINE)
    painter = QPainter(image)
    painter.fillRect(1, 1, size - 2, size - 2, QColor(color))
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return f'<img src="data:image/png;base64,{bytes(data.toBase64()).decode()}">'


def groups_listed(groups: Sequence[Sequence[str]]) -> str:
    """Groups of 2: "A1-B1 and A1-B3"; of more: "S2-Q3 and S1-Q1, S3-Q5" (the first one, and the others listed);
    separated by semicolons."""
    return "; ".join(tr("{first} and {others}", first=g[0], others=", ".join(g[1:])) for g in groups)


def failure_text(failure: ValidationFailure) -> str:
    """The message for a failed check (the last one's is a question: see `REINDEX`)."""
    names = [subscripted(n) for n in failure.names]
    groups = [[subscripted(n) for n in g] for g in failure.groups]
    many = len(names) > 1 or len(groups) > 1
    match failure.problem:
        case ValidationProblem.NO_COLOR:
            if failure.count > 1:
                return tr("You have faces without a color. Double-click on a face to assign its color.")
            return tr("You have a face without a color. Double-click on the face to assign its color.")
        case ValidationProblem.UNLABELLED:
            return tr("Some vertices don't have assigned labels. Name each vertex.")
        case ValidationProblem.SELF_EDGE:
            if many:
                return tr(
                    "You have edges that connect a vertex to itself, which is impossible: {list}.", list=listed(names)
                )
            return tr(
                "You have an edge that connects a vertex to itself, which is impossible: {list}.", list=listed(names)
            )
        case ValidationProblem.NO_COUNTERPART:
            if many:
                return tr(
                    "Segments {list} don't have counterparts. Each segment should appear exactly twice, because "
                    "that's what gluing implies.",
                    list=listed(names),
                )
            return tr(
                "Segment {list} doesn't have a counterpart. Each segment should appear exactly twice, because that's "
                "what gluing implies.",
                list=listed(names),
            )
        case ValidationProblem.NOT_PARALLEL:
            return tr(
                "Counterparts for {list} are neither parallel nor perpendicular. Cube Net accepts only nets with "
                "parallel or perpendicular counterparts, to stay within rational numbers.",
                list=listed(names),
            )
        case ValidationProblem.DIFFERENT_LENGTHS:
            return tr(
                "Counterparts for {list} have different lengths, thus it would be impossible to glue them.",
                list=listed(names),
            )
        case ValidationProblem.SAME_DIRECTION:
            return tr(
                "Counterparts for {list} run in the same direction along the loop, so one of them would have to be "
                "turned over to glue them. Counterparts must run in opposite directions.",
                list=listed(names),
            )
        case ValidationProblem.CUT_AND_FOLD:
            if many or len(groups[0]) > 2:
                return tr(
                    "You have cuts that also exist as folds, which is impossible: {list}.",
                    list=groups_listed(groups),
                )
            return tr(
                "You have a cut that also exists as a fold, which is impossible: {list}.",
                list=groups_listed(groups),
            )
        case ValidationProblem.SAME_FOLDS:
            return tr(
                "You have folds that connect the same vertices, which is impossible: {list}.",
                list="; ".join(listed(group) for group in groups),
            )
        case ValidationProblem.NOT_GLUED:
            if many:
                return tr(
                    "Some of your vertices are not glued to themselves, which is impossible: {list}.",
                    list=listed(names),
                )
            return tr("Vertex {name} is not glued to itself, which is impossible.", name=names[0])
        case ValidationProblem.SAME_COLOR_FOLD:
            if many:
                return tr(
                    "You have folds between faces of the same color: {list}. A fold separates two faces: give them "
                    "different colors.",
                    list=listed(names),
                )
            return tr(
                "You have a fold between faces of the same color: {list}. A fold separates two faces: give them "
                "different colors.",
                list=listed(names),
            )
        case ValidationProblem.PIECES_APART:
            squares = [color_square(c) for c in failure.colors]
            if len(squares) > 1:
                return tr("Pieces of some faces aren't glued together: {list}.", list=listed(squares))
            return tr("Pieces of this face aren't glued together: {list}.", list=listed(squares))
        case ValidationProblem.TOO_FEW_FACES:
            return tr("Net should have at least 4 faces.")
        case ValidationProblem.FACE_TOUCHES_ITSELF:
            return tr(
                "A face touches itself at {list}, which a face can't do: a slit, or a point where the loop touches "
                "itself, must lie between two faces. Divide the face there with a fold.",
                list=listed(names),
            )
        case ValidationProblem.SELF_INTERSECTING:
            squares = [color_square(c) for c in failure.colors]
            if len(squares) > 1:
                return tr("Some faces self-intersect after gluing: {list}.", list=listed(squares))
            return tr("This face self-intersects after gluing: {list}.", list=listed(squares))
        case ValidationProblem.INDEX_GAPS:
            if many:
                return tr("Indices for vertices {list} have gaps. Reindex automatically?", list=listed(names))
            return tr("Indices for vertex {list} have gaps. Reindex automatically?", list=listed(names))
