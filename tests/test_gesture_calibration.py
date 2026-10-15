import pytest

from gesture_control.gesture_calibration import estimate_pinch_threshold


def test_calibration_uses_midpoint_of_median_pinch_and_neutral_samples():
    threshold = estimate_pinch_threshold(
        [0.20, 0.21, 0.19, 0.90] * 3,
        [0.72, 0.70, 0.74, 0.10] * 3,
    )
    assert threshold == pytest.approx(0.4575)


def test_calibration_requires_enough_samples_and_distinguishable_poses():
    with pytest.raises(ValueError, match="ao menos"):
        estimate_pinch_threshold([0.2] * 5, [0.7] * 12)
    with pytest.raises(ValueError, match="parecidas demais"):
        estimate_pinch_threshold([0.30] * 12, [0.32] * 12)


def test_calibration_rejects_threshold_outside_supported_bounds():
    with pytest.raises(ValueError, match="fora da faixa"):
        estimate_pinch_threshold([0.01] * 12, [0.15] * 12)
