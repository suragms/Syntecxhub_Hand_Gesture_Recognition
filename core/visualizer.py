"""Fresh-frame OpenCV overlays for hand tracking and application status."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.models import HandObservation, RecognizedHand


class Visualizer:
    """Draw readable landmark, classification, and runtime status overlays."""

    LANDMARK_COLOR = (0, 220, 0)
    CONNECTION_COLOR = (255, 125, 0)
    TEXT_COLOR = (255, 255, 255)
    ACTION_COLOR = (255, 255, 0)
    WARNING_COLOR = (0, 215, 255)
    ERROR_COLOR = (0, 0, 255)

    def __init__(self, show_landmarks: bool = True) -> None:
        self.show_landmarks = show_landmarks

    @staticmethod
    def _point(landmark: Any, width: int, height: int) -> tuple[int, int]:
        return (
            max(0, min(width - 1, round(landmark.x * width))),
            max(0, min(height - 1, round(landmark.y * height))),
        )

    @staticmethod
    def _text(
        frame: Any,
        text: str,
        origin: tuple[int, int],
        color: tuple[int, int, int],
        scale: float = 0.55,
        thickness: int = 1,
    ) -> None:
        import cv2

        height, width = frame.shape[:2]
        (text_width, text_height), _ = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness
        )
        x = max(4, min(origin[0], max(4, width - text_width - 4)))
        y = max(text_height + 4, min(origin[1], height - 4))
        cv2.putText(
            frame,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )

    def draw_hand(
        self,
        frame: Any,
        hand: RecognizedHand,
        connections: Iterable[tuple[int, int]] | None = None,
    ) -> None:
        """Draw a hand's points, finger connections, box, and classification."""
        import cv2

        if not self.show_landmarks:
            return
        height, width = frame.shape[:2]
        points = [self._point(point, width, height) for point in hand.landmarks.raw]
        if connections:
            for start, end in connections:
                if start < len(points) and end < len(points):
                    cv2.line(frame, points[start], points[end], self.CONNECTION_COLOR, 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(frame, point, 3, self.LANDMARK_COLOR, -1, cv2.LINE_AA)
        left = min(point[0] for point in points)
        right = max(point[0] for point in points)
        top = min(point[1] for point in points)
        bottom = max(point[1] for point in points)
        padding = 10
        cv2.rectangle(
            frame,
            (max(0, left - padding), max(0, top - padding)),
            (min(width - 1, right + padding), min(height - 1, bottom + padding)),
            self.LANDMARK_COLOR,
            2,
        )
        label = hand.landmarks.handedness.value.title()
        raw_gesture = hand.prediction.gesture.value.upper()
        stable_gesture = hand.smoothed_gesture.gesture.value.upper()
        label += f" | {raw_gesture}"
        if hand.smoothed_gesture.stable:
            label += f" → {stable_gesture}"
        self._text(frame, label, (left, top - 14), self.TEXT_COLOR)

    def draw_status(
        self,
        frame: Any,
        *,
        fps: float | None,
        action_status: str,
        actions_enabled: bool,
        warning: str | None = None,
        error: str | None = None,
    ) -> None:
        """Draw top-level, non-overlapping status messages on a fresh frame."""
        import cv2

        height, width = frame.shape[:2]
        banner_height = 84
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, min(height, banner_height)), (25, 25, 25), -1)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
        fps_text = "FPS: --" if fps is None else f"FPS: {fps:.1f}"
        control_text = "ACTIONS: ENABLED" if actions_enabled else "ACTIONS: DISABLED / SIMULATED"
        self._text(frame, fps_text, (10, 24), self.TEXT_COLOR)
        self._text(frame, control_text, (10, 49), self.ACTION_COLOR if actions_enabled else self.WARNING_COLOR)
        self._text(frame, f"Action: {action_status}", (10, 74), self.ACTION_COLOR)
        if warning:
            self._text(frame, warning, (10, height - 34), self.WARNING_COLOR)
        if error:
            self._text(frame, error, (10, height - 10), self.ERROR_COLOR)

    def draw_controls(self, frame: Any) -> None:
        """Draw the standard demo keyboard shortcut legend."""
        height, width = frame.shape[:2]
        self._text(frame, "Q: Quit  A: Actions  R: Reset  S: Screenshot", (width - 310, height - 10), self.TEXT_COLOR, 0.43)
