"""Smoothed temporal swipe recognition using palm-center movement."""
from collections import deque
from dataclasses import dataclass
import math
from typing import Optional, Sequence


@dataclass(frozen=True)
class Motion:
    name: str
    action: str


class MotionRecognizer:
    """Recognize deliberate swipes while rejecting tremor and diagonal motion."""

    PALM_LANDMARKS = (0, 5, 9, 13, 17)

    def __init__(
        self,
        threshold: float = 0.10,
        window_seconds: float = 0.80,
        neutral_seconds: float = 0.28,
        dominance: float = 1.25,
        sensitivity: float = 1.0,
        smoothing: float = 0.65,
        enable_vertical: bool = True,
    ):
        if not 0.5 <= sensitivity <= 2.0:
            raise ValueError("A sensibilidade deve estar entre 0.5 e 2.0")

        self.threshold = threshold
        self.window_seconds = window_seconds
        self.neutral_seconds = neutral_seconds
        self.dominance = dominance
        self.sensitivity = sensitivity
        self.smoothing = smoothing
        self.enable_vertical = enable_vertical
        self._samples = deque()
        self._armed = True
        self._stable_since = None
        self._previous = None
        self._filtered = None

    def reset(self) -> None:
        """Clear the trajectory when tracking is lost."""
        self._samples.clear()
        self._previous = None
        self._filtered = None
        self._stable_since = None
        self._armed = True

    @staticmethod
    def _distance(a, b) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _palm_center(self, landmarks: Sequence):
        if len(landmarks) > max(self.PALM_LANDMARKS):
            xs = [float(landmarks[i].x) for i in self.PALM_LANDMARKS]
            ys = [float(landmarks[i].y) for i in self.PALM_LANDMARKS]
            center = (sum(xs) / len(xs), sum(ys) / len(ys))
            width = math.hypot(
                float(landmarks[5].x) - float(landmarks[17].x),
                float(landmarks[5].y) - float(landmarks[17].y),
            )
            return center, width

        point = (float(landmarks[0].x), float(landmarks[0].y))
        return point, 0.0

    def update(self, landmarks: Optional[Sequence], now: float) -> Optional[Motion]:
        if landmarks is None or len(landmarks) <= 0:
            self.reset()
            return None

        raw, palm_width = self._palm_center(landmarks)

        if self._filtered is None:
            point = raw
        else:
            alpha = self.smoothing
            point = (
                alpha * raw[0] + (1.0 - alpha) * self._filtered[0],
                alpha * raw[1] + (1.0 - alpha) * self._filtered[1],
            )

        step = (
            0.0
            if self._filtered is None
            else self._distance(point, self._filtered)
        )
        self._filtered = point

        if step <= 0.008:
            if self._stable_since is None:
                self._stable_since = now
            elif now - self._stable_since >= self.neutral_seconds:
                self._armed = True
        else:
            self._stable_since = None

        self._samples.append((now, point[0], point[1]))
        while (
            self._samples
            and now - self._samples[0][0] > self.window_seconds
        ):
            self._samples.popleft()

        if not self._armed or len(self._samples) < 3:
            return None

        start = self._samples[0]
        dx = point[0] - start[1]
        dy = point[1] - start[2]
        ax, ay = abs(dx), abs(dy)
        net_distance = math.hypot(dx, dy)

        path_distance = sum(
            math.hypot(b[1] - a[1], b[2] - a[2])
            for a, b in zip(self._samples, list(self._samples)[1:])
        )

        # Repeated wobble has a long path but little net travel; reject it.
        if path_distance <= 0.0 or net_distance / path_distance < 0.58:
            return None

        vertical_threshold = (
            max(self.threshold, palm_width * 0.42) / self.sensitivity
        )
        horizontal_threshold = (
            max(self.threshold * 1.30, palm_width * 0.60)
            / self.sensitivity
        )

        if ay >= vertical_threshold and ay >= ax * self.dominance:
            if not self.enable_vertical:
                return None
            motion = (
                Motion("Deslize para baixo", "scroll_down")
                if dy > 0
                else Motion("Deslize para cima", "scroll_up")
            )
        elif ax >= horizontal_threshold and ax >= ay * self.dominance:
            motion = (
                Motion("Deslize para a direita", "page_forward")
                if dx > 0
                else Motion("Deslize para a esquerda", "page_back")
            )
        else:
            return None

        self._armed = False
        self._samples.clear()
        return motion
