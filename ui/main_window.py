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
    run_id: int
    kind: str
    payload: Any


class MainWindow:
    """Keep native capture in one worker and update Tk through ``after`` only."""

    def __init__(self, root: tk.Tk, config: AppConfig) -> None:
        self.root = root
        self.config = config
        self._worker: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._commands: queue.Queue[str] = queue.Queue()
        self._frames: queue.Queue[_WorkerMessage] = queue.Queue(maxsize=1)
        self._events: queue.Queue[_WorkerMessage] = queue.Queue()
        self._active_run_id = 0
        self._running = False
        self._stopping = False
        self._closing = False
        self._actions_enabled = False

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
        """Start a new worker only after the prior native owner has stopped."""
        if self._running or self._stopping or (self._worker and self._worker.is_alive()):
            return
        self._active_run_id += 1
        run_id = self._active_run_id
        stop_event = threading.Event()
        self._stop_event = stop_event
        self._running = True
        self._stopping = False
        self._actions_enabled = False
        self.controls.set_actions_enabled(False)
        self.controls.set_running(True)
        self._worker = threading.Thread(
            target=self._run_worker,
            args=(run_id, stop_event),
            name=f"gesture-camera-{run_id}",
            daemon=True,
        )
        self._worker.start()

    def stop(self) -> None:
        """Signal the worker; only its thread closes camera/MediaPipe resources."""
        if not self._running or self._stopping:
            return
        self._stopping = True
        if self._stop_event is not None:
            self._stop_event.set()
        self.controls.set_running(True, stopping=True)
        self.camera_panel.clear("Stopping camera preview…")

    def toggle_actions(self) -> None:
        if not self._running or self._stopping:
            return
        if not self._actions_enabled:
            approved = messagebox.askyesno(
                "Enable operating-system actions?",
                "Real media and volume actions may affect the current computer. Continue?",
                icon="warning",
            )
            if not approved:
                return
        self.controls.actions_button.configure(state="disabled")
        self._commands.put("toggle_actions")

    def _run_worker(self, run_id: int, stop_event: threading.Event) -> None:
        """Own one engine for the complete lifetime of a worker session."""
        engine: GestureEngine | None = None
        try:
            engine = GestureEngine(self.config, action_backend=self.config.actions.backend)
            engine.start()
            self._put_event(_WorkerMessage(run_id, "action_state", engine.actions_enabled))
            while not stop_event.is_set():
                self._apply_commands(run_id, engine)
                result = engine.process_next_frame()
                self._put_latest_frame(_WorkerMessage(run_id, "frame", result))
        except Exception as error:
            self._put_event(_WorkerMessage(run_id, "error", str(error)))
        finally:
            if engine is not None:
                engine.close()
            self._put_event(_WorkerMessage(run_id, "stopped", None))

    def _apply_commands(self, run_id: int, engine: GestureEngine) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            if command == "toggle_actions":
                self._put_event(
                    _WorkerMessage(run_id, "action_state", engine.toggle_actions())
                )

    def _put_latest_frame(self, message: _WorkerMessage) -> None:
        try:
            self._frames.put_nowait(message)
        except queue.Full:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                pass
            try:
                self._frames.put_nowait(message)
            except queue.Full:
                pass

    def _put_event(self, message: _WorkerMessage) -> None:
        self._events.put(message)

    def _poll_results(self) -> None:
        self._process_events()
        self._process_latest_frame()
        if not self._closing:
            self.root.after(30, self._poll_results)

    def _process_events(self) -> None:
        while True:
            try:
                message = self._events.get_nowait()
            except queue.Empty:
                return
            if message.run_id != self._active_run_id:
                continue
            if message.kind == "action_state":
                self._actions_enabled = bool(message.payload)
                self.controls.set_actions_enabled(self._actions_enabled)
                self.controls.set_running(self._running, stopping=self._stopping)
            elif message.kind == "error":
                self._running = False
                self._stopping = True
                self.controls.set_running(False, stopping=True)
                self.camera_panel.clear("Camera error. See the message below.")
                messagebox.showerror("Camera or recognition error", str(message.payload))
            elif message.kind == "stopped":
                self._running = False
                self._stopping = False
                self._stop_event = None
                self._actions_enabled = False
                self.controls.set_actions_enabled(False)
                self.controls.set_running(False)
                if self._closing:
                    self.root.destroy()

    def _process_latest_frame(self) -> None:
        latest: _WorkerMessage | None = None
        while True:
            try:
                candidate = self._frames.get_nowait()
            except queue.Empty:
                break
            if candidate.run_id == self._active_run_id:
                latest = candidate
        if latest is not None and self._running and not self._stopping:
            self._show_frame(latest.payload)

    def _show_frame(self, result: FrameResult) -> None:
        self.camera_panel.update_frame(result.frame)
        if result.recognition.hands:
            primary = result.recognition.hands[0]
            hand = primary.landmarks.handedness.value.title()
            gesture = primary.smoothed_gesture.gesture.value.upper()
        else:
            hand, gesture = "None", "NO HAND DETECTED"
        action = result.action_event.result.message if result.action_event else ""
        self.status_panel.update(hand=hand, gesture=gesture, action=action, fps=result.fps)
        self.controls.set_actions_enabled(self._actions_enabled)

    def close(self) -> None:
        """Request orderly worker cleanup before destroying the Tk root."""
        self._closing = True
        if self._running:
            self.stop()
            return
        self.root.destroy()
