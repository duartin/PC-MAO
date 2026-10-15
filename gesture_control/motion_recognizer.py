"""Temporal swipe recognition with movement threshold and stable re-arming."""
from collections import deque
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Motion:
    name: str
    action: str


class MotionRecognizer:
    """Detect deliberate horizontal/vertical wrist swipes from normalized landmarks."""

    def __init__(self, threshold: float = 0.20, window_seconds: float = 0.55,
                 neutral_seconds: float = 0.30, dominance: float = 1.25):
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.neutral_seconds = neutral_seconds
        self.dominance = dominance
        self._samples = deque()
        self._armed = True
        self._stable_since = None
        self._previous = None

    def reset(self) -> None:
        """Clear the trajectory when tracking is lost."""
        self._samples.clear()
        self._previous = None
        self._stable_since = None
        self._armed = True

    def update(self, landmarks: Optional[Sequence], now: float) -> Optional[Motion]:
        if landmarks is None or len(landmarks) < 1:
            self.reset()
            return None

        wrist = landmarks[0]
        point = (float(wrist.x), float(wrist.y))
        step = 0.0 if self._previous is None else (
            (point[0] - self._previous[0]) ** 2 + (point[1] - self._previous[1]) ** 2
        ) ** 0.5
        self._previous = point

        if step <= 0.012:
            if self._stable_since is None:
                self._stable_since = now
            elif now - self._stable_since >= self.neutral_seconds:
                self._armed = True
        else:
            self._stable_since = None

        self._samples.append((now, point[0], point[1]))
        while self._samples and now - self._samples[0][0] > self.window_seconds:
            self._samples.popleft()

        if not self._armed or len(self._samples) < 2:
            return None
        start = self._samples[0]
        dx, dy = point[0] - start[1], point[1] - start[2]
        ax, ay = abs(dx), abs(dy)
        if max(ax, ay) < self.threshold:
            return None
        if ax >= ay * self.dominance:
            motion = Motion("Deslize para a direita", "page_forward") if dx > 0 else Motion(
                "Deslize para a esquerda", "page_back"
            )
        elif ay >= ax * self.dominance:
            motion = Motion("Deslize para baixo", "scroll_down") if dy > 0 else Motion(
                "Deslize para cima", "scroll_up"
            )
        else:
            return None

        self._armed = False
        self._samples.clear()
        return motion
