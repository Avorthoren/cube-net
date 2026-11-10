# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Rigid90, Vec

fractions = st.fractions(max_denominator=1000, min_value=-100, max_value=100)
vecs = st.builds(Vec, fractions, fractions)
nonzero_vecs = vecs.filter(lambda v: not v.is_zero())
motions = st.builds(Rigid90, st.integers(-10, 10), vecs)


class TestConstruction:
    def test_k_normalized(self) -> None:
        assert Rigid90(5, Vec(1, 1)).k == 1
        assert Rigid90(-1).k == 3
        assert Rigid90(-1) == Rigid90(3)

    def test_defaults_are_identity(self) -> None:
        assert Rigid90() == Rigid90.identity()
        assert Rigid90().is_identity()
        assert not Rigid90(1).is_identity()
        assert not Rigid90.translation(Vec(0, 1)).is_identity()

    @pytest.mark.parametrize("bad_k", [1.0, True, "1", None])
    def test_bad_k_rejected(self, bad_k: object) -> None:
        with pytest.raises(TypeError):
            Rigid90(bad_k)  # type: ignore[arg-type]

    def test_bad_t_rejected(self) -> None:
        with pytest.raises(TypeError):
            Rigid90(0, (1, 2))  # type: ignore[arg-type]

    def test_immutable_and_hashable(self) -> None:
        m = Rigid90(1, Vec(2, 3))
        with pytest.raises(AttributeError):
            m.k = 2  # type: ignore[misc]
        assert len({m, Rigid90(5, Vec(2, 3)), Rigid90(2, Vec(2, 3))}) == 2

    def test_repr(self) -> None:
        assert repr(Rigid90(1, Vec(F(1, 2), 0))) == "Rigid90(k=1, t=Vec(1/2, 0))"


class TestApply:
    def test_translation(self) -> None:
        assert Rigid90.translation(Vec(1, -2)).apply(Vec(3, 3)) == Vec(4, 1)

    def test_rotation_around_origin(self) -> None:
        assert Rigid90(1).apply(Vec(1, 0)) == Vec(0, 1)

    def test_rotation_around_center_keeps_center(self) -> None:
        c = Vec(11, 13)
        r = Rigid90.rotation(1, c)
        assert r.apply(c) == c
        assert r.apply(Vec(12, 13)) == Vec(11, 14)

    def test_apply_vector_ignores_translation(self) -> None:
        m = Rigid90(1, Vec(100, 100))
        assert m.apply_vector(Vec(1, 0)) == Vec(0, 1)
        assert m.apply(Vec(1, 0)) - m.apply(Vec(0, 0)) == m.apply_vector(Vec(1, 0))


class TestFromSegments:
    def test_corner_cut_example_is_translation(self) -> None:
        """docs/idea.txt corner-cut example: x_1 B_1 is glued onto x_2 B_3."""
        x1, b1 = Vec(F(23, 2), 14), Vec(12, 14)
        x2, b3 = Vec(F(23, 2), 10), Vec(12, 10)
        assert Rigid90.from_segments(x1, b1, x2, b3) == Rigid90.translation(Vec(0, -4))

    def test_default_net_ac_counterparts_is_rotation_around_c1(self) -> None:
        """Gluing A_2 C_1 onto A_1 C_1 rotates face 4 clockwise around C_1."""
        a2, c1, a1 = Vec(10, 13), Vec(11, 13), Vec(11, 14)
        m = Rigid90.from_segments(a2, c1, a1, c1)
        assert m == Rigid90.rotation(-1, c1)
        # Face 4 ([10,11]x[12,13]) ends up to the left of face 1 ([10,11]x[13,14]); E lands next to A_1.
        assert m.apply(Vec(10, 12)) == Vec(10, 14)  # E_2
        assert m.apply(Vec(11, 12)) == Vec(10, 13)  # H_1

    def test_degenerate_rejected(self) -> None:
        with pytest.raises(ValueError, match="degenerate"):
            Rigid90.from_segments(Vec(0, 0), Vec(0, 0), Vec(1, 1), Vec(2, 1))
        with pytest.raises(ValueError, match="degenerate"):
            Rigid90.from_segments(Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(1, 1))

    @pytest.mark.parametrize(
        "dst_end",
        [
            Vec(2, 0),  # different length
            Vec(1, 1),  # 45 degrees
            Vec(F(3, 5), F(4, 5)),  # same length, but not a multiple of 90 degrees
        ],
    )
    def test_not_related_by_90_degree_motion_rejected(self, dst_end: Vec) -> None:
        with pytest.raises(ValueError, match="90-degree"):
            Rigid90.from_segments(Vec(0, 0), Vec(1, 0), Vec(0, 0), dst_end)

    @given(motions, vecs, nonzero_vecs)
    def test_recovers_any_motion(self, m: Rigid90, a: Vec, d: Vec) -> None:
        b = a + d
        assert Rigid90.from_segments(a, b, m.apply(a), m.apply(b)) == m


class TestAlgebra:
    @given(motions, motions, vecs)
    def test_composition_is_function_composition(self, a: Rigid90, b: Rigid90, p: Vec) -> None:
        assert (a @ b).apply(p) == a.apply(b.apply(p))

    @given(motions, motions, motions)
    def test_composition_associative(self, a: Rigid90, b: Rigid90, c: Rigid90) -> None:
        assert (a @ b) @ c == a @ (b @ c)

    @given(motions, vecs)
    def test_inverse(self, m: Rigid90, p: Vec) -> None:
        assert (m @ m.inverse()).is_identity()
        assert (m.inverse() @ m).is_identity()
        assert m.inverse().apply(m.apply(p)) == p

    @given(motions, vecs, vecs)
    def test_preserves_distances_and_orientation(self, m: Rigid90, p: Vec, q: Vec) -> None:
        assert (m.apply(p) - m.apply(q)).length_squared() == (p - q).length_squared()
        assert m.apply_vector(p).cross(m.apply_vector(q)) == p.cross(q)

    def test_not_commutative_in_general(self) -> None:
        r, t = Rigid90(1), Rigid90.translation(Vec(1, 0))
        assert r @ t != t @ r

    def test_matmul_with_other_type(self) -> None:
        with pytest.raises(TypeError):
            Rigid90() @ Vec(1, 1)  # type: ignore[operator]
