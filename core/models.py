"""Shared, dependency-free data models for hand-gesture recognition.

The core package deliberately uses its own small value objects rather than types
from a detector SDK.  An integration layer can therefore adapt MediaPipe (or any
other tracker) at its boundary without making the recognition logic optional.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Deque, Optional, Tuple


LANDMARK_COUNT = 21


class Handedness(str, Enum):
    """The physical hand reported by a detector, when it is known."""

    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


class Gesture(str, Enum):
    """Gestures recognised by the rule-based classifier.

    The first four entries are the deliberate initial application vocabulary.
    Extended entries are retained for future configuration, but do not map to
    system actions by default.
    """

    UNKNOWN = "unknown"
    OPEN_PALM = "open_palm"
    FIST = "fist"
    # Backward-compatible spelling for integrations that use the older name.
    CLOSED_FIST = "fist"
    POINTING = "pointing"
    PEACE = "peace"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PINCH = "pinch"


class Finger(str, Enum):
    """Names of the five human fingers."""

    THUMB = "thumb"
    INDEX = "index"
    MIDDLE = "middle"
    RING = "ring"
    PINKY = "pinky"


@dataclass(frozen=True, slots=True)
class Point3D:
    """A finite 3-D point in detector coordinate space."""

    x: float
    y: float
    z: float = 0.0

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (self.x, self.y, self.z)):
            raise ValueError("Point coordinates must be finite numbers.")

    def distance_to(self, other: "Point3D") -> float:
        """Return Euclidean distance to *other*."""
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        ) ** 0.5

    def __add__(self, other: "Point3D") -> "Point3D":
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Point3D") -> "Point3D":
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def scaled(self, factor: float) -> "Point3D":
        """Return a point/vector multiplied by *factor*."""
        return Point3D(self.x * factor, self.y * factor, self.z * factor)


@dataclass(frozen=True, slots=True)
class HandObservation:
    """Raw landmarks for one hand at a particular moment.

    ``landmarks`` follows the common 21-point hand-landmark ordering used by
    MediaPipe.  The object intentionally has no dependency on MediaPipe; use
    :class:`LandmarkProcessor` to adapt provider objects into this model.
    """

    landmarks: Tuple[Point3D, ...]
    timestamp: float
    handedness: Handedness = Handedness.UNKNOWN
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if len(self.landmarks) != LANDMARK_COUNT:
            raise ValueError(f"A hand observation requires {LANDMARK_COUNT} landmarks.")
        if not isfinite(self.timestamp):
            raise ValueError("Observation timestamp must be finite.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Observation confidence must be in [0, 1].")


@dataclass(frozen=True, slots=True)
class ProcessedLandmarks:
    """Validated landmarks plus scale-normalised geometry for classification."""

    raw: Tuple[Point3D, ...]
    normalized: Tuple[Point3D, ...]
    timestamp: float
    handedness: Handedness
    detector_confidence: float
    palm_size: float
    palm_center: Point3D

    def __post_init__(self) -> None:
        if len(self.raw) != LANDMARK_COUNT or len(self.normalized) != LANDMARK_COUNT:
            raise ValueError(f"Processed landmarks require {LANDMARK_COUNT} points.")
        if self.palm_size <= 0.0 or not isfinite(self.palm_size):
            raise ValueError("Palm size must be a positive finite value.")

    @property
    def wrist(self) -> Point3D:
        """The raw wrist landmark (index 0)."""
        return self.raw[0]


@dataclass(frozen=True, slots=True)
class FingerState:
    """Measured state of one finger used to explain a classification."""

    finger: Finger
    extended: bool
    bend_angle_degrees: float
    extension_ratio: float


@dataclass(frozen=True, slots=True)
class GesturePrediction:
    """One classifier decision before temporal smoothing."""

    gesture: Gesture
    confidence: float
    timestamp: float
    finger_states: Tuple[FingerState, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Gesture confidence must be in [0, 1].")
        if not isfinite(self.timestamp):
            raise ValueError("Prediction timestamp must be finite.")


@dataclass(frozen=True, slots=True)
class SmoothedGesture:
    """A temporally aggregated gesture decision for a single track."""

    gesture: Gesture
    confidence: float
    stability: float
    stable: bool
    timestamp: float
    sample_count: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Smoothed confidence must be in [0, 1].")
        if not 0.0 <= self.stability <= 1.0:
            raise ValueError("Gesture stability must be in [0, 1].")
        if self.sample_count < 0:
            raise ValueError("Sample count cannot be negative.")


@dataclass(frozen=True, slots=True)
class TrackSample:
    """An historical point in a hand track."""

    timestamp: float
    wrist: Point3D
    gesture: Gesture = Gesture.UNKNOWN


@dataclass(slots=True)
class TrackData:
    """Mutable state for one continuously observed hand.

    Position and gesture histories are bounded, allowing downstream consumers to
    inspect motion without retaining every frame of a long-running application.
    """

    track_id: int
    created_at: float
    last_seen_at: float
    handedness: Handedness
    wrist: Point3D
    velocity: Point3D = field(default_factory=lambda: Point3D(0.0, 0.0, 0.0))
    missed_frames: int = 0
    prediction: Optional[GesturePrediction] = None
    smoothed_gesture: Optional[SmoothedGesture] = None
    history: Deque[TrackSample] = field(default_factory=lambda: deque(maxlen=32))

    def __post_init__(self) -> None:
        if self.track_id < 1:
            raise ValueError("Track identifiers start at 1.")
        if self.last_seen_at < self.created_at:
            raise ValueError("A track cannot be seen before it is created.")
        if not self.history:
            self.history.append(TrackSample(self.last_seen_at, self.wrist))

    @property
    def age_seconds(self) -> float:
        """Duration between track creation and its most recent observation."""
        return self.last_seen_at - self.created_at

    def update_position(self, wrist: Point3D, timestamp: float) -> None:
        """Update position and estimate velocity from the previous observation."""
        if timestamp < self.last_seen_at:
            raise ValueError("Track timestamps must not move backwards.")
        elapsed = timestamp - self.last_seen_at
        if elapsed > 0.0:
            self.velocity = (wrist - self.wrist).scaled(1.0 / elapsed)
        self.wrist = wrist
        self.last_seen_at = timestamp
        self.missed_frames = 0

    def add_gesture(
        self,
        prediction: GesturePrediction,
        smoothed: SmoothedGesture,
    ) -> None:
        """Store the current decisions and append a bounded history sample."""
        self.prediction = prediction
        self.smoothed_gesture = smoothed
        self.history.append(TrackSample(prediction.timestamp, self.wrist, smoothed.gesture))


@dataclass(frozen=True, slots=True)
class RecognizedHand:
    """The complete recognition result for one tracked hand in a frame."""

    track_id: int
    landmarks: ProcessedLandmarks
    prediction: GesturePrediction
    smoothed_gesture: SmoothedGesture
    velocity: Point3D
    track_age_seconds: float


@dataclass(frozen=True, slots=True)
class RecognitionFrame:
    """Results and active track identifiers returned by the controller."""

    timestamp: float
    hands: Tuple[RecognizedHand, ...]
    active_track_ids: Tuple[int, ...]
