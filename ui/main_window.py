"""Thread-safe Tkinter desktop window for the optional gesture-recognition UI."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Any

from config import AppConfig
from core.engine import FrameResult, GestureEngine
from ui.camera_panel import CameraPanel
from ui.controls_panel import ControlsPanel
from ui.status_panel import StatusPanel


@dataclass(frozen=True, slots=True)
class _WorkerMessage:
    kind: str
    payload: Any


class MainWindow:
    """Keep capture/inference off Tk's event thread and update safely with ``after``."""

    def __init__(self, root: tk.Tk, config: AppConfig) -> None:
        self.root = root
        self.config = config
        self.engine: GestureEngine | None = None
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._results: queue.Queue[_WorkerMessage] = queue.Queue(maxsize=1)
        self._running = False

        root.title("Syntecxhub Hand Gesture Recognition")
        root.minsize(720, 600)
        root.protocol("WM_DELETE_WINDOW", self.close)
        content = ttk.Frame(root, padding=12)
        content.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        ttk.Label(
            content,
            text="SYNTECXHUB HAND GESTURE RECOGNITION",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.camera_panel = CameraPanel(content)
        self.camera_panel.grid(row=1, column=0, sticky="nsew")
        self.status_panel = StatusPanel(content)
        self.status_panel.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.controls = ControlsPanel(
            content,
            on_start=self.start,
            on_stop=self.stop,
            on_toggle_actions=self.toggle_actions,
        )
        self.controls.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            content,
            text="Supported gestures: Thumbs Up • Fist • Open Palm",
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.root.after(30, self._poll_results)

    def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._worker = threading.Thread(target=self._run_worker, name="gesture-camera", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self.engine is not None:
            self.engine.close()
        self.camera_panel.clear()

    def toggle_actions(self) -> None:
        if self.engine is None:
            messagebox.showinfo("Actions", "Start the camera before changing action controls.")
            return
        if not self.engine.actions_enabled:
            approved = messagebox.askyesno(
                "Enable operating-system actions?",
                "Real media and volume actions may affect the current computer. Continue?",
                icon="warning",
            )
            if not approved:
                return
        enabled = self.engine.toggle_actions()
        self.controls.set_actions_enabled(enabled)

    def _run_worker(self) -> None:
        try:
            self.engine = GestureEngine(self.config, action_backend=self.config.actions.backend)
            self.engine.start()
            while not self._stop_event.is_set():
                result = self.engine.process_next_frame()
                self._put_latest(_WorkerMessage("frame", result))
        except Exception as error:
            self._put_latest(_WorkerMessage("error", str(error)))
        finally:
            if self.engine is not None:
                self.engine.close()
            self._put_latest(_WorkerMessage("stopped", None))

    def _put_latest(self, message: _WorkerMessage) -> None:
        try:
            self._results.put_nowait(message)
        except queue.Full:
            try:
                self._results.get_nowait()
            except queue.Empty:
                pass
            try:
                self._results.put_nowait(message)
            except queue.Full:
                pass

    def _poll_results(self) -> None:
        latest: _WorkerMessage | None = None
        while True:
            try:
                latest = self._results.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            if latest.kind == "frame":
                self._show_frame(latest.payload)
            elif latest.kind == "error":
                self._running = False
                self.camera_panel.clear("Camera error. See the message below.")
                messagebox.showerror("Camera or recognition error", str(latest.payload))
            elif latest.kind == "stopped":
                self._running = False
        self.root.after(30, self._poll_results)

    def _show_frame(self, result: FrameResult) -> None:
        self.camera_panel.update_frame(result.frame)
        if result.recognition.hands:
            primary = result.recognition.hands[0]
            hand = primary.landmarks.handedness.value.title()
            gesture = primary.smoothed_gesture.gesture.value.upper()
        else:
            hand, gesture = "None", "NO HAND DETECTED"
        action = result.action_event.result.message if result.action_event else (self.engine.last_status if self.engine else "")
        self.status_panel.update(hand=hand, gesture=gesture, action=action, fps=result.fps)
        self.controls.set_actions_enabled(bool(self.engine and self.engine.actions_enabled))

    def close(self) -> None:
        self.stop()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=1.5)
        self.root.destroy()
