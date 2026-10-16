"""Time-based temporal smoothing for per-hand gesture predictions."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import exp, isfinite
from typing import Deque, Dict, Iterable, Mapping

from .models import Gesture, GesturePrediction, SmoothedGesture


@dataclass(frozen=True, slots=True)
class SmootherConfig:
    """Configuration for exponentially time-decayed gesture voting."""

    window_seconds: float = 0.75
    half_life_seconds: float = 0.25
    minimum_samples: int = 3
    minimum_stability: float = 0.60
    include_unknown: bool = False

    def __post_init__(self) -> None:
        if not isfinite(self.window_seconds) or self.window_seconds <= 0.0:
            raise ValueError("window_seconds must be a positive finite number.")
        if not isfinite(self.half_life_seconds) or self.half_life_seconds <= 0.0:
            raise ValueError("half_life_seconds must be a positive finite number.")
        if self.minimum_samples < 1:
            raise ValueError("minimum_samples must be at least one.")
        if not 0.0 <= self.minimum_stability <= 1.0:
            raise ValueError("minimum_stability must be in [0, 1].")


class GestureSmoother:
    """Aggregate classifier decisions with elapsed-time rather than frame counts.

    A prediction's vote is its classifier confidence multiplied by an exponential
    time-decay weight.  The approach behaves consistently at different camera
    frame rates and remains stable through small frame timing variations.
    Histories are kept separately by caller-provided track ID.
    """

    def __init__(self, config: SmootherConfig | None = None) -> None:
        self.config = config or SmootherConfig()
        self._history: Dict[int, Deque[GesturePrediction]] = defaultdict(deque)

    def update(self, track_id: int, prediction: GesturePrediction) -> SmoothedGesture:
        """Add a prediction and return the current smoothed decision for its track.

        Timestamps for a track must be monotonic.  This rejects stale asynchronous
        data instead of silently over-weighting it as if it were newly observed.
        """
        if track_id < 1:
            raise ValueError("Track identifiers start at 1.")
        history = self._history[track_id]
        if history and prediction.timestamp < history[-1].timestamp:
            raise ValueError("Predictions for a track must be timestamp ordered.")
        history.append(prediction)
        self._prune(history, prediction.timestamp)
        return self._aggregate(history, prediction.timestamp)

    def current(self, track_id: int, *, timestamp: float) -> SmoothedGesture | None:
        """Return a time-decayed decision without adding a new observation."""
        if not isfinite(timestamp):
            raise ValueError("timestamp must be finite.")
        history = self._history.get(track_id)
        if not history:
            return None
        if timestamp < history[-1].timestamp:
            raise ValueError("Current timestamp cannot precede the latest prediction.")
        self._prune(history, timestamp)
        if not history:
            self._history.pop(track_id, None)
            return None
        return self._aggregate(history, timestamp)

    def forget(self, track_id: int) -> None:
        """Discard the temporal history belonging to one finished track."""
        self._history.pop(track_id, None)

    def clear(self) -> None:
        """Discard all tracked histories."""
        self._history.clear()

    def active_track_ids(self) -> tuple[int, ...]:
        """Return IDs that currently have smoothing history."""
        return tuple(self._history)

    def _prune(self, history: Deque[GesturePrediction], now: float) -> None:
        cutoff = now - self.config.window_seconds
        while history and history[0].timestamp < cutoff:
            history.popleft()

    def _aggregate(
        self,
        history: Deque[GesturePrediction],
        timestamp: float,
    ) -> SmoothedGesture:
        scores: Dict[Gesture, float] = defaultdict(float)
        total_weight = 0.0
        newest_confidence = 0.0
        considered = 0
        for prediction in history:
            if prediction.gesture is Gesture.UNKNOWN and not self.config.include_unknown:
                continue
            age = max(0.0, timestamp - prediction.timestamp)
            weight = exp(-0.6931471805599453 * age / self.config.half_life_seconds)
            weighted_confidence = prediction.confidence * weight
            scores[prediction.gesture] += weighted_confidence
            total_weight += weighted_confidence
            newest_confidence = prediction.confidence
            considered += 1

        if not scores or total_weight <= 0.0:
            return SmoothedGesture(
                gesture=Gesture.UNKNOWN,
                confidence=0.0,
                stability=0.0,
                stable=False,
                timestamp=timestamp,
                sample_count=considered,
            )

        gesture, winning_weight = max(scores.items(), key=lambda pair: pair[1])
        stability = winning_weight / total_weight
        # Confidence couples consensus with evidence strength, avoiding an
        # artificially perfect result when a single low-confidence vote exists.
        evidence = min(1.0, total_weight / max(1.0, self.config.minimum_samples * 0.5))
        confidence = stability * evidence
        stable = (
            considered >= self.config.minimum_samples
            and stability >= self.config.minimum_stability
            and gesture is not Gesture.UNKNOWN
        )
        return SmoothedGesture(
            gesture=gesture,
            confidence=confidence,
            stability=stability,
            stable=stable,
            timestamp=timestamp,
            sample_count=considered,
        )
