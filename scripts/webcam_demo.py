"""Standalone real-time webcam demonstration for the gesture-recognition system."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    ActionConfig,
    AppConfig,
    CameraConfig,
    DEFAULT_CONFIG,
    DetectorConfig,
    RecognitionConfig,
)
from core.camera import CameraError  # noqa: E402
from core.engine import GestureEngine  # noqa: E402
from core.hand_detector import HandDetectorError  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process a real webcam feed with MediaPipe hand landmarks and safe gesture actions."
    )
    parser.add_argument("--camera", type=int, default=DEFAULT_CONFIG.camera.index, help="Webcam index (default: 0).")
    parser.add_argument("--width", type=int, default=DEFAULT_CONFIG.camera.width, help="Requested camera width.")
    parser.add_argument("--height", type=int, default=DEFAULT_CONFIG.camera.height, help="Requested camera height.")
    parser.add_argument("--show-fps", action="store_true", help="Display measured FPS (shown by default).")
    parser.add_argument(
        "--enable-actions",
        action="store_true",
        help="Explicitly enable configured computer actions. Default is safe simulation/disabled mode.",
    )
    parser.add_argument(
        "--action-backend",
        choices=("simulation", "pyautogui", "windows"),
        default="simulation",
        help="Action adapter: simulation is safe; pyautogui/windows require optional packages.",
    )
    parser.add_argument("--no-mirror", action="store_true", help="Show the unmirrored camera preview.")
    parser.add_argument("--backend", choices=("auto", "dshow", "msmf", "any"), default="auto", help="OpenCV camera backend preference.")
    return parser.parse_args()


def make_config(args: argparse.Namespace) -> AppConfig:
    return AppConfig(
        camera=CameraConfig(
            index=args.camera,
            width=args.width,
            height=args.height,
            target_fps=DEFAULT_CONFIG.camera.target_fps,
            mirror=not args.no_mirror,
            backend=args.backend,
        ),
        detector=DetectorConfig(),
        recognition=RecognitionConfig(),
        actions=ActionConfig(
            enabled_by_default=args.enable_actions,
            backend=args.action_backend,
        ),
    )


def save_screenshot(frame: object) -> str:
    import cv2

    destination = ROOT / "screenshots"
    destination.mkdir(exist_ok=True)
    path = destination / f"gesture_{datetime.now():%Y%m%d_%H%M%S}.png"
    if not cv2.imwrite(str(path), frame):
        raise RuntimeError("OpenCV could not write the screenshot.")
    return str(path.relative_to(ROOT))


def main() -> int:
    args = parse_args()
    config = make_config(args)
    config.validate()
    window_name = "Syntecxhub Hand Gesture Recognition — Q Quit | A Actions | R Reset | S Screenshot"
    engine = GestureEngine(config, action_backend=args.action_backend)
    try:
        engine.start()
        import cv2

        while True:
            result = engine.process_next_frame()
            cv2.imshow(window_name, result.frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("a"):
                enabled = engine.toggle_actions()
                print("Actions enabled." if enabled else "Actions disabled.")
            elif key == ord("r"):
                engine.reset()
                print("Recognition/action state reset.")
            elif key == ord("s"):
                try:
                    print(f"Saved screenshot: {save_screenshot(result.frame)}")
                except RuntimeError as error:
                    print(f"Screenshot failed: {error}", file=sys.stderr)
    except (CameraError, HandDetectorError, RuntimeError) as error:
        print(f"Demo error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        engine.close()
        try:
            import cv2

            cv2.destroyAllWindows()
        except ImportError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
