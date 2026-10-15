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

    def double_click_left(self):
        self.calls.append(("double",))
        return "double"

    def press_left(self):
        self.calls.append(("down",))
        return "down"

    def release_left(self):
        self.calls.append(("up",))
        return "up"


def tap(controller, start, release, finish):
    controller.update(True, (0.4, 0.5), start)
    controller.update(True, (0.42, 0.52), release - 0.01)
    controller.update(False, None, release)
    return controller.update(False, None, finish)


def test_single_click_waits_for_double_click_window_then_fires_once():
    mouse = FakeMouse()
    controller = ClickDragController(mouse)
    assert tap(controller, 1.0, 1.25, 1.37) is None
    assert not any(call[0] == "click" for call in mouse.calls)
    assert controller.state() == "Clique detectado — aguardando segundo toque"
    assert controller.update(False, None, 1.70) == ("Clique esquerdo", "click")
    assert [call[0] for call in mouse.calls].count("click") == 1


def test_two_short_pinches_inside_window_make_double_click_not_two_singles():
    mouse = FakeMouse()
    controller = ClickDragController(mouse, double_click_window_seconds=0.32)
    assert tap(controller, 1.0, 1.25, 1.37) is None
    event = tap(controller, 1.40, 1.53, 1.66)
    assert event == ("Clique duplo esquerdo", "double")
    assert [call[0] for call in mouse.calls].count("double") == 1
    assert not any(call[0] == "click" for call in mouse.calls)


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
    assert controller.update(True, (0.5, 0.6), 1.55) == ("Arraste iniciado", "down")
    controller.update(True, (0.6, 0.7), 1.7)
    assert controller.update(False, None, 1.8) == ("Arraste finalizado", "up")
    assert [call[0] for call in mouse.calls].count("down") == 1
    assert [call[0] for call in mouse.calls].count("up") == 1
    assert not any(call[0] in ("click", "double") for call in mouse.calls)


def test_cancel_releases_held_mouse_button_without_clicking():
    mouse = FakeMouse()
    controller = ClickDragController(mouse)
    controller.update(True, (0.4, 0.5), 1.0)
    controller.update(True, (0.5, 0.6), 1.6)
    assert controller.cancel(clear_pending=True) == ("Arraste cancelado", "up")
    assert controller.cancel(clear_pending=True) is None
    assert [call[0] for call in mouse.calls].count("up") == 1
    assert not any(call[0] in ("click", "double") for call in mouse.calls)
