from __future__ import annotations

from core.gesture_smoother import GestureSmoother, SmootherConfig
from core.models import Gesture, GesturePrediction


def prediction(gesture: Gesture, timestamp: float) -> GesturePrediction:
    return GesturePrediction(gesture, 1.0, timestamp)


def test_consecutive_gesture_becomes_stable_using_elapsed_time() -> None:
    smoother = GestureSmoother(SmootherConfig(window_seconds=1.0, minimum_samples=3, minimum_stability=0.7))
    assert not smoother.update(1, prediction(Gesture.OPEN_PALM, 0.0)).stable
    assert not smoother.update(1, prediction(Gesture.OPEN_PALM, 0.12)).stable
    result = smoother.update(1, prediction(Gesture.OPEN_PALM, 0.31))
    assert result.stable
    assert result.gesture is Gesture.OPEN_PALM


def test_unknown_frame_does_not_immediately_remove_stability() -> None:
    smoother = GestureSmoother(SmootherConfig(window_seconds=1.0, minimum_samples=3, minimum_stability=0.6))
    for time in (0.0, 0.1, 0.2):
        smoother.update(1, prediction(Gesture.OPEN_PALM, time))
    result = smoother.update(1, prediction(Gesture.UNKNOWN, 0.25))
    assert result.gesture is Gesture.OPEN_PALM
    assert result.stable


def test_forget_removes_history() -> None:
    smoother = GestureSmoother()
    smoother.update(1, prediction(Gesture.FIST, 0.0))
    smoother.forget(1)
    assert smoother.current(1, timestamp=1.0) is None
