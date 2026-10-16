"""Optional Tkinter desktop application entry point."""

from __future__ import annotations

import argparse
import os
import tkinter as tk
import warnings

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("GLOG_minloglevel", "2")
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")

from config import AppConfig, CameraConfig, DEFAULT_CONFIG
from ui.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the Syntecxhub gesture-recognition desktop app.")
    parser.add_argument("--camera", type=int, default=DEFAULT_CONFIG.camera.index, help="Webcam index.")
    args = parser.parse_args()
    config = AppConfig(camera=CameraConfig(index=args.camera))
    config.validate()
    root = tk.Tk()
    MainWindow(root, config)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
