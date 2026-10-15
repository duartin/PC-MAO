from types import SimpleNamespace as P

from gesture_control.motion_recognizer import MotionRecognizer


def point(x, y):
    landmarks = [P(x=x, y=y)]
    landmarks.extend([P(x=x, y=y) for _ in range(20)])
    return landmarks


def test_detects_vertical_scroll_swipes():
    detector = MotionRecognizer(threshold=0.18, neutral_seconds=0.2)
    assert detector.update(point(0.5, 0.5), 0.0) is None
    assert detector.update(point(0.5, 0.42), 0.1) is None
    motion = detector.update(point(0.5, 0.29), 0.2)
    assert motion.action == "scroll_up"


def test_detects_horizontal_page_navigation():
    detector = MotionRecognizer(threshold=0.18)
    detector.update(point(0.2, 0.5), 0.0)
    detector.update(point(0.3, 0.5), 0.1)
    motion = detector.update(point(0.43, 0.5), 0.2)
    assert motion.action == "page_forward"


def test_ignores_small_motion_and_requires_stability_to_rearm():
    detector = MotionRecognizer(threshold=0.20, neutral_seconds=0.2)
    detector.update(point(0.3, 0.5), 0.0)
    assert detector.update(point(0.38, 0.5), 0.1) is None
    motion = detector.update(point(0.55, 0.5), 0.2)
    assert motion.action == "page_forward"
    detector.update(point(0.56, 0.5), 0.3)
    assert detector.update(point(0.56, 0.5), 0.55) is None
    # New swipe is available after the motion has settled.
    detector.update(point(0.56, 0.5), 0.6)
    detector.update(point(0.7, 0.5), 0.7)
    assert detector.update(point(0.82, 0.5), 0.8).action == "page_forward"
