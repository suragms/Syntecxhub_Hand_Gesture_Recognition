"""Central, validated configuration for the gesture-recognition application.

All operational defaults live here so camera, recognition, and action policy can be
adjusted without scattering magic values through the application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


DEFAULT_GESTURE_ACTIONS: Final[dict[str, str]] = {
    "THUMBS_UP": "PLAY_PAUSE",
    "OPEN_PALM": "VOLUME_UP",
}


@dataclass(frozen=True, slots=True)
class CameraConfig:
    """OpenCV camera settings."""

    index: int = 0
    width: int = 640
    height: int = 480
    target_fps: int = 30
    mirror: bool = True
    backend: str = "auto"

    def validate(self) -> None:
        if self.index < 0:
            raise ValueError("Camera index must be zero or greater.")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Camera width and height must be positive.")
        if self.target_fps <= 0:
            raise ValueError("Target FPS must be positive.")
        if self.backend not in {"auto", "dshow", "msmf", "any"}:
            raise ValueError("Camera backend must be auto, dshow, msmf, or any.")


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    """MediaPipe Hands settings."""

    max_hands: int = 2
    min_detection_confidence: float = 0.65
    min_tracking_confidence: float = 0.65
    model_complexity: int = 1

    def validate(self) -> None:
        if not 1 <= self.max_hands <= 2:
            raise ValueError("Maximum hands must be between 1 and 2.")
        for value, name in (
            (self.min_detection_confidence, "minimum detection confidence"),
            (self.min_tracking_confidence, "minimum tracking confidence"),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name.title()} must be between 0 and 1.")
        if self.model_complexity not in {0, 1}:
            raise ValueError("MediaPipe model complexity must be 0 or 1.")


@dataclass(frozen=True, slots=True)
class RecognitionConfig:
    """Gesture geometry and temporal-stability thresholds."""

    heuristic_confidence_threshold: float = 0.70
    smoothing_window_seconds: float = 0.55
    minimum_hold_seconds: float = 0.25
    majority_ratio: float = 0.70
    hand_lost_reset_seconds: float = 0.35
    association_distance: float = 0.24

    def validate(self) -> None:
        for value, name in (
            (self.heuristic_confidence_threshold, "heuristic confidence threshold"),
            (self.majority_ratio, "majority ratio"),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name.title()} must be between 0 and 1.")
        if self.smoothing_window_seconds <= 0:
            raise ValueError("Smoothing window must be positive.")
        if self.minimum_hold_seconds <= 0:
            raise ValueError("Minimum gesture hold duration must be positive.")
        if self.minimum_hold_seconds > self.smoothing_window_seconds:
            raise ValueError("Minimum hold duration cannot exceed smoothing window.")
        if self.hand_lost_reset_seconds <= 0:
            raise ValueError("Hand lost reset duration must be positive.")
        if self.association_distance <= 0:
            raise ValueError("Hand association distance must be positive.")


@dataclass(frozen=True, slots=True)
class ActionConfig:
    """Safety policy for mapping stable gestures to operating-system actions."""

    enabled_by_default: bool = False
    backend: str = "simulation"
    play_pause_cooldown_seconds: float = 1.2
    volume_cooldown_seconds: float = 0.7
    rearm_seconds: float = 0.35
    volume_step: float = 0.05
    gesture_mappings: dict[str, str] = field(
        default_factory=lambda: DEFAULT_GESTURE_ACTIONS.copy()
    )

    def validate(self) -> None:
        if self.backend not in {"simulation", "pyautogui", "windows"}:
            raise ValueError("Action backend must be simulation, pyautogui, or windows.")
        if self.play_pause_cooldown_seconds < 0 or self.volume_cooldown_seconds < 0:
            raise ValueError("Action cooldowns cannot be negative.")
        if self.rearm_seconds < 0:
            raise ValueError("Action rearm duration cannot be negative.")
        if not 0 < self.volume_step <= 0.25:
            raise ValueError("Volume step must be greater than 0 and no more than 0.25.")
        for gesture, action in self.gesture_mappings.items():
            if not isinstance(gesture, str) or not isinstance(action, str):
                raise ValueError("Gesture mappings must contain text gesture and action names.")


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Complete application configuration."""

    camera: CameraConfig = field(default_factory=CameraConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    actions: ActionConfig = field(default_factory=ActionConfig)
    debug: bool = False

    def validate(self) -> None:
        self.camera.validate()
        self.detector.validate()
        self.recognition.validate()
        self.actions.validate()


DEFAULT_CONFIG: Final[AppConfig] = AppConfig()
DEFAULT_CONFIG.validate()
