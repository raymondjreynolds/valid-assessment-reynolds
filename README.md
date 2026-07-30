# Valid Assessment Video API

Python API for receiving MP4 uploads, extracting video metadata, and serving files from an in-memory store.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload one or more MP4 files (multipart `files` field) |
| `GET` | `/videos` | List all uploaded videos (optional `?ratio=9:16\|1:1\|4:5\|16:9` filter) |
| `GET` | `/match?video_id=<id>` | Cross-bucket visual matches with confidence scores |
| `DELETE` | `/videos/{video_id}` | Delete an uploaded video |
| `GET` | `/health` | Health check for Render |

### Upload

```bash
curl -X POST https://your-service.onrender.com/upload \
  -F "files=@video1.mp4" \
  -F "files=@video2.mp4"
```

Response:

```json
[
  {
    "video_id": "59936273",
    "width": 576,
    "height": 1024,
    "aspect_ratio": "9:16",
    "ratio_bucket": "9:16",
    "filename": "video1.mp4"
  }
]
```

Standard `ratio_bucket` values: `9:16`, `1:1`, `4:5`, `16:9`, or `Other`.

### Match

```bash
curl "https://your-service.onrender.com/match?video_id=59936273"
```

Response:

```json
[
  {
    "video_id": "63223501",
    "ratio_bucket": "1:1",
    "confidence": 0.84,
    "matched_frame_ratio": 0.68,
    "alignment": "partial",
    "method": "dinov2"
  }
]
```

Matching is **cross-bucket only**: a query never matches videos in its own `ratio_bucket`. Uploads return immediately; DINOv2 fingerprinting runs in a background task after upload.

If `/match` is called before fingerprints are ready, the API returns **HTTP 202**:

```json
{
  "status": "processing",
  "message": "Fingerprints are still being computed for video 59936273",
  "video_id": "59936273"
}
```

If fingerprinting fails or exceeds the timeout, the API returns **HTTP 503** with `status` of `failed` or `timed_out`.

Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FRAME_SAMPLE_FPS` | `0.5` | Frame sampling rate during fingerprinting |
| `MAX_FRAMES` | `12` | Hard cap on frames embedded per video |
| `FRAME_SCALE_WIDTH` | `256` | Downscale width during ffmpeg extraction |
| `CENTER_CROP_FRACTION` | `0.85` | Center crop applied before embedding |
| `MATCH_CONFIDENCE_THRESHOLD` | `0.5` | Minimum match confidence to return |
| `FRAME_SIMILARITY_THRESHOLD` | `0.75` | Minimum cosine similarity for frame pairs |
| `MIN_ALIGNED_FRAMES` | `3` | Minimum temporally aligned frames required |
| `FINGERPRINT_TIMEOUT_SECONDS` | `600` | Max seconds to wait for background fingerprinting |
| `PRELOAD_DINOV2` | `true` | Warm-load DINOv2 on service startup |
| `TORCH_NUM_THREADS` | `2` | CPU threads used by PyTorch on Render |

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Deploy to Render

1. Push this repo to GitHub.
2. Create a **Web Service** on [render.com](https://render.com) connected to the repo.
3. Use the included `render.yaml` Blueprint, or set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Python version:** `3.12.8` via `PYTHON_VERSION` env var or `.python-version` (required for PyTorch)

No other environment variables are required.

## Notes

- Only `.mp4` files are accepted.
- `video_id` is an 8-digit ID derived from the file content (CRC32).
- Videos, metadata, and DINOv2 fingerprints are kept in memory only and are lost on redeploy or restart.
- The matching pipeline is pluggable: `NoOpPrefilter` passes all cross-bucket candidates to DINOv2 scoring today; a future vPDQ pre-filter can plug in without changing the API.

## Architecture

```text
upload → store video + metadata → return response
       → background task → sample frames → DINOv2 fingerprints
GET /match → if processing: HTTP 202
            → if ready: cross-bucket candidates → prefilter → temporal alignment → confidence score
```

Future vPDQ support is stubbed in `app/fingerprints/vpdq.py` and `app/matching/prefilter.py`.
