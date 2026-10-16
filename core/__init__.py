"""Dependency-free core recognition data and pure processing logic.

This package intentionally excludes camera capture, detector SDK bindings,
visualisation, actions, UI, configuration loading, and application scripts.
"""

from .gesture_classifier import ClassifierConfig, GestureClassifier
from .gesture_controller import ControllerConfig, GestureController
from .gesture_smoother import GestureSmoother, SmootherConfig
from .landmark_processor import LandmarkProcessor
from .models import (
    Finger,
    FingerState,
    Gesture,
    GesturePrediction,
    HandObservation,
    Handedness,
    Point3D,
    ProcessedLandmarks,
    RecognitionFrame,
    RecognizedHand,
    SmoothedGesture,
    TrackData,
    TrackSample,
)
from .performance_monitor import PerformanceMonitor, PerformanceSnapshot

__all__ = (
    "ClassifierConfig",
    "ControllerConfig",
    "Finger",
    "FingerState",
    "Gesture",
    "GestureClassifier",
    "GestureController",
    "GesturePrediction",
    "GestureSmoother",
    "HandObservation",
    "Handedness",
    "LandmarkProcessor",
    "PerformanceMonitor",
    "PerformanceSnapshot",
    "Point3D",
    "ProcessedLandmarks",
    "RecognitionFrame",
    "RecognizedHand",
    "SmoothedGesture",
    "SmootherConfig",
    "TrackData",
    "TrackSample",
)
