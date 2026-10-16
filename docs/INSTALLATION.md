# Installation

## Supported baseline

- Windows 10 or Windows 11, 64-bit.
- Python **3.11**, 64-bit.
- A built-in or USB webcam.
- CPU-only hardware; no CUDA, TensorFlow, PyTorch, or dedicated GPU is required.

This project uses the synchronous MediaPipe Hands API, which must be installed from the pinned `requirements.txt` in the supported Python 3.11 environment. Do not treat a successful installation under another Python version as verified compatibility.

## Create an isolated environment

From the repository root:

```bash
python --version
```

```bash
py -3.11 -m venv .venv
```

```bash
.\.venv\Scripts\Activate.ps1
```

If PowerShell reports that scripts cannot run, apply this temporary, process-scoped setting—not a permanent machine-wide relaxation:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

```bash
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install --upgrade pip
```

```bash
python -m pip install -r requirements.txt
```

## Dependency notes

- `opencv-python` is the sole GUI-capable OpenCV distribution declared for the supported Python 3.11 baseline. Do not install it alongside `opencv-contrib-python` or any `*-headless` flavor in the same environment.
- `mediapipe` is pinned because native wheel/API behavior is sensitive to interpreter version.
- Tkinter is included with the standard Python Windows installer; it is not installed with `pip`.
- Pillow is used only to render OpenCV BGR images in the optional Tkinter UI.

## Optional real action packages

The core application is usable without any host-control package. To enable the optional live Windows backends only after validating simulation behavior, install:

```bash
python -m pip install pyautogui==0.9.54 pycaw==20240210 comtypes==1.4.7
```

Installing them does not enable actions. Start a live mode explicitly only after reviewing the safety guidance:

```bash
python scripts\webcam_demo.py --enable-actions --action-backend windows
```

## First-run checks

```bash
python scripts\test_camera.py
```

```bash
python scripts\test_gestures.py
```

```bash
python -m pytest -q
```

Then launch the required demo:

```bash
python scripts\webcam_demo.py
```

## Common installation problems

| Problem | Resolution |
| --- | --- |
| `py -3.11` is unavailable | Install 64-bit Python 3.11 from python.org, then recreate `.venv`. |
| MediaPipe import/API error | Confirm `.venv` is active and reinstall the pinned requirements with Python 3.11. |
| OpenCV DLL/import error | Remove conflicting OpenCV packages from the environment, then reinstall only `opencv-python` from `requirements.txt`. |
| Camera cannot open | Check Windows Settings → Privacy & security → Camera, close other camera apps, and try `--camera 1`. |
| `PIL` error in GUI | Reinstall `Pillow` using the active project environment. |
