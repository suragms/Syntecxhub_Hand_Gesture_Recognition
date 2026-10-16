from __future__ import annotations

from config import ActionConfig, AppConfig, RecognitionConfig
from core.engine import GestureEngine


def test_engine_wires_recognition_and_action_configuration() -> None:
    config = AppConfig(
        recognition=RecognitionConfig(
            heuristic_confidence_threshold=0.45,
            smoothing_window_seconds=0.8,
            minimum_hold_seconds=0.3,
            majority_ratio=0.75,
            hand_lost_reset_seconds=0.4,
            association_distance=0.2,
        ),
        actions=ActionConfig(
            play_pause_cooldown_seconds=1.8,
            volume_cooldown_seconds=0.4,
            rearm_seconds=0.2,
        ),
    )
    engine = GestureEngine(config)

    assert engine.controller.classifier.config.minimum_confidence == 0.45
    assert engine.controller.smoother.config.window_seconds == 0.8
    assert engine.controller.smoother.config.minimum_hold_seconds == 0.3
    assert engine.controller.smoother.config.minimum_stability == 0.75
    assert engine.controller.config.hand_lost_reset_seconds == 0.4
    assert engine.controller.config.max_match_distance == 0.2
    assert engine.actions.play_pause_cooldown == 1.8
    assert engine.actions.volume_cooldown == 0.4
    assert engine.actions.rearm_seconds == 0.2
