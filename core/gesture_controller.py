"""Orchestration and lightweight hand-track management for core recognition."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Dict, Iterable, List, Sequence, Tuple

from .gesture_classifier import GestureClassifier
from .gesture_smoother import GestureSmoother
from .landmark_processor import LandmarkProcessor
from .models import (
    HandObservation,
    Handedness,
    ProcessedLandmarks,
    RecognitionFrame,
    RecognizedHand,
    TrackData,
)


@dataclass(frozen=True, slots=True)
class ControllerConfig:
    """Track association and expiry settings for :class:`GestureController`.

    ``max_match_distance`` is measured in the raw coordinate system supplied by
    the detector. For the usual image-normalised coordinate convention, 0.15
    is a conservative per-frame wrist displacement threshold. Track expiry is
    elapsed-time based so it is consistent across different camera frame rates.
    """

    max_match_distance: float = 0.15
    hand_lost_reset_seconds: float = 0.35
    match_handedness: bool = True

    def __post_init__(self) -> None:
        if not isfinite(self.max_match_distance) or self.max_match_distance <= 0.0:
            raise ValueError("max_match_distance must be a positive finite number.")
        if not isfinite(self.hand_lost_reset_seconds) or self.hand_lost_reset_seconds <= 0.0:
            raise ValueError("hand_lost_reset_seconds must be a positive finite number.")


class GestureController:
    """Run the pure recognition pipeline and maintain bounded per-hand tracks.

    The controller accepts detector-neutral :class:`HandObservation` values and
    returns recognition data only.  It does not open cameras, invoke detectors,
    render output, or execute actions.  Calling integrations retain ownership of
    those side effects and merely adapt their detector output at this boundary.
    """

    def __init__(
        self,
        *,
        landmark_processor: LandmarkProcessor | None = None,
        classifier: GestureClassifier | None = None,
        smoother: GestureSmoother | None = None,
        config: ControllerConfig | None = None,
    ) -> None:
        self.landmark_processor = landmark_processor or LandmarkProcessor()
        self.classifier = classifier or GestureClassifier()
        self.smoother = smoother or GestureSmoother()
        self.config = config or ControllerConfig()
        self._tracks: Dict[int, TrackData] = {}
        self._next_track_id = 1
        self._last_frame_timestamp: float | None = None

    def process_frame(
        self,
        observations: Iterable[HandObservation],
        *,
        timestamp: float | None = None,
    ) -> RecognitionFrame:
        """Process one detector result set and update hand tracks.

        If ``timestamp`` is omitted, all non-empty observations must share one
        timestamp, which becomes the frame timestamp. Empty frames must provide
        an explicit timestamp so elapsed hand-loss behavior remains meaningful.
        Timestamps must advance monotonically across calls to avoid corrupting
        velocity and time-based smoothing.
        """
        source = tuple(observations)
        frame_timestamp = self._resolve_timestamp(source, timestamp)
        self._validate_frame_timestamp(frame_timestamp)

        self._expire_tracks(frame_timestamp)
        processed = tuple(self.landmark_processor.process(item) for item in source)
        assignments = self._assign_tracks(processed)

        recognized: List[RecognizedHand] = []
        for observation_index, landmarks in enumerate(processed):
            track_id = assignments[observation_index]
            track = self._tracks[track_id]
            track.update_position(landmarks.wrist, frame_timestamp)
            track.handedness = landmarks.handedness
            prediction = self.classifier.classify(landmarks)
            smoothed = self.smoother.update(track_id, prediction)
            track.add_gesture(prediction, smoothed)
            recognized.append(
                RecognizedHand(
                    track_id=track_id,
                    landmarks=landmarks,
                    prediction=prediction,
                    smoothed_gesture=smoothed,
                    velocity=track.velocity,
                    track_age_seconds=track.age_seconds,
                )
            )

        self._last_frame_timestamp = frame_timestamp
        return RecognitionFrame(
            timestamp=frame_timestamp,
            hands=tuple(recognized),
            active_track_ids=tuple(sorted(self._tracks)),
        )

    def tracks(self) -> Tuple[TrackData, ...]:
        """Return active track objects ordered by identifier.

        The returned objects are live mutable track state.  Integrations that
        need a snapshot should copy individual values rather than mutate them.
        """
        return tuple(self._tracks[track_id] for track_id in sorted(self._tracks))

    def reset(self) -> None:
        """Remove all tracks and temporal history, preserving component setup."""
        self._tracks.clear()
        self._next_track_id = 1
        self._last_frame_timestamp = None
        self.smoother.clear()

    def _resolve_timestamp(
        self,
        observations: Sequence[HandObservation],
        supplied: float | None,
    ) -> float:
        if supplied is not None:
            if not isfinite(supplied):
                raise ValueError("Frame timestamp must be finite.")
            if any(item.timestamp != supplied for item in observations):
                raise ValueError("Observation timestamps must match the supplied frame timestamp.")
            return supplied
        if not observations:
            if self._last_frame_timestamp is None:
                raise ValueError("An empty first frame requires an explicit timestamp.")
            raise ValueError("An empty frame requires an explicit advancing timestamp.")
        timestamp = observations[0].timestamp
        if any(item.timestamp != timestamp for item in observations[1:]):
            raise ValueError("All observations in a frame must have the same timestamp.")
        return timestamp

    def _validate_frame_timestamp(self, timestamp: float) -> None:
        if self._last_frame_timestamp is not None and timestamp < self._last_frame_timestamp:
            raise ValueError("Frame timestamps must not move backwards.")

    def _assign_tracks(self, hands: Sequence[ProcessedLandmarks]) -> Dict[int, int]:
        """Greedily match closest compatible wrists before creating tracks.

        Pairwise distances are sorted globally, rather than assigning each hand
        independently, so two detections cannot claim the same old track.
        """
        candidates: List[Tuple[float, int, int]] = []
        for hand_index, hand in enumerate(hands):
            for track_id, track in self._tracks.items():
                if not self._compatible_handedness(hand.handedness, track.handedness):
                    continue
                distance = hand.wrist.distance_to(track.wrist)
                if distance <= self.config.max_match_distance:
                    candidates.append((distance, hand_index, track_id))
        candidates.sort()

        assignments: Dict[int, int] = {}
        claimed_tracks: set[int] = set()
        for _, hand_index, track_id in candidates:
            if hand_index not in assignments and track_id not in claimed_tracks:
                assignments[hand_index] = track_id
                claimed_tracks.add(track_id)

        for hand_index, hand in enumerate(hands):
            if hand_index not in assignments:
                assignments[hand_index] = self._create_track(hand)
        return assignments

    def _compatible_handedness(self, incoming: Handedness, existing: Handedness) -> bool:
        if not self.config.match_handedness:
            return True
        return (
            incoming is Handedness.UNKNOWN
            or existing is Handedness.UNKNOWN
            or incoming is existing
        )

    def _create_track(self, hand: ProcessedLandmarks) -> int:
        track_id = self._next_track_id
        self._next_track_id += 1
        self._tracks[track_id] = TrackData(
            track_id=track_id,
            created_at=hand.timestamp,
            last_seen_at=hand.timestamp,
            handedness=hand.handedness,
            wrist=hand.wrist,
        )
        return track_id

    def _expire_tracks(self, timestamp: float) -> None:
        """Remove hands absent longer than the configured wall-clock interval."""
        stale_ids = [
            track_id
            for track_id, track in self._tracks.items()
            if timestamp - track.last_seen_at >= self.config.hand_lost_reset_seconds
        ]
        for track_id in stale_ids:
            self._tracks.pop(track_id)
            self.smoother.forget(track_id)
