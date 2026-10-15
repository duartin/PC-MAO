from gesture_control.click_drag import ClickDragController


class FakeMouse:
    def __init__(self):
        self.calls = []

    def move_cursor(self, x, y):
        self.calls.append(("move", x, y))
        return "cursor"

    def click_left(self):
        self.calls.append(("click",))
        return "click"

    def press_left(self):
        self.calls.append(("down",))
        return "down"

    def release_left(self):
        self.calls.append(("up",))
        return "up"


def test_short_thumb_middle_pinch_clicks_once_on_release():
    mouse = FakeMouse()
    controller = ClickDragController(mouse)
    assert controller.update(True, (0.4, 0.5), 1.0) is None
    assert controller.update(True, (0.42, 0.52), 1.2) is None
    assert controller.update(False, None, 1.25) is None
    assert controller.update(False, None, 1.37) == ("Clique esquerdo", "click")
    assert [call[0] for call in mouse.calls].count("click") == 1


def test_very_short_noisy_pinch_does_not_click():
    mouse = FakeMouse()
    controller = ClickDragController(mouse)
    controller.update(True, (0.4, 0.5), 1.0)
    assert controller.update(False, None, 1.05) is None
    assert not any(call[0] == "click" for call in mouse.calls)


def test_held_pinch_starts_drag_and_release_ends_it():
    mouse = FakeMouse()
    controller = ClickDragController(mouse)
    controller.update(True, (0.4, 0.5), 1.0)
    assert controller.update(True, (0.5, 0.6), 1.55) == (
        "Arraste iniciado",
        "down",
    )
    controller.update(True, (0.6, 0.7), 1.7)
    assert controller.update(False, None, 1.8) == (
        "Arraste finalizado",
        "up",
    )
    assert [call[0] for call in mouse.calls].count("down") == 1
    assert [call[0] for call in mouse.calls].count("up") == 1
    assert not any(call[0] == "click" for call in mouse.calls)


def test_cancel_releases_held_mouse_button_without_clicking():
    mouse = FakeMouse()
    controller = ClickDragController(mouse)
    controller.update(True, (0.4, 0.5), 1.0)
    controller.update(True, (0.5, 0.6), 1.6)
    assert controller.cancel() == ("Arraste cancelado", "up")
    assert controller.cancel() is None
    assert [call[0] for call in mouse.calls].count("up") == 1
    assert not any(call[0] == "click" for call in mouse.calls)
