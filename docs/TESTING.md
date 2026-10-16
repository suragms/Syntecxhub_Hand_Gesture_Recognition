# Testing and verification

## Recorded development evidence

The following commands were actually completed on Windows during implementation:

| Check | Result | Scope |
| --- | --- | --- |
| `python -m pytest -q` | **18 passed** | Pure landmark/classifier/smoother/action logic plus mocked camera lifecycle; no real media or volume side effects. |
| `python -m compileall -q .` | Passed | Source compilation check. |
| `python scripts/test_gestures.py` | Passed | Synthetic open-palm fixture classified as `OPEN_PALM`. |
| `python scripts/test_camera.py` | Passed | Camera index 0 opened through DirectShow and returned one 640×480 frame. |
| CLI help checks | Passed | `webcam_demo.py`, `test_camera.py`, and `app.py` all displayed help. |

Full live MediaPipe hand-landmark/gesture verification was **not** completed in this development environment. The active Python 3.14 MediaPipe package exposed a Tasks-only API, while this application pins a Python 3.11 legacy-Hands baseline. Use the documented Python 3.11 virtual environment before completing the manual checklist below. No real Play/Pause or system-volume action was intentionally dispatched during automated testing.

## Important distinction: code tests vs. hardware verification

Automated tests establish deterministic logic behavior, not real-world recognition quality. Hardware validation is required for claims about a specific camera, lighting setup, media player, or audio endpoint.

| Activity | Command | What it establishes | What it does not establish |
| --- | --- | --- | --- |
| Automated tests | `python -m pytest -q` | Committed logic behavior in a controlled environment | That a real webcam opens or a gesture is reliable on a person's hardware |
| Camera diagnostic | `python scripts\test_camera.py` | One fresh frame from the selected local camera | General compatibility across cameras, drivers, or systems |
| Gesture fixture diagnostic | `python scripts\test_gestures.py` | Basic synthetic classifier wiring | Real-world recognition accuracy |
| Minimal preview | `python scripts\webcam_demo.py` | Local detector/preview behavior after dependencies are installed | Broad hardware support or action safety beyond the test performed |
| Desktop app | `python main.py` | GUI behavior in the observed configuration | Independent confirmation of every optional adapter |

## Automated coverage

The pytest suite deliberately avoids physical hardware and external side effects.

### Unit and mock coverage

- Landmark count, finite coordinate, and degenerate-palm validation.
- Scale-normalized input processing and handedness values.
- Mandatory `OPEN_PALM`, `FIST`, and `THUMBS_UP` classifier fixtures.
- Conservative `UNKNOWN` behavior for a partial/ambiguous gesture.
- Time-based smoothing, flicker tolerance, and track-history cleanup.
- Disabled actions, action mapping, neutral rearming, cooldown, and one-shot repeat prevention.
- Simulation volume clamping.
- Camera-open failure, empty frame, and idempotent release via mocked OpenCV capture.

Run all tests:

```bash
python -m pytest -q
```

## Manual Windows validation checklist

Complete this in the Python 3.11 virtual environment, recording the date, Windows version, camera index/model, MediaPipe/OpenCV versions, and configuration used.

### Camera and preview

- [ ] Run `python scripts\test_camera.py`; record actual result.
- [ ] Run `python scripts\webcam_demo.py`; confirm preview is live and exits with `Q`.
- [ ] Confirm the camera releases by opening it in another camera app afterward.
- [ ] Verify a busy/disconnected camera produces the intended error rather than a crash.
- [ ] Try another camera index if available.

### Landmark and gesture behavior

- [ ] Confirm landmark points, connections, bounding boxes, and handedness labels appear.
- [ ] Test **Open Palm** under normal light, dim light, and backlight.
- [ ] Test **Fist** under the same conditions.
- [ ] Test **Thumbs Up** with the thumb upright and other fingers folded.
- [ ] Confirm partial/rotated/occluded poses tend toward `UNKNOWN` and do not accidentally trigger controls.
- [ ] Show two hands and confirm both are displayed while only one is action-eligible.
- [ ] Record actual FPS at the resolution used; do not extrapolate it as a benchmark.

### Action safety and integration

1. Start with ordinary `python scripts\webcam_demo.py` and verify the overlay states that actions are disabled/simulated.
2. Exercise each mandatory gesture; confirm no real host control occurs.
3. Observe a stable `THUMBS_UP` or `OPEN_PALM` in simulation mode; verify exactly one intended event is displayed for a held gesture.
4. Only after those checks, install optional action integrations and run the explicit live-command form:

```bash
python scripts\webcam_demo.py --enable-actions --action-backend windows
```

5. Confirm one `THUMBS_UP` gives at most one Play/Pause request.
6. Confirm one `OPEN_PALM` gives at most one bounded configured volume increment.
7. Hold either gesture and ensure it does not repeatedly execute.
8. Return to `FIST`, change gesture, or remove the hand long enough to rearm; then verify a second intentional action is possible.
9. Confirm an unavailable player/audio endpoint displays an error while landmark detection continues.

## Reporting format

For a submission record, save a short validation entry containing:

- application revision/date;
- Python, MediaPipe, OpenCV, and Windows versions;
- camera model/index, frame resolution, and lighting condition;
- command and effective configuration;
- pass/fail/observed result for each checklist item;
- known false positives/unknown results;
- whether actions remained simulated or were deliberately enabled.

Do not mark hardware-dependent acceptance criteria complete from an automated test alone.
