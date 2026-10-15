"""Recognize deliberate one-hand pinch-distance changes for zoom control."""
import math
from typing import Optional, Sequence


class PinchZoomRecognizer:
    """Convert normalized thumb/index separation changes into zoom steps.

    Increasing separation zooms in; decreasing separation zooms out. The
    distance is normalized by palm width so hand size and camera distance have
    less influence on the thresholds.
    """

    THUMB_TIP = 4
    INDEX_TIP = 8
    INDEX_MCP = 5
    PINKY_MCP = 17

    def __init__(
        self,
        min_delta: float = 0.11,
        min_interval: float = 0.22,
        smoothing: float = 0.55,
    ):
        if min_delta <= 0 or min_interval < 0:
            raise ValueError("Os limiares da pinça devem ser válidos")
        if not 0 < smoothing <= 1:
            raise ValueError("A suavização deve estar entre 0 e 1")

        self.min_delta = min_delta
        self.min_interval = min_interval
        self.smoothing = smoothing
        self._filtered_ratio = None
        self._anchor_ratio = None
        self._last_event_time = float("-inf")

    def reset(self) -> None:
        """Forget the current hand position after tracking is lost."""
        self._filtered_ratio = None
        self._anchor_ratio = None
        self._last_event_time = float("-inf")

    def _normalized_gap(self, landmarks: Sequence) -> Optional[float]:
        if len(landmarks) <= self.PINKY_MCP:
            return None

        thumb = landmarks[self.THUMB_TIP]
        index = landmarks[self.INDEX_TIP]
        index_base = landmarks[self.INDEX_MCP]
        pinky_base = landmarks[self.PINKY_MCP]

        palm_width = math.hypot(
            float(index_base.x) - float(pinky_base.x),
            float(index_base.y) - float(pinky_base.y),
        )
        if palm_width < 0.025:
            return None

        gap = math.hypot(
            float(thumb.x) - float(index.x),
            float(thumb.y) - float(index.y),
        )
        return gap / palm_width

    def update(self, landmarks: Optional[Sequence], now: float) -> Optional[str]:
        if landmarks is None:
            self.reset()
            return None

        ratio = self._normalized_gap(landmarks)
        if ratio is None:
            self.reset()
            return None

        if self._filtered_ratio is None:
            self._filtered_ratio = ratio
            self._anchor_ratio = ratio
            return None

        alpha = self.smoothing
        self._filtered_ratio = (
            alpha * ratio + (1.0 - alpha) * self._filtered_ratio
        )
        delta = self._filtered_ratio - self._anchor_ratio

        if abs(delta) < self.min_delta:
            return None
        if now - self._last_event_time < self.min_interval:
            return None

        action = "zoom_in" if delta > 0 else "zoom_out"
        self._anchor_ratio = self._filtered_ratio
        self._last_event_time = now
        return action
