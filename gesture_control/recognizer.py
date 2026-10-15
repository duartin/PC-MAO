"""Conservative geometric recognition of a small set of hand poses."""
from dataclasses import dataclass
import math
from typing import Optional, Sequence

WRIST = 0
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 3, 2
INDEX_TIP, INDEX_PIP, INDEX_MCP = 8, 6, 5
MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP = 12, 10, 9
RING_TIP, RING_PIP, RING_MCP = 16, 14, 13
PINKY_TIP, PINKY_PIP, PINKY_MCP = 20, 18, 17


@dataclass(frozen=True)
class Gesture:
    name: str
    action: str
    confidence: float


class HandGestureRecognizer:
    """Recognizes only broad, separable poses; ambiguous letter shapes are omitted."""

    def __init__(self, min_confidence: float = 0.78,
                 click_pinch_threshold: float = 0.32):
        if not 0.12 <= click_pinch_threshold <= 0.60:
            raise ValueError("O limiar da pinça precisa ficar entre 0,12 e 0,60")
        self.min_confidence = min_confidence
        self.click_pinch_threshold = float(click_pinch_threshold)

    @staticmethod
    def _finger_extended(points: Sequence, tip: int, pip: int, mcp: int) -> bool:
        return points[tip].y < points[pip].y - 0.015 and points[pip].y < points[mcp].y + 0.04

    @staticmethod
    def _finger_extended_down(points: Sequence, tip: int, pip: int, mcp: int) -> bool:
        return points[tip].y > points[pip].y + 0.045 and points[pip].y > points[mcp].y + 0.015

    @staticmethod
    def _thumb_sideways(points: Sequence) -> bool:
        return abs(points[THUMB_TIP].x - points[THUMB_IP].x) > 0.055

    @staticmethod
    def _thumb_vertical(points: Sequence) -> bool:
        return abs(points[THUMB_TIP].y - points[THUMB_IP].y) > 0.075

    @staticmethod
    def _palm_width(points):
        return math.hypot(points[INDEX_MCP].x - points[PINKY_MCP].x,
                          points[INDEX_MCP].y - points[PINKY_MCP].y)

    @classmethod
    def middle_pinch_ratio(cls, points):
        """Return thumb-middle distance normalized by palm width, or None."""
        if points is None or len(points) < 21:
            return None
        palm_width = cls._palm_width(points)
        if palm_width < 0.025:
            return None
        gap = math.hypot(points[THUMB_TIP].x - points[MIDDLE_TIP].x,
                         points[THUMB_TIP].y - points[MIDDLE_TIP].y)
        return gap / palm_width

    @classmethod
    def _pinch_pose(cls, points: Sequence) -> bool:
        palm_width = cls._palm_width(points)
        if palm_width < 0.025:
            return False
        gap = math.hypot(points[THUMB_TIP].x - points[INDEX_TIP].x,
                         points[THUMB_TIP].y - points[INDEX_TIP].y)
        index_reach = math.hypot(points[INDEX_TIP].x - points[INDEX_MCP].x,
                                 points[INDEX_TIP].y - points[INDEX_MCP].y)
        return gap / palm_width < 0.60 and index_reach / palm_width > 0.55

    @classmethod
    def _middle_pinch_pose(cls, points: Sequence, extended, extended_down,
                           threshold=0.32) -> bool:
        palm_width = cls._palm_width(points)
        if palm_width < 0.025 or not extended[0]:
            return False
        gap = math.hypot(points[THUMB_TIP].x - points[MIDDLE_TIP].x,
                         points[THUMB_TIP].y - points[MIDDLE_TIP].y)
        index_reach = math.hypot(points[INDEX_TIP].x - points[INDEX_MCP].x,
                                 points[INDEX_TIP].y - points[INDEX_MCP].y)
        middle_curled = not extended[1] and not extended_down[1]
        ring_and_pinky_curled = not any(extended[2:]) and not any(extended_down[2:])
        return (gap / palm_width < threshold and index_reach / palm_width > 0.55
                and middle_curled and ring_and_pinky_curled)

    @classmethod
    def _ring_pinch_pose(cls, points: Sequence, extended, extended_down) -> bool:
        palm_width = cls._palm_width(points)
        if palm_width < 0.025 or not extended[0] or not extended[1]:
            return False
        gap = math.hypot(points[THUMB_TIP].x - points[RING_TIP].x,
                         points[THUMB_TIP].y - points[RING_TIP].y)
        ring_curled = not extended[2] and not extended_down[2]
        pinky_curled = not extended[3] and not extended_down[3]
        return gap / palm_width < 0.34 and ring_curled and pinky_curled

    def recognize(self, points: Sequence) -> Optional[Gesture]:
        if len(points) < 21:
            return None
        extended = [
            self._finger_extended(points, INDEX_TIP, INDEX_PIP, INDEX_MCP),
            self._finger_extended(points, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
            self._finger_extended(points, RING_TIP, RING_PIP, RING_MCP),
            self._finger_extended(points, PINKY_TIP, PINKY_PIP, PINKY_MCP),
        ]
        extended_down = [
            self._finger_extended_down(points, INDEX_TIP, INDEX_PIP, INDEX_MCP),
            self._finger_extended_down(points, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
            self._finger_extended_down(points, RING_TIP, RING_PIP, RING_MCP),
            self._finger_extended_down(points, PINKY_TIP, PINKY_PIP, PINKY_MCP),
        ]
        count = sum(extended)
        thumb_y = points[THUMB_TIP].y - points[THUMB_IP].y
        thumb_vertical = self._thumb_vertical(points)
        if count == 0 and thumb_vertical:
            if thumb_y < -0.04:
                return Gesture("Polegar para cima", "enter", 0.88)
            if thumb_y > 0.04:
                return Gesture("Polegar para baixo", "esc", 0.88)
        if count == 4 and self._thumb_sideways(points):
            return Gesture("Mão aberta", "space", 0.90)
        if extended[0] and extended[1] and not any(extended[2:]):
            if self._ring_pinch_pose(points, extended, extended_down):
                return Gesture("Pinça polegar-anelar", "right_click", 0.90)
            return Gesture("Dois dedos para cima", "scroll_up", 0.88)
        if extended_down[0] and extended_down[1] and not any(extended_down[2:]):
            return Gesture("Dois dedos para baixo", "scroll_down", 0.88)
        if self._pinch_pose(points):
            return Gesture("Pinça", "pinch", 0.90)
        if self._ring_pinch_pose(points, extended, extended_down):
            return Gesture("Pinça polegar-anelar", "right_click", 0.90)
        if self._middle_pinch_pose(
            points, extended, extended_down, self.click_pinch_threshold
        ):
            return Gesture("Pinça polegar-médio", "click_drag", 0.90)
        if extended[0] and not any(extended[1:]) and not any(extended_down[1:]):
            return Gesture("Indicador apontado", "cursor", 0.90)
        if count == 0 and not thumb_vertical:
            return Gesture("Punho fechado", "ctrl+s", 0.84)
        return None

    def confident(self, gesture: Optional[Gesture]) -> bool:
        return gesture is not None and gesture.confidence >= self.min_confidence
