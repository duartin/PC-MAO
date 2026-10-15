from types import SimpleNamespace as P

from gesture_control.pinch_zoom import PinchZoomRecognizer
from gesture_control.recognizer import HandGestureRecognizer


def landmarks_with_gap(ratio):
    points = [P(x=0.5, y=0.5) for _ in range(21)]
    points[5] = P(x=0.4, y=0.5)
    points[17] = P(x=0.6, y=0.5)
    points[8] = P(x=0.5, y=0.25)
    points[4] = P(x=0.5 + ratio * 0.2, y=0.25)
    return points


def test_increasing_pinch_gap_zooms_in_and_decreasing_gap_zooms_out():
    zoom = PinchZoomRecognizer(min_delta=0.10, min_interval=0.10, smoothing=1.0)
    assert zoom.update(landmarks_with_gap(0.30), 0.0) is None
    assert zoom.update(landmarks_with_gap(0.43), 0.15) == "zoom_in"
    assert zoom.update(landmarks_with_gap(0.56), 0.30) == "zoom_in"
    assert zoom.update(landmarks_with_gap(0.43), 0.45) == "zoom_out"


def test_small_pinch_wobble_does_not_zoom_and_tracking_loss_resets():
    zoom = PinchZoomRecognizer(min_delta=0.12, min_interval=0.10, smoothing=1.0)
    assert zoom.update(landmarks_with_gap(0.40), 0.0) is None
    assert zoom.update(landmarks_with_gap(0.46), 0.2) is None
    assert zoom.update(None, 0.3) is None
    assert zoom.update(landmarks_with_gap(0.60), 0.4) is None


def test_closed_pinch_is_not_classified_as_the_mode_switch_fist():
    detected = HandGestureRecognizer().recognize(landmarks_with_gap(0.20))
    assert detected.name == "Pinça"
    assert detected.action == "pinch"
