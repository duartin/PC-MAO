"""Temporal entry hysteresis for discrete gestures; cursor remains immediate."""


class GestureHysteresis:
    def __init__(self, stable_seconds=0.10, release_grace_seconds=0.06):
        if stable_seconds < 0 or release_grace_seconds < 0:
            raise ValueError("Os tempos de estabilidade precisam ser não negativos")
        self.stable_seconds = float(stable_seconds)
        self.release_grace_seconds = float(release_grace_seconds)
        self._candidate_action = None
        self._candidate_since = None
        self._accepted = None
        self._missing_since = None

    def reset(self):
        self._candidate_action = None
        self._candidate_since = None
        self._accepted = None
        self._missing_since = None

    def update(self, gesture, now):
        """Return a gesture only when a discrete pose survives the entry window."""
        if gesture is None:
            self._candidate_action = None
            self._candidate_since = None
            if self._accepted is None or self._accepted.action == "click_drag":
                self._accepted = None
                self._missing_since = None
                return None
            if self._missing_since is None:
                self._missing_since = float(now)
            if float(now) - self._missing_since >= self.release_grace_seconds:
                self._accepted = None
                self._missing_since = None
                return None
            return self._accepted
        self._missing_since = None
        if gesture.action == "cursor":
            self._candidate_action = None
            self._candidate_since = None
            self._accepted = gesture
            return gesture
        if self._accepted is not None and gesture.action == self._accepted.action:
            self._missing_since = None
            self._candidate_action = gesture.action
            self._candidate_since = float(now) - self.stable_seconds
            self._accepted = gesture
            return gesture
        if gesture.action != self._candidate_action:
            self._candidate_action = gesture.action
            self._candidate_since = float(now)
            self._accepted = None
        if float(now) - self._candidate_since < self.stable_seconds:
            return None
        self._accepted = gesture
        return gesture
