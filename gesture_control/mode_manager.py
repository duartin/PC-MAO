"""Mode switching by short, stable open-hand/fist pose sequences."""
from typing import Optional


class ModeManager:
    """Keep keyboard and mouse actions mutually exclusive.

    Sequences:
      - open, fist, open -> keyboard mode
      - fist, open, fist, open -> mouse mode
    """

    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    OPEN_ACTION = "space"
    FIST_ACTION = "ctrl+s"

    KEYBOARD_SEQUENCE = ("open", "fist", "open")
    MOUSE_SEQUENCE = ("fist", "open", "fist", "open")

    def __init__(
        self,
        initial_mode: str = MOUSE,
        pose_hold_seconds: float = 0.25,
        sequence_timeout_seconds: float = 2.2,
        lost_grace_seconds: float = 0.12,
    ):
        if initial_mode not in (self.KEYBOARD, self.MOUSE):
            raise ValueError("O modo inicial deve ser 'keyboard' ou 'mouse'")
        if pose_hold_seconds <= 0 or sequence_timeout_seconds <= 0:
            raise ValueError("Os tempos de reconhecimento devem ser positivos")

        self.mode = initial_mode
        self.pose_hold_seconds = pose_hold_seconds
        self.sequence_timeout_seconds = sequence_timeout_seconds
        self.lost_grace_seconds = lost_grace_seconds
        self._candidate_action = None
        self._candidate_since = None
        self._last_seen = None
        self._candidate_consumed = False
        self._events = []
        self._last_event_at = None

    def update(self, gesture, now: float) -> Optional[str]:
        """Return the newly activated mode, or None if mode did not change."""
        action = getattr(gesture, "action", None)
        if action not in (self.OPEN_ACTION, self.FIST_ACTION):
            self._expire_sequence(now)
            if (
                self._candidate_action is not None
                and self._last_seen is not None
                and now - self._last_seen >= self.lost_grace_seconds
            ):
                self._candidate_action = None
                self._candidate_since = None
                self._last_seen = None
                self._candidate_consumed = False
            return None

        if action != self._candidate_action:
            self._candidate_action = action
            self._candidate_since = now
            self._candidate_consumed = False

        self._last_seen = now
        if self._candidate_consumed:
            return None
        if now - self._candidate_since < self.pose_hold_seconds:
            return None

        self._candidate_consumed = True
        event = "open" if action == self.OPEN_ACTION else "fist"
        self._expire_sequence(now)

        if self._events and event == self._events[-1]:
            # A repeated pose without the other pose is not a valid double action.
            self._events = [event]
        else:
            self._events.append(event)

        self._last_event_at = now

        # Check the longer sequence first: its final three events also resemble
        # the keyboard sequence, but the intended result is mouse mode.
        if tuple(self._events[-4:]) == self.MOUSE_SEQUENCE:
            self._clear_sequence()
            return self._switch_to(self.MOUSE)

        if tuple(self._events[-3:]) == self.KEYBOARD_SEQUENCE:
            self._clear_sequence()
            return self._switch_to(self.KEYBOARD)

        self._events = self._events[-4:]
        return None

    def _expire_sequence(self, now: float) -> None:
        if (
            self._last_event_at is not None
            and now - self._last_event_at > self.sequence_timeout_seconds
        ):
            self._clear_sequence()

    def _clear_sequence(self) -> None:
        self._events.clear()
        self._last_event_at = None

    def _switch_to(self, mode: str) -> Optional[str]:
        if self.mode == mode:
            return None
        self.mode = mode
        return mode
