import pytest

from cube_net.ui.sheet import zoom


def test_initial_scale_makes_net_half_the_screen() -> None:
    assert zoom.initial_scale(1080, 4) == 135  # 4 units * 135 px = 540 px = 50% of 1080


def test_limits_for_default_sheet() -> None:
    low, high = zoom.zoom_limits(1080, 13, 14)
    assert low == pytest.approx(0.1 * 1080 / 13)  # smaller side (13 units) >= 108 px
    assert high == pytest.approx(1080 / (0.05 * 14))  # bigger side (14 units) <= 20 screen heights
    assert low < zoom.initial_scale(1080, 4) < high


def test_contradicting_limits_prefer_zoom_out_rule() -> None:
    low, high = zoom.zoom_limits(1000, 1, 1000)
    assert low == high == pytest.approx(100)


@pytest.mark.parametrize(("scale", "expected"), [(5, 10), (10, 10), (15, 15), (20, 20), (25, 20)])
def test_clamp(scale: float, expected: float) -> None:
    assert zoom.clamp_scale(scale, (10, 20)) == expected


@pytest.mark.parametrize("args", [(0, 4), (1080, 0), (-1, 4)])
def test_initial_scale_rejects_non_positive(args: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        zoom.initial_scale(*args)


def test_limits_reject_non_positive() -> None:
    with pytest.raises(ValueError):
        zoom.zoom_limits(1080, 0, 5)
