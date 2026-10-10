from devsec_bench.dashboard.theme import COLORS


def luminance(color):
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return sum(
        channel * weight for channel, weight in zip(linear, [0.2126, 0.7152, 0.0722], strict=True)
    )


def contrast(first, second):
    low, high = sorted([luminance(first), luminance(second)])
    return (high + 0.05) / (low + 0.05)


def test_text_and_status_colors_meet_aa_on_light_surfaces():
    for text in ["text", "muted", "accent", "green", "amber", "red"]:
        for background in ["canvas", "surface"]:
            assert contrast(COLORS[text], COLORS[background]) >= 4.5


def test_interactive_boundaries_are_distinguishable():
    assert contrast(COLORS["control_border"], COLORS["canvas"]) >= 3
