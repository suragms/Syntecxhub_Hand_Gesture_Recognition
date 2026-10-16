from __future__ import annotations

from core.gesture_controller import ControllerConfig, GestureController
from core.models import HandObservation
from tests.fixtures import open_palm_points


def observation(timestamp: float) -> HandObservation:
    return HandObservation(open_palm_points(), timestamp=timestamp)


def test_track_expiry_uses_elapsed_time_not_empty_frame_count() -> None:
    controller = GestureController(
        config=ControllerConfig(hand_lost_reset_seconds=0.5)
    )
    initial = controller.process_frame((observation(0.0),), timestamp=0.0)
    assert initial.hands[0].track_id == 1

    controller.process_frame((), timestamp=0.1)
    controller.process_frame((), timestamp=0.2)
    assert controller.tracks()

    controller.process_frame((), timestamp=0.5)
    assert controller.tracks() == ()


def test_returning_hand_after_timeout_receives_new_track() -> None:
    controller = GestureController(
        config=ControllerConfig(hand_lost_reset_seconds=0.25)
    )
    assert controller.process_frame((observation(0.0),), timestamp=0.0).hands[0].track_id == 1
    controller.process_frame((), timestamp=0.3)
    returned = controller.process_frame((observation(0.31),), timestamp=0.31)
    assert returned.hands[0].track_id == 2
