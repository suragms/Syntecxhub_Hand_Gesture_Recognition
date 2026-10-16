from __future__ import annotations

from core.gesture_classifier import GestureClassifier
from core.landmark_processor import LandmarkProcessor
from core.models import Gesture
from tests.fixtures import fist_points, open_palm_points, thumbs_up_points


def classify(points, *, handedness: str = "right"):
    processed = LandmarkProcessor().from_landmarks(points, timestamp=1.0, handedness=handedness)
    return GestureClassifier().classify(processed)


def test_open_palm_is_recognized() -> None:
    assert classify(open_palm_points()).gesture is Gesture.OPEN_PALM


def test_fist_is_recognized() -> None:
    assert classify(fist_points()).gesture is Gesture.FIST


def test_thumbs_up_is_recognized() -> None:
    assert classify(thumbs_up_points()).gesture is Gesture.THUMBS_UP


def test_left_and_right_hands_use_same_geometry_rules() -> None:
    assert classify(open_palm_points(), handedness="left").gesture is Gesture.OPEN_PALM
    assert classify(open_palm_points(), handedness="right").gesture is Gesture.OPEN_PALM


def test_unknown_partial_pose_is_not_forced_into_mandatory_gesture() -> None:
    points = list(open_palm_points())
    points[8] = points[6]
    result = classify(tuple(points))
    assert result.gesture is Gesture.UNKNOWN
