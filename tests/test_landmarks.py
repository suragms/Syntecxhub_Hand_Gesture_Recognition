from __future__ import annotations

import math

import pytest

from core.landmark_processor import LandmarkProcessor
from core.models import HandObservation, Handedness, Point3D
from tests.fixtures import open_palm_points


def test_processor_returns_twenty_one_normalized_landmarks() -> None:
    processed = LandmarkProcessor().from_landmarks(open_palm_points(), timestamp=1.0, handedness="left")
    assert len(processed.raw) == 21
    assert len(processed.normalized) == 21
    assert processed.handedness is Handedness.LEFT
    assert processed.palm_size > 0


def test_invalid_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="21"):
        HandObservation(tuple(open_palm_points()[:-1]), timestamp=1.0)


def test_non_finite_landmark_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        Point3D(math.nan, 0.0)


def test_degenerate_palm_is_rejected() -> None:
    points = tuple(Point3D(0.0, 0.0) for _ in range(21))
    with pytest.raises(ValueError, match="palm"):
        LandmarkProcessor().from_landmarks(points, timestamp=1.0)
