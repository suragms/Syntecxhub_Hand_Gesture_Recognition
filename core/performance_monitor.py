"""Small dependency-free performance metrics collector for recognition loops."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite
from statistics import fmean
from time import perf_counter
from typing import Deque, Iterator


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """A read-only summary of recently measured processing durations."""

    samples: int
    average_latency_ms: float
    minimum_latency_ms: float
    maximum_latency_ms: float
    frames_per_second: float
    total_frames: int
    dropped_frames: int
    drop_rate: float


class _Measurement:
    """Context manager returned by :meth:`PerformanceMonitor.measure`."""

    def __init__(self, monitor: "PerformanceMonitor") -> None:
        self._monitor = monitor
        self._started_at: float | None = None

    def __enter__(self) -> "_Measurement":
        self._started_at = perf_counter()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        assert self._started_at is not None
        self._monitor.record_duration(perf_counter() - self._started_at)


class PerformanceMonitor:
    """Collect rolling latency/FPS metrics without coupling to a UI or camera.

    Use ``with monitor.measure():`` around one complete processing iteration or
    call :meth:`record_duration` when an external timing source is preferred.
    FPS is derived from the summed durations in the rolling sample window.
    """

    def __init__(self, *, window_size: int = 120) -> None:
        if window_size < 1:
            raise ValueError("window_size must be at least one.")
        self._durations: Deque[float] = deque(maxlen=window_size)
        self._total_frames = 0
        self._dropped_frames = 0

    def measure(self) -> _Measurement:
        """Return a context manager that records one elapsed duration."""
        return _Measurement(self)

    def record_duration(self, seconds: float) -> None:
        """Record a non-negative processing duration in seconds."""
        if not isfinite(seconds) or seconds < 0.0:
            raise ValueError("Duration must be a finite, non-negative number.")
        self._durations.append(seconds)
        self._total_frames += 1

    def record_drop(self, count: int = 1) -> None:
        """Record frames intentionally skipped or unavailable upstream."""
        if count < 1:
            raise ValueError("Drop count must be at least one.")
        self._dropped_frames += count

    def snapshot(self) -> PerformanceSnapshot:
        """Return rolling latency and throughput statistics."""
        durations = tuple(self._durations)
        if not durations:
            return PerformanceSnapshot(
                samples=0,
                average_latency_ms=0.0,
                minimum_latency_ms=0.0,
                maximum_latency_ms=0.0,
                frames_per_second=0.0,
                total_frames=self._total_frames,
                dropped_frames=self._dropped_frames,
                drop_rate=self._drop_rate(),
            )
        total_duration = sum(durations)
        return PerformanceSnapshot(
            samples=len(durations),
            average_latency_ms=fmean(durations) * 1000.0,
            minimum_latency_ms=min(durations) * 1000.0,
            maximum_latency_ms=max(durations) * 1000.0,
            frames_per_second=(len(durations) / total_duration if total_duration > 0.0 else 0.0),
            total_frames=self._total_frames,
            dropped_frames=self._dropped_frames,
            drop_rate=self._drop_rate(),
        )

    def reset(self) -> None:
        """Clear all measurements and counters."""
        self._durations.clear()
        self._total_frames = 0
        self._dropped_frames = 0

    def _drop_rate(self) -> float:
        considered = self._total_frames + self._dropped_frames
        return self._dropped_frames / considered if considered else 0.0
