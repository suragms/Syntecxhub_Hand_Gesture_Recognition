"""Explainable, dependency-free geometric hand gesture classification."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, isfinite
from typing import Dict, Iterable, Mapping, Tuple

from .landmark_processor import (
    INDEX_DIP,
    INDEX_MCP,
    INDEX_PIP,
    INDEX_TIP,
    MIDDLE_DIP,
    MIDDLE_MCP,
    MIDDLE_PIP,
    MIDDLE_TIP,
    PINKY_DIP,
    PINKY_MCP,
    PINKY_PIP,
    PINKY_TIP,
    RING_DIP,
    RING_MCP,
    RING_PIP,
    RING_TIP,
    THUMB_CMC,
    THUMB_IP,
    THUMB_MCP,
    THUMB_TIP,
)
from .models import Finger, FingerState, Gesture, GesturePrediction, Point3D, ProcessedLandmarks


@dataclass(frozen=True, slots=True)
class ClassifierConfig:
    """Tunable, scale-normalised thresholds for :class:`GestureClassifier`."""

    finger_extended_angle_degrees: float = 150.0
    finger_extended_ratio: float = 1.55
    thumb_extended_angle_degrees: float = 145.0
    pinch_distance: float = 0.45
    upright_dot_threshold: float = 0.28
    minimum_confidence: float = 0.70

    def __post_init__(self) -> None:
        if not 0.0 < self.finger_extended_angle_degrees < 180.0:
            raise ValueError("finger_extended_angle_degrees must be within (0, 180).")
        if not 0.0 < self.thumb_extended_angle_degrees < 180.0:
            raise ValueError("thumb_extended_angle_degrees must be within (0, 180).")
        if self.finger_extended_ratio <= 1.0:
            raise ValueError("finger_extended_ratio must be greater than one.")
        if self.pinch_distance <= 0.0:
            raise ValueError("pinch_distance must be positive.")
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be in [0, 1].")


class GestureClassifier:
    """Classify a small core vocabulary from normalised hand geometry.

    Classification is deterministic and exposes each finger measurement in the
    result, keeping decisions inspectable and easy to calibrate.  It identifies
    open palms, fists, pointing, peace, thumbs up/down, and a thumb-index pinch.
    Inputs are expected to come from :class:`LandmarkProcessor` so distances are
    expressed in palm-size units.
    """

    _FINGER_INDICES: Mapping[Finger, Tuple[int, int, int, int]] = {
        Finger.INDEX: (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
        Finger.MIDDLE: (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
        Finger.RING: (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
        Finger.PINKY: (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
    }

    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig()

    def classify(self, landmarks: ProcessedLandmarks) -> GesturePrediction:
        """Return a raw gesture decision for one processed hand."""
        points = landmarks.normalized
        states = self._finger_states(points)
        extended = {state.finger: state.extended for state in states}
        detector_confidence = landmarks.detector_confidence

        if detector_confidence < self.config.minimum_confidence:
            return self._prediction(
                Gesture.UNKNOWN,
                detector_confidence,
                landmarks.timestamp,
                states,
                "Observation confidence is below the classifier threshold.",
            )

        def accept(
            gesture: Gesture,
            evidence: float,
            reason: str,
        ) -> GesturePrediction:
            confidence = self._bounded_confidence(detector_confidence * evidence)
            if confidence < self.config.minimum_confidence:
                return self._prediction(
                    Gesture.UNKNOWN,
                    confidence,
                    landmarks.timestamp,
                    states,
                    f"{reason} Geometric evidence is below the classifier threshold.",
                )
            return self._prediction(gesture, confidence, landmarks.timestamp, states, reason)

        non_thumb = (Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY)
        extended_count = sum(extended[finger] for finger in non_thumb)
        thumb_extended = extended[Finger.THUMB]

        # A pinch must include an extended index finger.  Without that guard, a
        # naturally compact fist can place its folded thumb and index tips close
        # together and be falsely classified as a pinch.
        pinch_distance = points[THUMB_TIP].distance_to(points[INDEX_TIP])
        if extended[Finger.INDEX] and pinch_distance <= self.config.pinch_distance:
            pinch_strength = 1.0 - pinch_distance / self.config.pinch_distance
            return accept(
                Gesture.PINCH,
                0.65 + 0.35 * pinch_strength,
                "Thumb and extended index tips are close in palm-normalised space.",
            )

        if extended_count == 4 and thumb_extended:
            return accept(Gesture.OPEN_PALM, 1.0, "All fingers are extended.")
        if extended_count == 0 and not thumb_extended:
            compactness = self._mean_tip_distance_to_wrist(points)
            return accept(
                Gesture.FIST,
                self._bounded_confidence(1.45 - compactness),
                "All fingers are curled toward the palm.",
            )
        if extended[Finger.INDEX] and extended_count == 1 and not thumb_extended:
            return accept(Gesture.POINTING, 1.0, "Only the index finger is extended.")
        if extended[Finger.INDEX] and extended[Finger.MIDDLE] and extended_count == 2 and not thumb_extended:
            return accept(Gesture.PEACE, 1.0, "Index and middle fingers are extended.")

        if thumb_extended and extended_count == 0:
            orientation = self._thumb_vertical_orientation(points)
            if orientation >= self.config.upright_dot_threshold:
                return accept(
                    Gesture.THUMBS_UP,
                    self._orientation_confidence(orientation),
                    "Thumb points upward relative to the wrist.",
                )
            if orientation <= -self.config.upright_dot_threshold:
                return accept(
                    Gesture.THUMBS_DOWN,
                    self._orientation_confidence(-orientation),
                    "Thumb points downward relative to the wrist.",
                )

        return self._prediction(
            Gesture.UNKNOWN,
            detector_confidence * 0.5,
            landmarks.timestamp,
            states,
            "Finger configuration does not match a core gesture.",
        )

    def _finger_states(self, points: Tuple[Point3D, ...]) -> Tuple[FingerState, ...]:
        states = [self._thumb_state(points)]
        for finger, (mcp, pip, dip, tip) in self._FINGER_INDICES.items():
            angle = self._joint_angle(points[pip], points[dip], points[tip])
            extension_ratio = points[mcp].distance_to(points[tip]) / max(
                points[mcp].distance_to(points[pip]), 1e-9
            )
            extended = (
                angle >= self.config.finger_extended_angle_degrees
                and extension_ratio >= self.config.finger_extended_ratio
            )
            states.append(FingerState(finger, extended, angle, extension_ratio))
        return tuple(states)

    def _thumb_state(self, points: Tuple[Point3D, ...]) -> FingerState:
        angle = self._joint_angle(points[THUMB_MCP], points[THUMB_IP], points[THUMB_TIP])
        extension_ratio = points[THUMB_CMC].distance_to(points[THUMB_TIP]) / max(
            points[THUMB_CMC].distance_to(points[THUMB_MCP]), 1e-9
        )
        extended = (
            angle >= self.config.thumb_extended_angle_degrees
            and extension_ratio >= self.config.finger_extended_ratio
        )
        return FingerState(Finger.THUMB, extended, angle, extension_ratio)

    @staticmethod
    def _joint_angle(base: Point3D, joint: Point3D, tip: Point3D) -> float:
        """Return the included angle at *joint* in degrees, safely handling zero vectors."""
        first = base - joint
        second = tip - joint
        first_length = first.distance_to(Point3D(0.0, 0.0, 0.0))
        second_length = second.distance_to(Point3D(0.0, 0.0, 0.0))
        if first_length <= 1e-9 or second_length <= 1e-9:
            return 0.0
        cosine = (
            first.x * second.x + first.y * second.y + first.z * second.z
        ) / (first_length * second_length)
        return degrees(acos(max(-1.0, min(1.0, cosine))))

    @staticmethod
    def _mean_tip_distance_to_wrist(points: Tuple[Point3D, ...]) -> float:
        tip_indices = (THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)
        return sum(points[0].distance_to(points[index]) for index in tip_indices) / len(tip_indices)

    @staticmethod
    def _thumb_vertical_orientation(points: Tuple[Point3D, ...]) -> float:
        """Positive means up in image coordinates (where smaller y is higher)."""
        thumb = points[THUMB_TIP] - points[THUMB_CMC]
        length = thumb.distance_to(Point3D(0.0, 0.0, 0.0))
        return -thumb.y / length if length > 1e-9 else 0.0

    def _prediction(
        self,
        gesture: Gesture,
        confidence: float,
        timestamp: float,
        states: Tuple[FingerState, ...],
        reason: str,
    ) -> GesturePrediction:
        return GesturePrediction(
            gesture=gesture,
            confidence=self._bounded_confidence(confidence),
            timestamp=timestamp,
            finger_states=states,
            reason=reason,
        )

    @staticmethod
    def _bounded_confidence(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _orientation_confidence(self, magnitude: float) -> float:
        threshold = self.config.upright_dot_threshold
        return self._bounded_confidence((magnitude - threshold) / max(1.0 - threshold, 1e-9)) * 0.35 + 0.65
