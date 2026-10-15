"""One-shot gesture confirmation and re-arming safety state machine."""
from dataclasses import dataclass
from typing import Optional
from .recognizer import Gesture


@dataclass
class SafetySettings:
    hold_seconds: float = 0.65
    cooldown_seconds: float = 1.2
    neutral_seconds: float = 0.45
    min_confidence: float = 0.78


class SafetyManager:
    def __init__(self, settings: Optional[SafetySettings] = None):
        self.settings = settings or SafetySettings()
        self._candidate = None
        self._candidate_since = 0.0
        self._neutral_since = None
        self._armed = True
        self._last_action = float("-inf")

    def update(self, gesture: Optional[Gesture], now: float) -> Optional[Gesture]:
        if gesture is None or gesture.confidence < self.settings.min_confidence:
            self._candidate = None
            if self._neutral_since is None:
                self._neutral_since = now
            elif now - self._neutral_since >= self.settings.neutral_seconds:
                self._armed = True
            return None

        self._neutral_since = None
        if gesture.name != self._candidate:
            self._candidate = gesture.name
            self._candidate_since = now
            return None
        if not self._armed or now - self._candidate_since < self.settings.hold_seconds:
            return None
        if now - self._last_action < self.settings.cooldown_seconds:
            return None
        self._armed = False
        self._last_action = now
        return gesture
