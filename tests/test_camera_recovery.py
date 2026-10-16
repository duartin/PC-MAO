from gesture_control.camera_capture import camera_backends


def test_windows_prefers_directshow_and_keeps_opencv_fallback():
    assert camera_backends("Windows", 700, 0) == [700, 0]


def test_other_platforms_use_default_backend():
    assert camera_backends("Linux", 700, 0) == [0]


def test_windows_without_directshow_constant_uses_default_backend():
    assert camera_backends("Windows", None, 0) == [0]
