# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from cube_net.core.body import CUBE
from cube_net.core.cutting import TooLong, TooLongKind
from cube_net.core.geometry import MAX_NUMBER_DIGITS, Axis, LongNumber, Part, Vec
from cube_net.core.labels import PointLabels
from cube_net.core.net import default_net
from cube_net.core.origin import Origin
from cube_net.core.template import Fold, Template
from cube_net.core.template.too_long import TemplateTooLong, TemplateTooLongKind
from cube_net.ui.i18n import TRANSLATIONS, Language
from cube_net.ui.template.validation_messages import NON_BREAKING_HYPHEN
from cube_net.ui.too_long_message import project_too_long_text, template_too_long_text

NUMBER = LongNumber(Axis.Y, Part.DENOMINATOR, 2101)


def lines(text: str) -> list[str]:
    return text.split("<br>")


def test_a_vertex_where_it_is_from_the_origin() -> None:
    net = default_net()
    origin = Origin(Vec(10, 10), Vec(10, 10))
    found = TooLong(TooLongKind.VERTEX, Vec(F(23, 2), F(41, 3)), NUMBER)
    assert lines(project_too_long_text(found, net, PointLabels(CUBE), origin)) == [
        "Your action was rejected.",
        f"The application supports numbers up to {MAX_NUMBER_DIGITS} digits long, while you tried to create a vertex "
        "(x ≈ 1.500, y ≈ 3.667), whose y coordinate would require a denominator 2101 digits long.",
    ]


def test_a_point_on_a_segment_by_the_names_of_its_ends() -> None:
    net = default_net()
    top = next(
        e for e in net.boundary_edges() if {e.origin.position, e.destination.position} == {Vec(11, 14), Vec(12, 14)}
    )
    found = TooLong(TooLongKind.CROSSING, Vec(F(23, 2), 14), LongNumber(Axis.X, Part.NUMERATOR, 2200), top)
    text = project_too_long_text(found, net, PointLabels(CUBE), Origin())
    names = {f"B<sub>1</sub>{NON_BREAKING_HYPHEN}A<sub>1</sub>", f"A<sub>1</sub>{NON_BREAKING_HYPHEN}B<sub>1</sub>"}
    assert any(f"the point where the cut crosses segment {n} (x ≈ 11.500, y ≈ 14.000)" in text for n in names)
    assert "whose x coordinate would require a numerator 2200 digits long" in text
    end = TooLong(TooLongKind.END, Vec(F(23, 2), 14), NUMBER, top)
    assert "the cut's end on segment" in project_too_long_text(end, net, PointLabels(CUBE), Origin())


def test_every_kind_of_point() -> None:
    net = default_net()
    vertex = net.vertices[0]
    texts = {
        kind: project_too_long_text(
            TooLong(kind, Vec(0, 0), NUMBER, net.fold_edges()[0], vertex, net), net, PointLabels(CUBE), Origin()
        )
        for kind in TooLongKind
    }
    assert "the point where the cut crosses fold" in texts[TooLongKind.FOLD_CROSSING]
    assert "of the glued half" in texts[TooLongKind.GLUED] and "<sub>" in texts[TooLongKind.GLUED]
    assert "the origin (x ≈ 0.000, y ≈ 0.000)" in texts[TooLongKind.ORIGIN]


def test_in_a_template() -> None:
    template = Template()
    found = TemplateTooLong(TemplateTooLongKind.VERTEX, Vec(1, 2), NUMBER)
    assert "create a vertex (x ≈ 1.000, y ≈ 2.000)" in template_too_long_text(found, template, Origin())
    origin = TemplateTooLong(TemplateTooLongKind.ORIGIN, Vec(1, 2), NUMBER)
    assert "create the origin" in template_too_long_text(origin, template, Origin())


def test_a_holes_crossing_names_the_fold_by_its_ends() -> None:
    from cube_net.core.template import TemplateEditor

    editor = TemplateEditor()
    for p in [Vec(10, 10), Vec(11, 10), Vec(12, 10), Vec(12, 11), Vec(11, 11), Vec(10, 11), Vec(10, 10)]:
        assert editor.add_point(p) is None
    assert editor.add_fold(1, 4) is None
    found = TemplateTooLong(TemplateTooLongKind.HOLE_CROSSING, Vec(11, F(21, 2)), NUMBER, Fold(1, 4))
    text = template_too_long_text(found, editor.template, Origin())
    fold = f"(11.000, 10.000){NON_BREAKING_HYPHEN}(11.000, 11.000)"  # no labels: where its ends are
    assert f"the point where the hole's side crosses fold {fold} (x ≈ 11.000, y ≈ 10.500)" in text


def test_in_russian_with_the_numbers_forms() -> None:
    TRANSLATIONS.set_language(Language.RUSSIAN)
    net = default_net()
    for digits, form in ((2101, "цифру"), (2102, "цифры"), (2105, "цифр")):
        found = TooLong(TooLongKind.VERTEX, Vec(1, 2), LongNumber(Axis.X, Part.NUMERATOR, digits))
        text = project_too_long_text(found, net, PointLabels(CUBE), Origin())
        assert text.startswith("Ваше действие отклонено.<br>")
        assert (
            f"вершину (x ≈ 1.000, y ≈ 2.000): для координаты x потребовался бы числитель длиной в {digits} {form}."
            in text
        )
