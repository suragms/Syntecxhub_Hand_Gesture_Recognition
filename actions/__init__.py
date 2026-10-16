"""Gesture action dispatch with safe simulation defaults."""

from .action_registry import (
    Action,
    ActionRegistry,
    DEFAULT_GESTURE_MAPPING,
    GestureMappingConfig,
    coerce_action,
    normalize_gesture,
)
from .media_controller import (
    ActionResult,
    MediaCommand,
    MediaController,
    PyAutoGUIMediaController,
    SimulationMediaController,
    SystemMediaController,
)
from .volume_controller import (
    PyCAWVolumeController,
    PycawVolumeController,
    SimulationVolumeController,
    SystemVolumeController,
    VolumeController,
)

__all__ = [
    "Action",
    "ActionRegistry",
    "ActionResult",
    "DEFAULT_GESTURE_MAPPING",
    "GestureMappingConfig",
    "MediaCommand",
    "MediaController",
    "PyAutoGUIMediaController",
    "PyCAWVolumeController",
    "PycawVolumeController",
    "SimulationMediaController",
    "SimulationVolumeController",
    "SystemMediaController",
    "SystemVolumeController",
    "VolumeController",
    "coerce_action",
    "normalize_gesture",
]
