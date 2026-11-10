# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from cube_net.ui.sheet import zoom


def test_initial_scale_makes_net_half_the_screen() -> None:
    assert zoom.initial_scale(1080, 4) == 135  # 4 units * 135 px = 540 px = 50% of 1080


class TestLimits:
    def test_zoom_in_up_to_the_setting(self) -> None:
        assert zoom.zoom_limits(1920, 1200, 3, 4, 1000)[1] == 1000
        assert zoom.zoom_limits(1920, 1200, 3, 4, 2500)[1] == 2500

    def test_zoom_out_until_the_net_takes_half_the_screen_height(self) -> None:
        low, _ = zoom.zoom_limits(1920, 1200, 3, 4, 1000)  # the default cross: taller than wide
        assert low == pytest.approx(150)  # 4 units * 150 px = 600 px = 50% of 1200

    def test_or_half_the_screen_width_if_it_takes_more_of_that(self) -> None:
        low, _ = zoom.zoom_limits(1920, 1200, 24, 4, 1000)  # a wide net
        assert low == pytest.approx(40)  # 24 units * 40 px = 960 px = 50% of 1920
        assert 4 * low / 1200 < 0.5

    def test_the_net_never_takes_more_than_half_at_the_limit(self) -> None:
        for width, height in ((3, 4), (24, 4), (7, 7), (1, 30)):
            low, _ = zoom.zoom_limits(1920, 1080, width, height, 10000)
            assert max(width * low / 1920, height * low / 1080) == pytest.approx(0.5)

    def test_there_is_always_a_valid_zoom(self) -> None:
        low, high = zoom.zoom_limits(1920, 1200, 0.1, 0.1, 500)  # a tiny net would allow zooming out only at 6000
        assert low == high == 500

    @pytest.mark.parametrize("args", [(0, 1200, 3, 4, 1000), (1920, 1200, 0, 4, 1000), (1920, 1200, 3, 4, 0)])
    def test_rejects_non_positive(self, args: tuple[float, float, float, float, float]) -> None:
        with pytest.raises(ValueError):
            zoom.zoom_limits(*args)

    def test_the_default_setting_is_in_its_range(self) -> None:
        low, high = zoom.MAX_ZOOM_RANGE
        assert low <= zoom.DEFAULT_MAX_ZOOM <= high


@pytest.mark.parametrize(("scale", "expected"), [(5, 10), (10, 10), (15, 15), (20, 20), (25, 20)])
def test_clamp(scale: float, expected: float) -> None:
    assert zoom.clamp_scale(scale, (10, 20)) == expected


@pytest.mark.parametrize("args", [(0, 4), (1080, 0), (-1, 4)])
def test_initial_scale_rejects_non_positive(args: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        zoom.initial_scale(*args)
