# User guide

## Start safely

The normal demonstration starts with action dispatch disabled:

```bash
python scripts\webcam_demo.py
```

When the supported runtime and a camera are available, this shows webcam frames, detected hands, landmarks, classification status, capture-to-annotated-frame engine-pipeline FPS, and intended action feedback. It does **not** send a media key or alter system volume.

## Demo controls

| Key | Purpose |
| --- | --- |
| `Q` / `Esc` | Quit safely. |
| `A` | Toggle action dispatch; the overlay changes visibly. |
| `R` | Reset smoothing, tracking, cooldown, and action-rearm state. |
| `S` | Save a genuine annotated frame under `screenshots/`. |

Command-line options:

```bash
python scripts\webcam_demo.py --help
```

Frequently used options:

```bash
python scripts\webcam_demo.py --camera 1 --width 1280 --height 720
```

```bash
python scripts\webcam_demo.py --no-mirror
```

## Use gestures

### Open Palm

Show an open, forward-facing palm with extended fingers. The classifier requires all fingers, including thumb, to appear extended. It maps to one **Volume Up** intent after stabilizing.

### Fist

Close all fingers into a compact fist. It is a visible neutral/rearm gesture and deliberately has no operating-system command.

### Thumbs Up

Point the thumb upward in the image while keeping the other fingers folded. It maps to one **Play/Pause** intent after stabilizing. A sideways/rotated thumb deliberately may be shown as `UNKNOWN`.

### Unknown

`UNKNOWN` means a hand exists but its pose is not confidently one of the mandatory gestures. This is expected under partial frames, occlusion, blur, extreme rotation, or in-between positions. It is safer than forcing a potentially action-triggering classification.

## Enable live actions deliberately

Only perform this after testing the disabled/simulation mode. Install optional dependencies from [installation instructions](INSTALLATION.md), then start an explicit live-backend session:

```bash
python scripts\webcam_demo.py --enable-actions --action-backend windows
```

The `A` key lets the person operating the demo enable/disable dispatch while the demo is open. The status overlay always indicates the state. If a backend is unavailable, the application reports the real error and continues recognition.

### Repeat-prevention behavior

- A stabilized `THUMBS_UP` dispatches once, then cannot repeat while held.
- A stabilized `OPEN_PALM` dispatches one bounded volume step, then cannot repeat while held.
- Return to `FIST`, change gesture, or remove the hand for the configured absence interval to rearm the next intentional action.
- Rearming never clears a previous action's cooldown; cooldowns remain a second timing guard.
- When two hands are visible, both appear in the preview but only one deterministic primary track can be action-eligible.

## Use the desktop application

```bash
python main.py
```

The GUI has Start/Stop/Enable Actions controls, current hand/gesture/action/FPS labels, and a live preview. Camera and MediaPipe work runs in a background worker. The main Tk thread alone updates visual widgets, avoiding a frozen or thread-unsafe UI.

## Privacy and screenshots

Frames are processed locally. The code does not upload or persist video. `S` creates an explicit local PNG only when the operator asks for it. Review any screenshot before sharing; it may include surroundings captured by the webcam.

## Recovery

- Press `Q` or close the GUI window to release resources.
- If controls are active, press `A` to disable them immediately.
- If recognition seems stuck, press `R` to reset tracking/action state.
- If the webcam is unavailable, run `python scripts\test_camera.py` and follow [installation troubleshooting](INSTALLATION.md).
