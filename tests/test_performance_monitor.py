from __future__ import annotations

import pytest

from core.performance_monitor import PerformanceMonitor


def test_snapshot_reports_rolling_fps_and_reset() -> None:
    monitor = PerformanceMonitor(window_size=2)
    monitor.record_duration(0.1)
    monitor.record_duration(0.2)
    monitor.record_duration(0.3)

    snapshot = monitor.snapshot()
    assert snapshot.samples == 2
    assert snapshot.total_frames == 3
    assert snapshot.frames_per_second == pytest.approx(4.0)

    monitor.reset()
    assert monitor.snapshot().samples == 0


def test_invalid_duration_is_rejected() -> None:
    with pytest.raises(ValueError):
        PerformanceMonitor().record_duration(-0.1)
