"""Run the geometric classifier against deterministic synthetic sample poses."""

from __future__ import annotations

import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gesture_classifier import GestureClassifier  # noqa: E402
from core.landmark_processor import LandmarkProcessor  # noqa: E402
from core.models import Point3D  # noqa: E402


def open_palm() -> tuple[Point3D, ...]:
    """Return a simple scale-valid palm fixture suitable for diagnostic output."""
    return (
        Point3D(0.0, 0.0), Point3D(-0.55, -0.10), Point3D(-0.75, -0.25), Point3D(-0.95, -0.45), Point3D(-1.12, -0.68),
        Point3D(-0.35, -0.65), Point3D(-0.38, -1.15), Point3D(-0.40, -1.60), Point3D(-0.42, -2.02),
        Point3D(0.0, -0.72), Point3D(0.0, -1.30), Point3D(0.0, -1.82), Point3D(0.0, -2.25),
        Point3D(0.35, -0.65), Point3D(0.40, -1.13), Point3D(0.45, -1.53), Point3D(0.50, -1.88),
        Point3D(0.67, -0.45), Point3D(0.77, -0.82), Point3D(0.85, -1.12), Point3D(0.92, -1.40),
    )


def main() -> int:
    processor = LandmarkProcessor()
    processed = processor.from_landmarks(open_palm(), timestamp=monotonic(), confidence=1.0)
    result = GestureClassifier().classify(processed)
    print(f"Synthetic sample classification: {result.gesture.value.upper()}")
    print(f"Heuristic evidence: {result.confidence:.2f} (not a calibrated probability)")
    print(f"Reason: {result.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
