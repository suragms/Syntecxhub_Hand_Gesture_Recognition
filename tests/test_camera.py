from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from config import CameraConfig
from core.camera import Camera, CameraError


class FakeCapture:
    def __init__(self, opened: bool, read_result=(True, object())) -> None:
        self.opened = opened
        self.read_result = read_result
        self.released = False

    def isOpened(self) -> bool:
        return self.opened

    def set(self, *_args) -> None:
        pass

    def read(self):
        return self.read_result

    def release(self) -> None:
        self.released = True


def test_unavailable_camera_raises_actionable_error() -> None:
    fake = FakeCapture(False)
    with patch("cv2.VideoCapture", return_value=fake):
        with pytest.raises(CameraError, match="Unable to access"):
            Camera(CameraConfig(backend="any")).open()
    assert fake.released


def test_empty_frame_raises_and_release_is_idempotent() -> None:
    fake = FakeCapture(True, (False, None))
    camera = Camera(CameraConfig(backend="any"))
    with patch("cv2.VideoCapture", return_value=fake):
        camera.open()
        with pytest.raises(CameraError, match="empty frame"):
            camera.read()
        camera.release()
        camera.release()
    assert fake.released
