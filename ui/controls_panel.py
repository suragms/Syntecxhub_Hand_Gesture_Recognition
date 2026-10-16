"""User controls for starting capture and explicitly enabling gesture actions."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class ControlsPanel(ttk.LabelFrame):
    """Small action panel that leaves lifecycle decisions to the main window."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_toggle_actions: Callable[[], None],
    ) -> None:
        super().__init__(parent, text="Controls", padding=8)
        self.start_button = ttk.Button(self, text="Start Camera", command=on_start)
        self.start_button.grid(row=0, column=0, padx=4, pady=2)
        self.stop_button = ttk.Button(self, text="Stop", command=on_stop)
        self.stop_button.grid(row=0, column=1, padx=4, pady=2)
        self.actions_button = ttk.Button(self, text="Enable Actions", command=on_toggle_actions)
        self.actions_button.grid(row=0, column=2, padx=4, pady=2)
        self.set_running(False)

    def set_actions_enabled(self, enabled: bool) -> None:
        self.actions_button.configure(text="Disable Actions" if enabled else "Enable Actions")

    def set_running(self, running: bool, *, stopping: bool = False) -> None:
        """Reflect capture ownership state and prevent conflicting callbacks."""
        self.start_button.configure(state="disabled" if running or stopping else "normal")
        self.stop_button.configure(state="normal" if running and not stopping else "disabled")
        self.actions_button.configure(state="normal" if running and not stopping else "disabled")
