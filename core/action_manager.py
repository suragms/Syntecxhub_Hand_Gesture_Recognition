"""Stateful, rate-limited gesture action manager."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Optional, Protocol

from actions.action_registry import Action, ActionRegistry, GestureMappingConfig, coerce_action, normalize_gesture
from actions.media_controller import ActionResult


@dataclass(frozen=True)
class ActionEvent:
    """Outcome metadata for one gesture observation."""

    gesture: str
    action: Action
    result: ActionResult
    executed: bool
    reason: str = ""


class ActionManagerConfig(GestureMappingConfig, Protocol):
    """Structural contract accepted by :meth:`ActionManager.from_config`."""

    enabled_by_default: bool
    play_pause_cooldown_seconds: float
    volume_cooldown_seconds: float
    rearm_seconds: float
    volume_step: float


class ActionManager:
    """Turns recognized gestures into safe, debounced action dispatches.

    The manager begins disabled. While disabled it does not call the registry,
    guaranteeing that gesture processing cannot cause external actions.  Once
    enabled, a non-neutral action is eligible only after its gesture is rearmed:
    observe the configured neutral gesture (``FIST`` by default), then observe
    the intended gesture. A cooldown also guards each dispatched action. Use
    ``rearm_seconds`` when the neutral pose must remain stable before rearming.
    """

    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        *,
        enabled: bool = False,
        cooldown: float = 0.75,
        play_pause_cooldown: Optional[float] = None,
        volume_cooldown: Optional[float] = None,
        rearm_seconds: float = 0.0,
        neutral_gesture: Any = "FIST",
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if cooldown < 0:
            raise ValueError("cooldown must be non-negative.")
        if play_pause_cooldown is not None and play_pause_cooldown < 0:
            raise ValueError("play_pause_cooldown must be non-negative.")
        if volume_cooldown is not None and volume_cooldown < 0:
            raise ValueError("volume_cooldown must be non-negative.")
        if rearm_seconds < 0:
            raise ValueError("rearm_seconds must be non-negative.")
        self.registry = registry or ActionRegistry()
        self.cooldown = float(cooldown)
        self.play_pause_cooldown = (
            self.cooldown if play_pause_cooldown is None else float(play_pause_cooldown)
        )
        self.volume_cooldown = (
            self.cooldown if volume_cooldown is None else float(volume_cooldown)
        )
        self.rearm_seconds = float(rearm_seconds)
        self.neutral_gesture = normalize_gesture(neutral_gesture)
        self._clock = clock
        self._enabled = bool(enabled)
        self._armed = True
        self._last_action_at: dict[Action, float] = {}
        self._neutral_observed_at: Optional[float] = None

    @classmethod
    def from_config(
        cls,
        config: ActionManagerConfig,
        *,
        registry: Optional[ActionRegistry] = None,
        clock: Callable[[], float] = monotonic,
    ) -> "ActionManager":
        """Create a manager from the project's lightweight action config shape."""

        action_registry = registry or ActionRegistry(
            config.gesture_mappings,
            volume_step=config.volume_step,
        )
        return cls(
            action_registry,
            enabled=config.enabled_by_default,
            play_pause_cooldown=config.play_pause_cooldown_seconds,
            volume_cooldown=config.volume_cooldown_seconds,
            rearm_seconds=config.rearm_seconds,
            clock=clock,
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def armed(self) -> bool:
        return self._armed

    def set_enabled(self, enabled: bool) -> bool:
        """Set action dispatch state and reset the rearm gate when disabling."""

        self._enabled = bool(enabled)
        if not self._enabled:
            self._armed = True
            self._neutral_observed_at = None
        return self._enabled

    def enable(self) -> None:
        self.set_enabled(True)

    def disable(self) -> None:
        self.set_enabled(False)

    def reset(self) -> None:
        """Clear cooldown state and allow the next mapped action."""

        self._last_action_at.clear()
        self.rearm()

    def rearm(self) -> None:
        """Restore gesture eligibility without bypassing action cooldowns."""

        self._armed = True
        self._neutral_observed_at = None

    def process_gesture(self, gesture: Any) -> ActionEvent:
        """Process a gesture label or enum-like detection result.

        Expected non-exceptional conditions, such as disabled dispatch,
        cooldown, unrecognized gestures, and missing rearm are returned as
        successful no-op results rather than exceptions.
        """

        normalized_gesture = normalize_gesture(gesture)
        action = self.registry.action_for(gesture)

        if self._is_neutral(normalized_gesture, action):
            now = self._clock()
            if self._neutral_observed_at is None:
                self._neutral_observed_at = now
            if now - self._neutral_observed_at >= self.rearm_seconds:
                self._armed = True
                return self._no_op(normalized_gesture, action, "neutral gesture rearmed actions")
            return self._no_op(normalized_gesture, action, "waiting for neutral gesture rearm")

        # A continuous neutral gesture must be re-observed before another cycle.
        self._neutral_observed_at = None
        if action is Action.NONE:
            return self._no_op(normalized_gesture, action, "no action configured")

        if not self._enabled:
            return self._no_op(normalized_gesture, action, "actions are disabled")

        if not self._armed:
            return self._no_op(normalized_gesture, action, "awaiting neutral gesture to rearm")

        now = self._clock()
        last_dispatched = self._last_action_at.get(action)
        if last_dispatched is not None and now - last_dispatched < self._cooldown_for(action):
            return self._no_op(normalized_gesture, action, "action is cooling down")

        result = self.registry.execute(action)
        if result.success:
            self._last_action_at[action] = now
            self._armed = False
        return ActionEvent(normalized_gesture, action, result, result.success, "dispatched" if result.success else "dispatch failed")

    # Common aliases used by frame-processing loops and callback adapters.
    handle_gesture = process_gesture
    update = process_gesture

    def execute(self, action: Action | str) -> ActionResult:
        """Dispatch an explicit action only when action execution is enabled."""

        try:
            normalized = coerce_action(action)
        except (TypeError, ValueError) as exc:
            return ActionResult.failed("Unsupported action.", backend="manager", error=str(exc))
        if not self._enabled:
            return ActionResult.succeeded(
                "Actions are disabled; no external action was performed.",
                backend="manager",
                command=normalized.value,
            )
        return self.registry.execute(normalized)

    def _is_neutral(self, gesture: str, action: Action) -> bool:
        return gesture == self.neutral_gesture

    def _cooldown_for(self, action: Action) -> float:
        if action is Action.PLAY_PAUSE:
            return self.play_pause_cooldown
        if action in {Action.VOLUME_UP, Action.VOLUME_DOWN}:
            return self.volume_cooldown
        return self.cooldown

    @staticmethod
    def _no_op(gesture: str, action: Action, reason: str) -> ActionEvent:
        result = ActionResult.succeeded(reason, backend="manager", command=action.value)
        return ActionEvent(gesture, action, result, False, reason)
