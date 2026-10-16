from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from config import DetectorConfig
from core.hand_detector import HandDetector


class FakeHands:
    HAND_CONNECTIONS = ()

    def __init__(self, **_kwargs) -> None:
        self.result = SimpleNamespace(
            multi_hand_landmarks=[
                SimpleNamespace(
                    landmark=[SimpleNamespace(x=index / 100, y=index / 100, z=0.0) for index in range(21)]
                )
            ],
            multi_handedness=[
                SimpleNamespace(classification=[SimpleNamespace(label="Right", score=0.31)])
            ],
        )

    def process(self, _frame):
        return self.result

    def close(self) -> None:
        pass


def test_handedness_score_is_metadata_not_observation_confidence() -> None:
    detector = HandDetector(DetectorConfig())
    fake_hands = FakeHands()
    detector._hands = fake_hands

    with patch("cv2.cvtColor", side_effect=lambda frame, _code: frame):
        frame = Mock()
        frame.size = 1
        frame.flags.writeable = True
        observations = detector.process(frame, timestamp=1.0)

    assert observations[0].confidence == 1.0
    assert observations[0].handedness_confidence == 0.31
