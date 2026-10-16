# Model directory

This release uses the MediaPipe Hands solution provided by the installed, pinned MediaPipe package. It does **not** download or bundle a repository-local `.task`, `.tflite`, or trained model binary.

The application currently targets the synchronous Hands API in the documented Python 3.11 Windows baseline. If the project later migrates to the MediaPipe Tasks Hand Landmarker API, add the official model asset deliberately and document:

- exact model name, version, official source URL, and license;
- SHA-256 checksum;
- storage/install procedure;
- expected input preprocessing;
- code path that loads it; and
- validation evidence for the new API.

Do not commit downloaded, trained, or licensed model binaries without confirming redistribution terms. `.gitignore` excludes common model formats in this directory.
