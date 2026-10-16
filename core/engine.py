"""Reusable, side-effect-managed real-time gesture processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any

from actions.action_registry import ActionRegistry
from actions.media_controller import PyAutoGUIMediaController
from actions.volume_controller import PycawVolumeController
from config import AppConfig
from core.action_manager import ActionEvent, ActionManager
from core.camera import Camera
from core.gesture_classifier import ClassifierConfig, GestureClassifier
from core.gesture_controller import ControllerConfig, GestureController
from core.gesture_smoother import GestureSmoother, SmootherConfig
from core.hand_detector import HandDetector
from core.models import Gesture, RecognitionFrame
from core.performance_monitor import PerformanceMonitor
from core.visualizer import Visualizer


@dataclass(frozen=True, slots=True)
class FrameResult:
    """One fresh camera image plus recognition/action state for presentation."""

    frame: Any
    recognition: RecognitionFrame
    action_event: ActionEvent | None
    fps: float


class GestureEngine:
    """Coordinate hardware adapters, pure recognition, safe actions, and overlays."""

    def __init__(self, config: AppConfig, *, action_backend: str | None = None) -> None:
        config.validate()
        self.config = config
        self.camera = Camera(config.camera)
        self.detector = HandDetector(config.detector)
        self.controller = self._build_controller()
        self.visualizer = Visualizer()
        self.actions = ActionManager.from_config(
            config.actions,
            registry=self._build_registry(action_backend or config.actions.backend),
        )
        self.performance_monitor = PerformanceMonitor()
        self.last_status = "Actions are disabled."
        self._no_hand_since: float | None = None
        self._absence_rearmed = False
        self._started = False

    def _build_controller(self) -> GestureController:
        """Translate validated application recognition settings to core components."""
        recognition = self.config.recognition
        return GestureController(
            classifier=GestureClassifier(
                ClassifierConfig(minimum_confidence=recognition.heuristic_confidence_threshold)
            ),
            smoother=GestureSmoother(
                SmootherConfig(
                    window_seconds=recognition.smoothing_window_seconds,
                    minimum_stability=recognition.majority_ratio,
                    minimum_hold_seconds=recognition.minimum_hold_seconds,
                )
            ),
            config=ControllerConfig(
                max_match_distance=recognition.association_distance,
                hand_lost_reset_seconds=recognition.hand_lost_reset_seconds,
            ),
        )

    def _build_registry(self, backend: str) -> ActionRegistry:
        if backend == "pyautogui":
            return ActionRegistry(
                self.config.actions.gesture_mappings,
                media_controller=PyAutoGUIMediaController(),
                volume_step=self.config.actions.volume_step,
            )
        if backend == "windows":
            return ActionRegistry(
                self.config.actions.gesture_mappings,
                media_controller=PyAutoGUIMediaController(),
                volume_controller=PycawVolumeController(),
                volume_step=self.config.actions.volume_step,
            )
        return ActionRegistry(
            self.config.actions.gesture_mappings,
            volume_step=self.config.actions.volume_step,
        )

    @property
    def actions_enabled(self) -> bool:
        return self.actions.enabled

    def start(self) -> None:
        """Initialize physical resources once before processing frames."""
        if self._started:
            return
        self.camera.open()
        try:
            self.detector.open()
        except Exception:
            self.camera.release()
            raise
        self._started = True
        self.last_status = "Camera started. Actions disabled." if not self.actions.enabled else "Camera started. Actions enabled."

    def toggle_actions(self) -> bool:
        """Toggle dispatch policy; live effects need explicit caller consent."""
        enabled = self.actions.set_enabled(not self.actions.enabled)
        self.last_status = "Gesture actions enabled." if enabled else "Gesture actions disabled."
        return enabled

    def reset(self) -> None:
        """Clear tracking, smoothing, cooldown, and rearming state."""
        self.controller.reset()
        self.actions.reset()
        self.performance_monitor.reset()
        self._no_hand_since = None
        self._absence_rearmed = False
        self.last_status = "Recognition and action state reset."

    def process_next_frame(self, *, annotate: bool = True) -> FrameResult:
        """Capture, recognize, and annotate one fresh frame.

        The returned FPS measures the previous completed capture-to-annotated-frame
        pipeline sample. Display/UI work owned by callers is intentionally excluded.
        """
        if not self._started:
            raise RuntimeError("Gesture engine has not been started.")
        previous_metrics = self.performance_monitor.snapshot()
        with self.performance_monitor.measure():
            frame = self.camera.read()
            if self.config.camera.mirror:
                import cv2

                frame = cv2.flip(frame, 1)
            timestamp = monotonic()
            observations = self.detector.process(frame, timestamp=timestamp)
            recognition = self.controller.process_frame(observations, timestamp=timestamp)
            self._update_hand_absence(recognition, timestamp)
            event = self._dispatch_primary_stable_gesture(recognition)
            if annotate:
                self._annotate(frame, recognition, previous_metrics.frames_per_second)
        metrics = self.performance_monitor.snapshot()
        return FrameResult(frame, recognition, event, metrics.frames_per_second)

    def _update_hand_absence(self, recognition: RecognitionFrame, timestamp: float) -> None:
        """Rearm once after a sustained no-hand period without clearing cooldowns."""
        if recognition.hands:
            self._no_hand_since = None
            self._absence_rearmed = False
            return
        if self._no_hand_since is None:
            self._no_hand_since = timestamp
            return
        if (
            not self._absence_rearmed
            and timestamp - self._no_hand_since >= self.config.recognition.hand_lost_reset_seconds
        ):
            self.actions.rearm()
            self._absence_rearmed = True
            self.last_status = "No hand detected; gesture actions rearmed."

    def _dispatch_primary_stable_gesture(self, recognition: RecognitionFrame) -> ActionEvent | None:
        stable = [
            item
            for item in recognition.hands
            if item.smoothed_gesture.stable
        ]
        if not stable:
            return None
        # Deterministic single-action-hand policy: oldest current track wins.
        active = min(stable, key=lambda item: (item.track_id, -item.track_age_seconds))
        event = self.actions.process_gesture(active.smoothed_gesture.gesture)
        self.last_status = event.result.message
        return event

    def _annotate(self, frame: Any, recognition: RecognitionFrame, fps: float) -> None:
        for hand in recognition.hands:
            self.visualizer.draw_hand(frame, hand, connections=self.detector.connections)
        warning = "No hand detected." if not recognition.hands else None
        self.visualizer.draw_status(
            frame,
            fps=fps,
            action_status=self.last_status,
            actions_enabled=self.actions.enabled,
            warning=warning,
        )
        self.visualizer.draw_controls(frame)

    def close(self) -> None:
        """Release all owned native resources safely and idempotently."""
        self.detector.close()
        self.camera.release()
        self._started = False

    def __enter__(self) -> "GestureEngine":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
