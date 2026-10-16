"""Registry and normalization utilities for gesture-triggered actions."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional, Protocol

from .media_controller import ActionResult, MediaCommand, MediaController, SimulationMediaController, coerce_media_command
from .volume_controller import SimulationVolumeController, VolumeController


class Action(str, Enum):
    """Actions the gesture subsystem can dispatch."""

    PLAY_PAUSE = "PLAY_PAUSE"
    NEXT_TRACK = "NEXT_TRACK"
    PREVIOUS_TRACK = "PREVIOUS_TRACK"
    STOP = "STOP"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    NONE = "NONE"


class GestureMappingConfig(Protocol):
    """Structural contract for configuration objects exposing gesture mappings."""

    gesture_mappings: Mapping[Any, Any]


DEFAULT_GESTURE_MAPPING: dict[str, Action] = {
    "THUMBS_UP": Action.PLAY_PAUSE,
    "OPEN_PALM": Action.VOLUME_UP,
    "FIST": Action.NONE,
}


class ActionRegistry:
    """Maps gesture labels to actions and dispatches them to controllers.

    Its default controllers are simulations, which intentionally never perform
    external system actions.  Install concrete optional backends explicitly to
    enable host media or volume control.
    """

    def __init__(
        self,
        gesture_mapping: Optional[Mapping[Any, Any]] = None,
        *,
        media_controller: Optional[MediaController] = None,
        volume_controller: Optional[VolumeController] = None,
        volume_step: float = 0.05,
    ) -> None:
        if volume_step <= 0:
            raise ValueError("volume_step must be positive.")
        self.media_controller = media_controller or SimulationMediaController()
        self.volume_controller = volume_controller or SimulationVolumeController()
        self.volume_step = float(volume_step)
        self._mapping: dict[str, Action] = {}
        # Supplying an explicit mapping replaces defaults; omitting it opts into
        # the built-in safe mapping contract.
        self.update_mapping(DEFAULT_GESTURE_MAPPING if gesture_mapping is None else gesture_mapping)

    @classmethod
    def from_config(
        cls,
        config: GestureMappingConfig,
        **kwargs: Any,
    ) -> "ActionRegistry":
        """Build a registry from an object exposing ``gesture_mappings``."""

        return cls(config.gesture_mappings, **kwargs)

    @property
    def mapping(self) -> dict[str, Action]:
        """Return a copy of the current normalized gesture-to-action mapping."""

        return dict(self._mapping)

    def update_mapping(self, mapping: Mapping[Any, Any]) -> None:
        for gesture, action in mapping.items():
            self.set_mapping(gesture, action)

    def set_mapping(self, gesture: Any, action: Any) -> None:
        self._mapping[normalize_gesture(gesture)] = coerce_action(action)

    def remove_mapping(self, gesture: Any) -> None:
        self._mapping.pop(normalize_gesture(gesture), None)

    def action_for(self, gesture: Any) -> Action:
        """Return the configured action, treating unrecognized gestures as neutral."""

        return self._mapping.get(normalize_gesture(gesture), Action.NONE)

    def dispatch_gesture(self, gesture: Any) -> ActionResult:
        return self.execute(self.action_for(gesture))

    # Alias useful for callers that use a generic registry interface.
    dispatch = dispatch_gesture

    def execute(self, action: Action | str) -> ActionResult:
        try:
            normalized = coerce_action(action)
        except (TypeError, ValueError) as exc:
            return ActionResult.failed(
                "Unsupported action.", backend="registry", command=str(action), error=str(exc)
            )

        if normalized is Action.NONE:
            return ActionResult.succeeded(
                "No action configured.", backend="registry", command=normalized.value
            )
        if normalized in _MEDIA_ACTIONS:
            return self.media_controller.execute(MediaCommand(normalized.value))
        if normalized is Action.VOLUME_UP:
            return self.volume_controller.increase(self.volume_step)
        if normalized is Action.VOLUME_DOWN:
            return self.volume_controller.decrease(self.volume_step)
        return ActionResult.failed(
            "Unsupported action.", backend="registry", command=normalized.value
        )


_MEDIA_ACTIONS = {
    Action.PLAY_PAUSE,
    Action.NEXT_TRACK,
    Action.PREVIOUS_TRACK,
    Action.STOP,
}


def normalize_gesture(gesture: Any) -> str:
    """Normalize strings and enum-like gesture models to a stable label."""

    value = getattr(gesture, "value", gesture)
    if value is None:
        return ""
    if not isinstance(value, str):
        value = getattr(gesture, "name", value)
    if not isinstance(value, str):
        return str(value).strip().upper()
    return value.strip().upper().replace("-", "_").replace(" ", "_")


def coerce_action(action: Action | str) -> Action:
    """Convert strings and compatible enum values to :class:`Action`."""

    if isinstance(action, Action):
        return action
    value = getattr(action, "value", action)
    if not isinstance(value, str):
        raise TypeError("An action must be a string or enum-like value.")
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return Action(normalized)
