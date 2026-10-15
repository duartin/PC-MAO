from types import SimpleNamespace as P

from gesture_control.keyboard_controller import KeyboardController
from gesture_control.recognizer import HandGestureRecognizer
from gesture_control.safety_manager import SafetyManager, SafetySettings


def landmarks(extended=(), thumb_tip=(0.50, 0.55), thumb_ip=(0.50, 0.50)):
    points = [P(x=0.5, y=0.6) for _ in range(21)]
    points[0] = P(x=0.5, y=0.9)
    points[2] = P(x=0.5, y=0.55)
    points[3] = P(x=thumb_ip[0], y=thumb_ip[1])
    points[4] = P(x=thumb_tip[0], y=thumb_tip[1])
    for tip, pip, mcp in ((8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)):
        points[mcp] = P(x=0.5, y=0.55)
        points[pip] = P(x=0.5, y=0.40)
        points[tip] = P(x=0.5, y=0.35 if tip in extended else 0.45)
    return points


def test_recognizes_five_conservative_poses():
    recognizer = HandGestureRecognizer()
    cases = [
        (landmarks(thumb_tip=(0.5, 0.25), thumb_ip=(0.5, 0.5)), "enter"),
        (landmarks(thumb_tip=(0.5, 0.75), thumb_ip=(0.5, 0.5)), "esc"),
        (landmarks((8, 12, 16, 20), thumb_tip=(0.8, 0.5), thumb_ip=(0.7, 0.5)), "space"),
        (landmarks(), "ctrl+s"),
        (landmarks((8, 12)), "alt+tab"),
    ]
    assert [recognizer.recognize(points).action for points, _ in cases] == [
        expected for _, expected in cases
    ]


def test_shortcut_controller_is_dry_run_by_default_and_rejects_unknown_actions():
    controller = KeyboardController()
    assert "Modo de teste" in controller.execute("ctrl+s")
    try:
        controller.execute("delete-all")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown action must be rejected")


def test_safety_requires_hold_and_neutral_rearm():
    settings = SafetySettings(hold_seconds=0.5, cooldown_seconds=0, neutral_seconds=0.2)
    safety = SafetyManager(settings)
    gesture = HandGestureRecognizer().recognize(landmarks())
    assert safety.update(gesture, 1.0) is None
    assert safety.update(gesture, 1.49) is None
    assert safety.update(gesture, 1.51) == gesture
    assert safety.update(gesture, 2.0) is None  # held gesture cannot repeat
    safety.update(None, 2.1)
    safety.update(None, 2.31)
    assert safety.update(gesture, 2.4) is None
    assert safety.update(gesture, 2.91) == gesture
