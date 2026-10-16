"""Safe and optional system volume-control backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .media_controller import ActionResult


class VolumeController(ABC):
    """Interface for relative master-volume changes."""

    backend_name = "volume"

    @abstractmethod
    def change(self, delta: float) -> ActionResult:
        """Change master volume by a normalized relative amount."""

    def increase(self, step: float = 0.05) -> ActionResult:
        return self.change(abs(float(step)))

    def decrease(self, step: float = 0.05) -> ActionResult:
        return self.change(-abs(float(step)))


@dataclass
class SimulationVolumeController(VolumeController):
    """Safe default backend storing an in-memory normalized volume level."""

    level: float = 0.5
    backend_name: str = "simulation"
    history: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.level = _clamp(self.level)

    def change(self, delta: float) -> ActionResult:
        try:
            amount = float(delta)
        except (TypeError, ValueError) as exc:
            return ActionResult.failed(
                "Volume delta must be numeric.", backend=self.backend_name, error=str(exc)
            )
        if amount != amount:  # NaN
            return ActionResult.failed("Volume delta must be finite.", backend=self.backend_name)
        previous = self.level
        self.level = _clamp(self.level + amount)
        applied = self.level - previous
        self.history.append(applied)
        return ActionResult.succeeded(
            f"Simulated volume level {self.level:.2f}.",
            backend=self.backend_name,
            command="VOLUME_UP" if applied > 0 else "VOLUME_DOWN" if applied < 0 else "VOLUME_UNCHANGED",
        )


class PycawVolumeController(VolumeController):
    """Windows master-volume backend using optional :mod:`pycaw` imports."""

    backend_name = "pycaw"

    def __init__(self) -> None:
        self._endpoint: Any | None = None
        self._load_error: Exception | None = None

    def _load_endpoint(self) -> Any | None:
        if self._endpoint is not None:
            return self._endpoint
        if self._load_error is not None:
            return None
        try:
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL  # type: ignore[import-not-found]
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore[import-not-found]

            device = AudioUtilities.GetSpeakers()
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._endpoint = cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as exc:  # includes non-Windows and unavailable audio APIs
            self._load_error = exc
            return None
        return self._endpoint

    def change(self, delta: float) -> ActionResult:
        try:
            amount = float(delta)
        except (TypeError, ValueError) as exc:
            return ActionResult.failed(
                "Volume delta must be numeric.", backend=self.backend_name, error=str(exc)
            )
        if amount != amount:
            return ActionResult.failed("Volume delta must be finite.", backend=self.backend_name)

        endpoint = self._load_endpoint()
        command = "VOLUME_UP" if amount > 0 else "VOLUME_DOWN" if amount < 0 else "VOLUME_UNCHANGED"
        if endpoint is None:
            return ActionResult.failed(
                "Pycaw volume backend is unavailable.",
                backend=self.backend_name,
                command=command,
                error=str(self._load_error),
            )

        try:
            current = float(endpoint.GetMasterVolumeLevelScalar())
            target = _clamp(current + amount)
            endpoint.SetMasterVolumeLevelScalar(target, None)
        except Exception as exc:
            return ActionResult.failed(
                "Failed to change system volume.",
                backend=self.backend_name,
                command=command,
                error=str(exc),
            )
        return ActionResult.succeeded(
            f"Set system volume to {target:.2f}.",
            backend=self.backend_name,
            command=command,
        )


# Alternate spelling that matches the package commonly known as "pycaw".
PyCAWVolumeController = PycawVolumeController
SystemVolumeController = PycawVolumeController


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
