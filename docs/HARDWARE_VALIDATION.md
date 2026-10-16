# Hardware validation record

Use this document only for observed evidence from a real machine. Automated tests never prove webcam, recognition-accuracy, GUI, FPS, or host-control behavior.

## Current audit status

| Area | Status | Evidence / next step |
| --- | --- | --- |
| Automated deterministic suite | **PASSED** | `python -m pytest -q` → `27 passed` under Python 3.14.4. |
| Compilation | **PASSED** | `python -m compileall .` completed under Python 3.14.4. |
| Webcam capture | **NOT TESTED** | The audit did not open a physical camera. |
| Live MediaPipe landmarks/gestures | **BLOCKED** | Installed MediaPipe 0.10.35 on Python 3.14.4 does not expose `mp.solutions`. Create the supported Python 3.11 environment and install pinned dependencies. |
| OpenCV/Tk live preview | **BLOCKED** | Depends on successful camera/legacy MediaPipe validation. |
| Measured real FPS | **NOT TESTED** | Do not infer a number from unit tests. |
| Simulation-only action flow | **PARTIALLY VERIFIED** | Mocked tests verify mapping, cooldown, rearming, and no external controller use while disabled. |
| Real Play/Pause / volume backends | **NOT TESTED** | Requires deliberate operator opt-in; no backend was enabled during this audit. |

## Environment record (complete before manual testing)

| Field | Value |
| --- | --- |
| Git revision | |
| Date and tester | |
| Windows version | |
| Python executable and version | |
| MediaPipe version | |
| OpenCV version | |
| Camera make/model/index | |
| Camera backend/resolution/requested FPS | |
| Lighting/background | |
| Mirrored preview? | |
| Action backend | Simulation / PyAutoGUI / Windows |

## Commands

```bash
py -3.11 -m venv .venv
```

```bash
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -r requirements.txt
```

```bash
python -m pytest -q
```

```bash
python scripts\test_camera.py
```

```bash
python scripts\webcam_demo.py
```

## Evidence checklist

Record each entry as **PASS**, **FAIL**, **NOT RUN**, or **BLOCKED**. Add observed behavior, errors, FPS, and screenshots only when genuinely collected.

| Scenario | Status | Observed evidence / notes |
| --- | --- | --- |
| Camera opens and preview receives fresh frames | | |
| Pressing `Q`/`Esc` releases camera; another application can open it | | |
| Camera busy/disconnected error remains actionable | | |
| No black/frozen preview over at least one minute | | |
| Frame overlays do not accumulate or visibly flicker | | |
| Landmark points, connections, and bounded boxes render correctly | | |
| Right-hand Open Palm → `OPEN_PALM` | | |
| Left/mirrored Open Palm → `OPEN_PALM` | | |
| Right-hand Fist → `FIST` | | |
| Left/mirrored Fist → `FIST` | | |
| Right-hand Thumbs Up → `THUMBS_UP` | | |
| Left/mirrored Thumbs Up → `THUMBS_UP` | | |
| Partial, blurred, rotated, and occluded hands tend to `UNKNOWN` | | |
| Near/far hand distances remain usable at the selected resolution | | |
| Two hands render; exactly one primary track is action-eligible | | |
| Reported capture-to-annotated-frame FPS | | |
| Simulation mode does not alter host media/volume | | |
| Held simulated Thumbs Up creates one intent only | | |
| Held simulated Open Palm creates one intent only | | |
| Fist or sustained hand absence rearms without bypassing cooldown | | |
| Explicit real Play/Pause backend test (optional) | | |
| Explicit real Volume Up backend test (optional) | | |

## Requirement traceability matrix

| Internship requirement | Implementation | Automated evidence | Manual evidence required | Current status |
| --- | --- | --- | --- | --- |
| Real-time OpenCV/MediaPipe hand landmarks | `core/camera.py`, `core/hand_detector.py`, `core/engine.py` | Mocked capture/adapter tests | Live preview and landmarks checklist | **BLOCKED** |
| Thumbs Up, Fist, Open Palm classification | `core/landmark_processor.py`, `core/gesture_classifier.py`, `core/gesture_smoother.py` | Synthetic required-gesture, unknown, smoothing, and configuration tests | Left/right/mirror/distance/rotation cases | **PARTIALLY VERIFIED** |
| Gesture mapping to computer actions | `core/action_manager.py`, `actions/action_registry.py` | Mocked/simulation mapping, cooldown, rearm, disabled-action tests | Simulation then opt-in real backend checklist | **PARTIALLY VERIFIED** |
| Working webcam demonstration script | `scripts/webcam_demo.py`, `core/engine.py` | CLI help check | Live launch, fresh frames, cleanup, measured FPS | **BLOCKED** |

## Known limits to record honestly

- The rule-based classifier is conservative, not a trained sign-language model.
- Extreme hand roll, foreshortening, depth changes, occlusion, blur, and low light may become `UNKNOWN` or misclassify.
- Thumbs Up is evaluated against image-up; strongly rotated hands are intentionally unreliable.
- Wrist-distance tracking can swap identities when hands cross or are occluded.
- Webcam availability depends on Windows privacy settings, drivers, backend, and competing applications.
- Media keys and system volume depend on the selected player/audio endpoint and optional Windows packages.
