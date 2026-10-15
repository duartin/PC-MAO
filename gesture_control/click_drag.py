"""Click/drag state machine using a dedicated thumb-middle pinch gesture."""


class ClickDragController:
    """A short pinch clicks; holding it starts drag, and release ends drag."""

    MIN_CLICK_SECONDS = 0.12
    RELEASE_STABILITY_SECONDS = 0.12
    DRAG_HOLD_SECONDS = 0.55

    def __init__(self, mouse, min_click_seconds=MIN_CLICK_SECONDS,
                 drag_hold_seconds=DRAG_HOLD_SECONDS,
                 release_stability_seconds=RELEASE_STABILITY_SECONDS):
        if min_click_seconds < 0 or drag_hold_seconds <= min_click_seconds:
            raise ValueError("Os tempos de clique/arraste precisam ser válidos")
        if release_stability_seconds < 0:
            raise ValueError("A estabilização de soltura não pode ser negativa")
        self.mouse = mouse
        self.min_click_seconds = min_click_seconds
        self.drag_hold_seconds = drag_hold_seconds
        self.release_stability_seconds = release_stability_seconds
        self._active = False
        self._started_at = None
        self._release_since = None
        self._dragging = False

    def update(self, active, point, now):
        """Update from a tracked pose; return (event, message) or None."""
        if active:
            self._release_since = None
            if point is not None:
                self.mouse.move_cursor(point[0], point[1])
            if not self._active:
                self._active = True
                self._started_at = now
                self._dragging = False
                return None
            if (
                not self._dragging
                and now - self._started_at >= self.drag_hold_seconds
            ):
                message = self.mouse.press_left()
                self._dragging = True
                return "Arraste iniciado", message
            return None

        if not self._active:
            return None

        if self._dragging:
            message = self.mouse.release_left()
            self._reset()
            return "Arraste finalizado", message

        if self._release_since is None:
            self._release_since = now
            return None
        if now - self._release_since < self.release_stability_seconds:
            return None

        duration = self._release_since - self._started_at
        self._reset()
        if duration >= self.min_click_seconds:
            return "Clique esquerdo", self.mouse.click_left()
        return None

    def cancel(self):
        """Cancel a candidate click; always release the button after a drag."""
        if self._dragging:
            message = self.mouse.release_left()
            self._reset()
            return "Arraste cancelado", message
        self._reset()
        return None

    def _reset(self):
        self._active = False
        self._started_at = None
        self._release_since = None
        self._dragging = False
