"""Cross-platform media-control backends.

Optional operating-system integrations are imported only when selected, so the
package stays importable in a minimal Python environment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MediaCommand(str, Enum):
    """Commands understood by a media controller."""

    PLAY_PAUSE = "PLAY_PAUSE"
    NEXT_TRACK = "NEXT_TRACK"
    PREVIOUS_TRACK = "PREVIOUS_TRACK"
    STOP = "STOP"


@dataclass(frozen=True)
class ActionResult:
    """Result of attempting a side-effecting controller operation."""

    success: bool
    message: str = ""
    backend: str = ""
    command: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def succeeded(
        cls, message: str = "", *, backend: str = "", command: Optional[str] = None
    ) -> "ActionResult":
        return cls(True, message, backend, command)

    @classmethod
    def failed(
        cls,
        message: str,
        *,
        backend: str = "",
        command: Optional[str] = None,
        error: Optional[str] = None,
    ) -> "ActionResult":
        return cls(False, message, backend, command, error)


class MediaController(ABC):
    """Interface for dispatching media playback commands."""

    backend_name = "media"

    @abstractmethod
    def execute(self, command: MediaCommand | str) -> ActionResult:
        """Execute one media command without raising for expected failures."""

    def play_pause(self) -> ActionResult:
        return self.execute(MediaCommand.PLAY_PAUSE)

    def next_track(self) -> ActionResult:
        return self.execute(MediaCommand.NEXT_TRACK)

    def previous_track(self) -> ActionResult:
        return self.execute(MediaCommand.PREVIOUS_TRACK)

    def stop(self) -> ActionResult:
        return self.execute(MediaCommand.STOP)


@dataclass
class SimulationMediaController(MediaController):
    """Safe default backend that records commands without controlling the host."""

    backend_name: str = "simulation"
    history: list[MediaCommand] = field(default_factory=list)

    def execute(self, command: MediaCommand | str) -> ActionResult:
        try:
            normalized = coerce_media_command(command)
        except (TypeError, ValueError) as exc:
            return ActionResult.failed(
                "Unsupported media command.",
                backend=self.backend_name,
                command=str(command),
                error=str(exc),
            )
        self.history.append(normalized)
        return ActionResult.succeeded(
            f"Simulated {normalized.value}.",
            backend=self.backend_name,
            command=normalized.value,
        )


class PyAutoGUIMediaController(MediaController):
    """Media-key backend implemented through optional :mod:`pyautogui`."""

    backend_name = "pyautogui"
    _KEYS = {
        MediaCommand.PLAY_PAUSE: "playpause",
        MediaCommand.NEXT_TRACK: "nexttrack",
        MediaCommand.PREVIOUS_TRACK: "prevtrack",
        MediaCommand.STOP: "stop",
    }

    def __init__(self) -> None:
        self._pyautogui: Any | None = None
        self._load_error: Exception | None = None

    def _load(self) -> Any | None:
        if self._pyautogui is not None:
            return self._pyautogui
        if self._load_error is not None:
            return None
        try:
            import pyautogui  # type: ignore[import-not-found]
        except Exception as exc:  # import may fail in headless sessions too
            self._load_error = exc
            return None
        self._pyautogui = pyautogui
        return self._pyautogui

    def execute(self, command: MediaCommand | str) -> ActionResult:
        try:
            normalized = coerce_media_command(command)
        except (TypeError, ValueError) as exc:
            return ActionResult.failed(
                "Unsupported media command.",
                backend=self.backend_name,
                command=str(command),
                error=str(exc),
            )

        pyautogui = self._load()
        if pyautogui is None:
            return ActionResult.failed(
                "PyAutoGUI media backend is unavailable.",
                backend=self.backend_name,
                command=normalized.value,
                error=str(self._load_error),
            )

        try:
            pyautogui.press(self._KEYS[normalized])
        except Exception as exc:
            return ActionResult.failed(
                "Failed to send media key.",
                backend=self.backend_name,
                command=normalized.value,
                error=str(exc),
            )
        return ActionResult.succeeded(
            f"Sent {normalized.value} media key.",
            backend=self.backend_name,
            command=normalized.value,
        )


# A concise alias for callers that choose the optional real backend explicitly.
SystemMediaController = PyAutoGUIMediaController


def coerce_media_command(command: MediaCommand | str) -> MediaCommand:
    """Convert strings and compatible enum values to :class:`MediaCommand`."""

    if isinstance(command, MediaCommand):
        return command
    value = getattr(command, "value", command)
    if not isinstance(value, str):
        raise TypeError("A media command must be a string or enum-like value.")
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return MediaCommand(normalized)
