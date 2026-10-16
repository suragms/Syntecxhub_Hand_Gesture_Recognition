"""Textual live recognition and action status for the Tkinter interface."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class StatusPanel(ttk.LabelFrame):
    """Present current detector state without owning any worker state."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Live Status", padding=8)
        self.hand = tk.StringVar(value="Detected hand: None")
        self.gesture = tk.StringVar(value="Current gesture: No hand detected")
        self.action = tk.StringVar(value="Action: Controls disabled")
        self.fps = tk.StringVar(value="FPS: --")
        for row, value in enumerate((self.hand, self.gesture, self.action, self.fps)):
            ttk.Label(self, textvariable=value).grid(row=row, column=0, sticky="w", pady=2)

    def update(self, *, hand: str, gesture: str, action: str, fps: float) -> None:
        self.hand.set(f"Detected hand: {hand}")
        self.gesture.set(f"Current gesture: {gesture}")
        self.action.set(f"Action: {action}")
        self.fps.set(f"FPS: {fps:.1f}" if fps else "FPS: --")
