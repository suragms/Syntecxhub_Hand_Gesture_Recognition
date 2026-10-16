"""Tkinter camera-preview widget that is updated only by the UI thread."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


class CameraPanel(ttk.Frame):
    """A resize-friendly image panel for annotated BGR camera frames."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=8)
        self._image: Any | None = None
        self.preview = ttk.Label(self, text="Camera preview is stopped.", anchor="center")
        self.preview.pack(fill="both", expand=True)

    def update_frame(self, frame: Any) -> None:
        """Convert BGR → RGB and display a retained Pillow image reference."""
        try:
            import cv2
            from PIL import Image, ImageTk
        except ImportError:
            self.preview.configure(text="Pillow/OpenCV is needed to render the preview.", image="")
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((900, 600))
        self._image = ImageTk.PhotoImage(image=image)
        self.preview.configure(image=self._image, text="")

    def clear(self, message: str = "Camera preview is stopped.") -> None:
        self._image = None
        self.preview.configure(image="", text=message)
