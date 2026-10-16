"""Non-destructive command-line diagnostic for webcam access and frame capture."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import CameraConfig  # noqa: E402
from core.camera import Camera, CameraError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Open one webcam, read one fresh frame, and release it.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default: 0).")
    parser.add_argument("--width", type=int, default=640, help="Requested width.")
    parser.add_argument("--height", type=int, default=480, help="Requested height.")
    args = parser.parse_args()
    camera = Camera(CameraConfig(index=args.camera, width=args.width, height=args.height))
    try:
        camera.open()
        frame = camera.read()
        height, width = frame.shape[:2]
        print(f"Camera {args.camera} OK via {camera.backend_name}: received {width}x{height} frame.")
    except CameraError as error:
        print(f"Camera test failed: {error}", file=sys.stderr)
        return 1
    finally:
        camera.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
