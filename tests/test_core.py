from types import SimpleNamespace as P

from gesture_control.keyboard_controller import KeyboardController
from gesture_control.mouse_controller import MouseController
from gesture_control.recognizer import HandGestureRecognizer
from gesture_control.safety_manager import SafetyManager, SafetySettings


def landmarks(extended=(), thumb_tip=(0.50, 0.55), thumb_ip=(0.50, 0.50), down=()):
    points = [P(x=0.5, y=0.6) for _ in range(21)]
    points[0] = P(x=0.5, y=0.9)
    points[2] = P(x=0.5, y=0.55)
    points[3] = P(x=thumb_ip[0], y=thumb_ip[1])
    points[4] = P(x=thumb_tip[0], y=thumb_tip[1])
    for tip, pip, mcp in ((8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)):
        if tip in down:
            points[mcp] = P(x=0.5, y=0.45)
            points[pip] = P(x=0.5, y=0.60)
            points[tip] = P(x=0.5, y=0.78)
        else:
            points[mcp] = P(x=0.5, y=0.55)
            points[pip] = P(x=0.5, y=0.40)
            points[tip] = P(x=0.5, y=0.35 if tip in extended else 0.45)
    return points


def test_recognizes_supported_conservative_poses():
    recognizer = HandGestureRecognizer()
    cases = [
        (landmarks(thumb_tip=(0.5, 0.25), thumb_ip=(0.5, 0.5)), "enter"),
        (landmarks(thumb_tip=(0.5, 0.75), thumb_ip=(0.5, 0.5)), "esc"),
        (landmarks((8, 12, 16, 20), thumb_tip=(0.8, 0.5), thumb_ip=(0.7, 0.5)), "space"),
        (landmarks(), "ctrl+s"),
        (landmarks((8, 12)), "scroll_up"),
        (landmarks(down=(8, 12)), "scroll_down"),
        (landmarks((8,)), "cursor"),
    ]
    assert [recognizer.recognize(points).action for points, _ in cases] == [
        expected for _, expected in cases
    ]


def test_shortcut_controller_is_dry_run_by_default_and_rejects_unknown_actions():
    controller = KeyboardController()
    assert "Modo de teste" in controller.execute("ctrl+s")
    assert "alt+left" in controller.execute("alt+left")
    assert "alt+right" in controller.execute("alt+right")
    assert "zoom_in" in controller.execute("zoom_in")
    assert "zoom_out" in controller.execute("zoom_out")
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


def test_safety_uses_short_hold_and_one_and_a_half_second_action_cooldown():
    settings = SafetySettings()
    assert settings.hold_seconds == 0.25
    assert settings.cooldown_seconds == 1.5


def test_action_is_not_delayed_at_start_but_next_action_waits_for_cooldown():
    safety = SafetyManager(
        SafetySettings(hold_seconds=0.25, cooldown_seconds=1.5, neutral_seconds=0.2)
    )
    gesture = HandGestureRecognizer().recognize(landmarks())
    assert safety.update(gesture, 0.0) is None
    assert safety.update(gesture, 0.25) == gesture
    safety.update(None, 0.30)
    safety.update(None, 0.51)
    assert safety.update(gesture, 0.60) is None
    assert safety.update(gesture, 1.75) == gesture


def test_mouse_scroll_is_one_step_and_dry_run_by_default():
    controller = MouseController()
    result = controller.execute("scroll_down")
    assert "1 passo" in result
    assert "Modo de teste" in result


def test_cursor_mapping_uses_safe_inner_area_and_clamps_edges():
    controller = MouseController()
    assert controller.map_to_screen(0.12, 0.12, 1000, 800) == (0, 0)
    assert controller.map_to_screen(0.88, 0.88, 1000, 800) == (999, 799)
    assert controller.map_to_screen(0.5, 0.5, 1000, 800) == (500, 400)


def test_cursor_moves_without_real_execution_in_dry_run():
    controller = MouseController()
    result = controller.move_cursor(0.5, 0.5)
    assert "Modo de teste" in result
    assert "0.50" in result
