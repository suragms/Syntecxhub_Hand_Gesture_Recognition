"""Reliable OpenCV webcam capture with Windows backend fallbacks."""

from __future__ import annotations

import logging
from typing import Any

from config import CameraConfig

LOGGER = logging.getLogger(__name__)


class CameraError(RuntimeError):
    """Raised when a camera cannot be initialized or used."""


class Camera:
    """Own an OpenCV capture device and guarantee resource cleanup."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self._capture: Any | None = None
        self.backend_name = "uninitialized"

    @property
    def is_open(self) -> bool:
        return bool(self._capture is not None and self._capture.isOpened())

    def open(self) -> None:
        """Open the configured camera, trying Windows-friendly backends in order."""
        if self.is_open:
            return
        try:
            import cv2
        except ImportError as error:  # pragma: no cover - environment dependent
            raise CameraError("OpenCV is not installed. Install requirements.txt first.") from error

        requested = self.config.backend
        backend_candidates: list[tuple[str, int | None]] = []
        backend_lookup = {
            "dshow": ("DirectShow", cv2.CAP_DSHOW),
            "msmf": ("Media Foundation", cv2.CAP_MSMF),
            "any": ("OpenCV default", cv2.CAP_ANY),
        }
        if requested == "auto":
            backend_candidates = [
                ("DirectShow", getattr(cv2, "CAP_DSHOW", None)),
                ("Media Foundation", getattr(cv2, "CAP_MSMF", None)),
                ("OpenCV default", getattr(cv2, "CAP_ANY", None)),
            ]
        else:
            backend_candidates = [backend_lookup[requested]]

        for name, backend in backend_candidates:
            if backend is None:
                continue
            capture = cv2.VideoCapture(self.config.index, backend)
            if capture.isOpened():
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
                capture.set(cv2.CAP_PROP_FPS, self.config.target_fps)
                self._capture = capture
                self.backend_name = name
                LOGGER.info(
                    "Opened camera %s using %s at requested %sx%s.",
                    self.config.index,
                    name,
                    self.config.width,
                    self.config.height,
                )
                return
            capture.release()
            LOGGER.debug("Camera %s was unavailable through %s.", self.config.index, name)

        raise CameraError(
            f"Unable to access webcam {self.config.index}. Check camera permissions, "
            "connections, and whether another application is using it."
        )

    def read(self) -> Any:
        """Return one fresh BGR frame or raise an actionable capture error."""
        if not self.is_open:
            raise CameraError("Camera is not open.")
        assert self._capture is not None
        success, frame = self._capture.read()
        if not success or frame is None or getattr(frame, "size", 0) == 0:
            raise CameraError(
                "Camera returned an empty frame. The webcam may have been disconnected "
                "or is no longer available."
            )
        return frame

    def release(self) -> None:
        """Release the underlying device. Safe to invoke repeatedly."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            LOGGER.info("Released camera resource.")

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
