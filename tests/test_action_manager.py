from __future__ import annotations

from actions.action_registry import ActionRegistry
from actions.media_controller import SimulationMediaController
from actions.volume_controller import SimulationVolumeController
from core.action_manager import ActionManager
from core.models import Gesture


def test_disabled_actions_never_reach_the_controller() -> None:
    media = SimulationMediaController()
    manager = ActionManager(ActionRegistry(media_controller=media), enabled=False)
    event = manager.process_gesture(Gesture.THUMBS_UP)
    assert not event.executed
    assert media.history == []
    assert "disabled" in event.reason


def test_rearm_prevents_held_gesture_repetition() -> None:
    media = SimulationMediaController()
    now = [0.0]
    manager = ActionManager(ActionRegistry(media_controller=media), enabled=True, clock=lambda: now[0])
    first = manager.process_gesture(Gesture.THUMBS_UP)
    held = manager.process_gesture(Gesture.THUMBS_UP)
    manager.process_gesture(Gesture.FIST)
    now[0] = 2.0
    second = manager.process_gesture(Gesture.THUMBS_UP)
    assert first.executed and not held.executed and second.executed
    assert len(media.history) == 2


def test_volume_dispatch_is_simulated_and_bounded() -> None:
    volume = SimulationVolumeController(level=0.98)
    manager = ActionManager(ActionRegistry(volume_controller=volume, volume_step=0.05), enabled=True)
    event = manager.process_gesture(Gesture.OPEN_PALM)
    assert event.executed
    assert volume.level == 1.0


def test_rearm_preserves_action_cooldown() -> None:
    media = SimulationMediaController()
    now = [0.0]
    manager = ActionManager(ActionRegistry(media_controller=media), enabled=True, cooldown=1.0, clock=lambda: now[0])
    assert manager.process_gesture(Gesture.THUMBS_UP).executed
    manager.rearm()
    now[0] = 0.5
    assert not manager.process_gesture(Gesture.THUMBS_UP).executed
    now[0] = 1.1
    assert manager.process_gesture(Gesture.THUMBS_UP).executed


def test_independent_action_cooldowns_are_honored() -> None:
    media = SimulationMediaController()
    volume = SimulationVolumeController()
    now = [0.0]
    manager = ActionManager(
        ActionRegistry(media_controller=media, volume_controller=volume),
        enabled=True,
        play_pause_cooldown=2.0,
        volume_cooldown=0.5,
        clock=lambda: now[0],
    )
    assert manager.process_gesture(Gesture.THUMBS_UP).executed
    manager.rearm()
    assert manager.process_gesture(Gesture.OPEN_PALM).executed
    manager.rearm()
    now[0] = 0.75
    assert manager.process_gesture(Gesture.OPEN_PALM).executed
    manager.rearm()
    assert not manager.process_gesture(Gesture.THUMBS_UP).executed
