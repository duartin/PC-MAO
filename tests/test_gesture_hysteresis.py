from types import SimpleNamespace

from gesture_control.gesture_hysteresis import GestureHysteresis


def test_transient_discrete_pose_is_not_accepted_until_stable():
    gate = GestureHysteresis(stable_seconds=0.10)
    pose = SimpleNamespace(name="Rolagem", action="scroll_up", confidence=0.9)
    assert gate.update(pose, 1.0) is None
    assert gate.update(None, 1.05) is None
    assert gate.update(pose, 1.08) is None
    assert gate.update(pose, 1.19) == pose


def test_brief_tracking_gap_keeps_static_pose_then_releases():
    gate = GestureHysteresis(stable_seconds=0.0, release_grace_seconds=0.06)
    pose = SimpleNamespace(name="Dois dedos", action="scroll_up", confidence=0.9)
    assert gate.update(pose, 1.0) == pose
    assert gate.update(None, 1.03) == pose
    assert gate.update(None, 1.10) is None


def test_cursor_is_returned_immediately_without_discrete_pose_delay():
    gate = GestureHysteresis(stable_seconds=0.25)
    cursor = SimpleNamespace(name="Indicador", action="cursor", confidence=0.9)
    assert gate.update(cursor, 2.0) == cursor
