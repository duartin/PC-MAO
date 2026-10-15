"""Temporal state machine for thumb-middle click, double-click and drag."""


class ClickDragController:
    """Tap-click is buffered for a double-click window; hold starts a drag."""

    MIN_CLICK_SECONDS = 0.12
    RELEASE_STABILITY_SECONDS = 0.12
    DRAG_HOLD_SECONDS = 0.55
    DOUBLE_CLICK_WINDOW_SECONDS = 0.32

    def __init__(self, mouse, min_click_seconds=MIN_CLICK_SECONDS,
                 drag_hold_seconds=DRAG_HOLD_SECONDS,
                 release_stability_seconds=RELEASE_STABILITY_SECONDS,
                 double_click_window_seconds=DOUBLE_CLICK_WINDOW_SECONDS):
        if min_click_seconds < 0 or drag_hold_seconds <= min_click_seconds:
            raise ValueError("Os tempos de clique/arraste precisam ser válidos")
        if release_stability_seconds < 0:
            raise ValueError("A estabilização de soltura não pode ser negativa")
        if double_click_window_seconds <= 0:
            raise ValueError("A janela do clique duplo precisa ser positiva")
        self.mouse = mouse
        self.min_click_seconds = min_click_seconds
        self.drag_hold_seconds = drag_hold_seconds
        self.release_stability_seconds = release_stability_seconds
        self.double_click_window_seconds = double_click_window_seconds
        self._active = False
        self._started_at = None
        self._release_since = None
        self._dragging = False
        self._pending_click_at = None

    def update(self, active, point, now):
        """Update from tracked poses; return (event, message) or None."""
        if self._pending_click_at is not None and now - self._pending_click_at > self.double_click_window_seconds:
            self._pending_click_at = None
            self._click_ready = ("Clique esquerdo", self.mouse.click_left())
        else:
            self._click_ready = None

        if active:
            self._release_since = None
            if point is not None:
                self.mouse.move_cursor(point[0], point[1])
            if not self._active:
                self._active = True
                self._started_at = now
                self._dragging = False
                return self._click_ready
            if not self._dragging and now - self._started_at >= self.drag_hold_seconds:
                message = self.mouse.press_left()
                self._dragging = True
                return ("Arraste iniciado", message)
            return self._click_ready

        if not self._active:
            if self._click_ready is not None:
                return self._click_ready
            return None

        if self._dragging:
            message = self.mouse.release_left()
            self._reset_active()
            return "Arraste finalizado", message

        if self._release_since is None:
            self._release_since = now
            return self._click_ready
        if now - self._release_since < self.release_stability_seconds:
            return self._click_ready

        duration = self._release_since - self._started_at
        self._reset_active()
        if duration < self.min_click_seconds:
            return self._click_ready
        if self._pending_click_at is not None and now - self._pending_click_at <= self.double_click_window_seconds:
            self._pending_click_at = None
            return "Clique duplo esquerdo", self.mouse.double_click_left()
        self._pending_click_at = now
        return self._click_ready

    def flush_pending(self):
        """Emit the buffered single click when the application is closing."""
        if self._pending_click_at is None:
            return None
        self._pending_click_at = None
        return "Clique esquerdo", self.mouse.click_left()

    def state(self, now=None):
        if self._dragging:
            return "Arrastando — solte a pinça para finalizar"
        if self._active:
            return "Pinça ativa — mantenha para iniciar arraste"
        if self._pending_click_at is not None:
            return "Clique detectado — aguardando segundo toque"
        return "Aguardando gesto"

    def cancel(self, clear_pending=False):
        """Cancel a candidate click; always release the button after a drag."""
        if clear_pending:
            self._pending_click_at = None
        if self._dragging:
            message = self.mouse.release_left()
            self._reset_active()
            return "Arraste cancelado", message
        self._reset_active()
        return None

    def _reset_active(self):
        self._active = False
        self._started_at = None
        self._release_since = None
        self._dragging = False
