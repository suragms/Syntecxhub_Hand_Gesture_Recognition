"""MediaPipe Hands adapter that exposes dependency-free application models."""

from __future__ import annotations

import logging
from typing import Any

from config import DetectorConfig
from core.models import HandObservation, Handedness, Point3D

LOGGER = logging.getLogger(__name__)


class HandDetectorError(RuntimeError):
    """Raised when MediaPipe cannot initialize or process a frame."""


class HandDetector:
    """Detect up to two hands and return normalized twenty-one-point landmarks."""

    def __init__(self, config: DetectorConfig) -> None:
        self.config = config
        self._hands: Any | None = None
        self._drawing_connections: Any | None = None

    @property
    def connections(self) -> Any | None:
        """MediaPipe connection topology for visualizers, if initialized."""
        return self._drawing_connections

    def open(self) -> None:
        """Initialize MediaPipe once for the full camera session."""
        if self._hands is not None:
            return
        import os
        import warnings
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        os.environ.setdefault("GLOG_minloglevel", "2")
        warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
        try:
            import mediapipe as mp
        except ImportError as error:  # pragma: no cover - dependency environment
            raise HandDetectorError(
                "MediaPipe is not installed. Install requirements.txt with Python 3.11."
            ) from error
        if not hasattr(mp, "solutions"):
            raise HandDetectorError(
                "This MediaPipe installation does not expose the legacy Hands API required "
                "by this release. Create the documented Python 3.11 virtual environment "
                "and install the pinned requirements.txt dependencies."
            )
        try:
            hands_solution = mp.solutions.hands
            self._hands = hands_solution.Hands(
                static_image_mode=False,
                max_num_hands=self.config.max_hands,
                model_complexity=self.config.model_complexity,
                min_detection_confidence=self.config.min_detection_confidence,
                min_tracking_confidence=self.config.min_tracking_confidence,
            )
            self._drawing_connections = hands_solution.HAND_CONNECTIONS
            LOGGER.info("Initialized MediaPipe Hands for up to %s hand(s).", self.config.max_hands)
        except Exception as error:  # pragma: no cover - native initialization varies
            raise HandDetectorError(f"Unable to initialize MediaPipe Hands: {error}") from error

    def process(self, bgr_frame: Any, *, timestamp: float) -> list[HandObservation]:
        """Detect visible hands in one BGR OpenCV frame."""
        if self._hands is None:
            raise HandDetectorError("Hand detector is not initialized.")
        if bgr_frame is None or getattr(bgr_frame, "size", 0) == 0:
            raise HandDetectorError("Cannot process an empty camera frame.")
        try:
            import cv2

            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results = self._hands.process(rgb_frame)
            rgb_frame.flags.writeable = True
        except Exception as error:  # pragma: no cover - native backend behavior
            raise HandDetectorError(f"MediaPipe failed while processing a frame: {error}") from error

        landmarks_by_hand = results.multi_hand_landmarks or []
        handedness_by_hand = results.multi_handedness or []
        detected: list[HandObservation] = []
        for index, hand_landmarks in enumerate(landmarks_by_hand[: self.config.max_hands]):
            handedness = Handedness.UNKNOWN
            handedness_confidence: float | None = None
            if index < len(handedness_by_hand) and handedness_by_hand[index].classification:
                label = handedness_by_hand[index].classification[0]
                try:
                    handedness = Handedness(label.label.lower())
                except ValueError:
                    handedness = Handedness.UNKNOWN
                handedness_confidence = float(label.score)
            points = tuple(
                Point3D(float(point.x), float(point.y), float(point.z))
                for point in hand_landmarks.landmark
            )
            if len(points) != 21:
                LOGGER.warning("Ignoring MediaPipe hand with %s instead of 21 landmarks.", len(points))
                continue
            detected.append(
                HandObservation(
                    landmarks=points,
                    timestamp=timestamp,
                    handedness=handedness,
                    # Legacy MediaPipe Hands exposes handedness certainty, not a
                    # landmark-quality score. Its accepted observations therefore
                    # use neutral confidence; the label score remains metadata.
                    confidence=1.0,
                    handedness_confidence=handedness_confidence,
                )
            )
        return detected

    def close(self) -> None:
        """Release MediaPipe native resources."""
        if self._hands is not None:
            self._hands.close()
            self._hands = None
            self._drawing_connections = None
            LOGGER.info("Closed MediaPipe Hands.")

    def __enter__(self) -> "HandDetector":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
