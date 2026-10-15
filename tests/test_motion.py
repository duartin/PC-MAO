from types import SimpleNamespace as P

import pytest

from gesture_control.motion_recognizer import MotionRecognizer


def point(x, y):
    # Todos os pontos se movem juntos neste teste; o centro da palma acompanha.
    return [P(x=x, y=y) for _ in range(21)]


def test_detects_vertical_scroll_swipes():
    detector = MotionRecognizer(threshold=0.10, neutral_seconds=0.2)
    assert detector.update(point(0.5, 0.5), 0.0) is None
    assert detector.update(point(0.5, 0.42), 0.1) is None

    motion = detector.update(point(0.5, 0.29), 0.2)
    assert motion.action == "scroll_up"


def test_detects_horizontal_page_navigation():
    detector = MotionRecognizer(threshold=0.10)
    detector.update(point(0.2, 0.5), 0.0)
    detector.update(point(0.3, 0.5), 0.1)

    motion = detector.update(point(0.43, 0.5), 0.2)
    assert motion.action == "page_forward"


def test_ignores_small_motion_and_requires_stability_to_rearm():
    detector = MotionRecognizer(threshold=0.20, neutral_seconds=0.2)
    detector.update(point(0.5, 0.3), 0.0)
    assert detector.update(point(0.5, 0.38), 0.1) is None

    motion = detector.update(point(0.5, 0.65), 0.2)
    assert motion.action == "scroll_down"

    detector.update(point(0.5, 0.66), 0.3)
    detector.update(point(0.5, 0.66), 0.55)
    detector.update(point(0.5, 0.66), 0.6)
    detector.update(point(0.5, 0.66), 0.7)
    detector.update(point(0.5, 0.66), 0.95)  # estabilizou e rearmou

    detector.update(point(0.5, 0.8), 1.0)
    motion = detector.update(point(0.5, 0.93), 1.1)
    assert motion.action == "scroll_down"


def test_sensitivity_limits_are_validated():
    with pytest.raises(ValueError):
        MotionRecognizer(sensitivity=0.2)

    assert MotionRecognizer(sensitivity=1.5).sensitivity == 1.5
