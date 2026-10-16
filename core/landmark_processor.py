"""Provider-independent validation and normalisation of hand landmarks."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import isfinite
from typing import Any, Optional, Tuple, Union

from .models import HandObservation, Handedness, Point3D, ProcessedLandmarks


# Landmark indices in the standard 21-point hand topology.
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


class LandmarkProcessor:
    """Convert detector-shaped landmarks into stable scale-normalised geometry.

    The processor accepts native :class:`HandObservation` values as well as
    common simple detector objects with ``x``, ``y`` and optional ``z``
    attributes.  Consequently it can be imported and tested without MediaPipe,
    OpenCV, NumPy, or any other optional runtime integration.

    Normalised coordinates are centred at the wrist and divided by a robust palm
    scale based on the wrist-to-middle-MCP and index-to-pinky-MCP distances.
    This makes rule thresholds substantially less sensitive to hand size and
    camera distance.
    """

    def __init__(self, *, minimum_palm_size: float = 1e-6) -> None:
        if not isfinite(minimum_palm_size) or minimum_palm_size <= 0.0:
            raise ValueError("minimum_palm_size must be a positive finite number.")
        self._minimum_palm_size = minimum_palm_size

    def process(self, observation: HandObservation) -> ProcessedLandmarks:
        """Validate and normalise a complete hand observation."""
        raw = observation.landmarks
        wrist = raw[WRIST]
        index_mcp = raw[INDEX_MCP]
        middle_mcp = raw[MIDDLE_MCP]
        pinky_mcp = raw[PINKY_MCP]

        # Averaging two independent palm dimensions makes the scale more robust
        # when one side of the hand is partially foreshortened.
        longitudinal = wrist.distance_to(middle_mcp)
        transverse = index_mcp.distance_to(pinky_mcp)
        palm_size = (longitudinal + transverse) / 2.0
        if palm_size < self._minimum_palm_size:
            raise ValueError("Landmarks do not describe a sufficiently sized palm.")

        palm_center = Point3D(
            (wrist.x + index_mcp.x + middle_mcp.x + pinky_mcp.x) / 4.0,
            (wrist.y + index_mcp.y + middle_mcp.y + pinky_mcp.y) / 4.0,
            (wrist.z + index_mcp.z + middle_mcp.z + pinky_mcp.z) / 4.0,
        )
        normalized = tuple((point - wrist).scaled(1.0 / palm_size) for point in raw)
        return ProcessedLandmarks(
            raw=raw,
            normalized=normalized,
            timestamp=observation.timestamp,
            handedness=observation.handedness,
            detector_confidence=observation.confidence,
            handedness_confidence=observation.handedness_confidence,
            palm_size=palm_size,
            palm_center=palm_center,
        )

    def from_landmarks(
        self,
        landmarks: Iterable[Any],
        *,
        timestamp: float,
        handedness: Union[Handedness, str, None] = None,
        confidence: float = 1.0,
    ) -> ProcessedLandmarks:
        """Adapt points/objects from a detector and process them.

        Each item may be a :class:`Point3D`, a three-item sequence, a two-item
        sequence (whose ``z`` becomes zero), or an object exposing ``x`` and
        ``y`` attributes plus an optional ``z``.  This method is deliberately a
        thin data adapter, not an import of a concrete detector package.
        """
        points = tuple(self._coerce_point(item) for item in landmarks)
        observation = HandObservation(
            landmarks=points,
            timestamp=timestamp,
            handedness=self._coerce_handedness(handedness),
            confidence=confidence,
        )
        return self.process(observation)

    @staticmethod
    def _coerce_handedness(value: Union[Handedness, str, None]) -> Handedness:
        if value is None:
            return Handedness.UNKNOWN
        if isinstance(value, Handedness):
            return value
        try:
            return Handedness(value.lower())
        except (AttributeError, ValueError) as error:
            raise ValueError(f"Unsupported handedness value: {value!r}") from error

    @staticmethod
    def _coerce_point(value: Any) -> Point3D:
        if isinstance(value, Point3D):
            return value
        if hasattr(value, "x") and hasattr(value, "y"):
            return Point3D(float(value.x), float(value.y), float(getattr(value, "z", 0.0)))
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) not in (2, 3):
                raise ValueError("Landmark sequences must contain two or three coordinates.")
            return Point3D(float(value[0]), float(value[1]), float(value[2]) if len(value) == 3 else 0.0)
        raise TypeError("Each landmark must be a Point3D, coordinate sequence, or x/y object.")
