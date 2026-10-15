from types import SimpleNamespace

from gesture_control.mode_manager import ModeManager


def gesture(action):
    return SimpleNamespace(action=action)


def perform_pose(manager, action, start):
    manager.update(gesture(action), start)
    return manager.update(gesture(action), start + 0.26)


def test_starts_in_mouse_mode_and_open_fist_open_switches_to_keyboard():
    manager = ModeManager(initial_mode="mouse")

    assert manager.mode == "mouse"
    assert perform_pose(manager, "space", 0.0) is None
    assert perform_pose(manager, "ctrl+s", 0.4) is None
    assert perform_pose(manager, "space", 0.8) == "keyboard"
    assert manager.mode == "keyboard"


def test_fist_open_fist_open_switches_to_mouse_without_keyboard_overlap():
    manager = ModeManager(initial_mode="keyboard")

    assert perform_pose(manager, "ctrl+s", 0.0) is None
    assert perform_pose(manager, "space", 0.4) is None
    assert perform_pose(manager, "ctrl+s", 0.8) is None
    assert perform_pose(manager, "space", 1.2) == "mouse"
    assert manager.mode == "mouse"


def test_pose_must_be_stable_and_incomplete_sequence_expires():
    manager = ModeManager(
        initial_mode="mouse",
        pose_hold_seconds=0.25,
        sequence_timeout_seconds=1.0,
    )

    assert manager.update(gesture("space"), 0.0) is None
    assert manager.update(gesture("space"), 0.10) is None
    assert manager.update(gesture("space"), 0.26) is None
    assert manager.update(gesture("ctrl+s"), 1.1) is None
    assert manager.update(gesture("ctrl+s"), 1.36) is None
    assert manager.update(gesture("space"), 1.5) is None
    assert manager.update(gesture("space"), 1.76) is None
    assert manager.mode == "mouse"
