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
    "filename": "video_reframed_1-1.mp4",
    "confidence": 0.5677
  }
]
```

Matching is **cross-bucket only**: a query never matches videos in its own `ratio_bucket`. Videos in the **`Other`** bucket are excluded from matching entirely (as query or candidate). Uploads return immediately; **vPDQ (PDQ frame hashes)** fingerprinting runs in a background task by default. Set `FINGERPRINT_METHOD=dinov2` locally for higher-accuracy matching (requires `requirements-dinov2.txt`).

`/match` returns **HTTP 202** until **all** uploaded videos have finished fingerprinting:

```json
{
  "status": "processing",
  "message": "Fingerprints are still being computed"
}
```

If fingerprinting fails or exceeds the timeout, the API returns **HTTP 503** with `status` of `failed` or `timed_out`.

#### Expected confidence scores

Confidence is computed as `matched_frame_ratio × mean_frame_similarity` (0–1). For **cross-bucket reframed UGC** with vPDQ, **0.5–0.7 is normal** for true matches; identical pixel-level clips would score near 1.0 but are excluded by the cross-bucket rule. Unrelated videos should score lower than reframed versions of the same creative.

`/match` returns only candidates at or above `MATCH_CONFIDENCE_THRESHOLD` (default **0.50**), sorted by confidence descending. Use **0.35–0.40** for maximum recall on heavily reframed clips.

Sampling is **length-aware**: frame rate and cap adjust to each video's duration (see table below). More frames improves temporal coverage but does **not** guarantee higher scores. For consistently higher legitimate scores on reframed content, use **DINOv2** locally.

| Duration | Sample rate | Max frames |
|----------|-------------|------------|
| ≤15s | 1 fps | 12 |
| ≤30s | 1 fps | 16 |
| ≤60s | 0.5 fps | 20 |
| >60s | 0.5 fps | 24 |

Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FINGERPRINT_METHOD` | `vpdq` | `vpdq` (fast, Render default) or `dinov2` (accurate, needs PyTorch) |
| `MATCH_CONFIDENCE_THRESHOLD` | `0.50` | Minimum match confidence returned by `/match` |
| `VPDQ_HAMMING_THRESHOLD` | `50` | Max PDQ Hamming distance for frame match |
| `FRAME_SAMPLE_FPS` | `1` | Fallback sample rate when duration is unavailable |
| `MAX_FRAMES` | `24` | Fallback frame cap for clips longer than 60 seconds |
| `FRAME_SCALE_WIDTH` | `384` | Downscale width during ffmpeg extraction |
| `LETTERBOX_SIZE` | `384` | Square canvas size after content crop + letterbox |
| `CONTENT_CROP_THRESHOLD` | `8` | Luminance threshold for trimming black borders |
| `DARK_FRAME_THRESHOLD` | `12` | Skip sampled frames with mean luminance below this |
| `FFMPEG_FRAME_QUALITY` | `2` | ffmpeg `-qscale:v` for extracted frames (lower is sharper) |
| `MIN_PDQ_QUALITY` | `50` | Skip low-quality PDQ hashes once enough frames are kept |
| `FRAME_SIMILARITY_THRESHOLD` | `0.75` | Minimum cosine similarity for DINOv2 frame pairs |
| `MIN_ALIGNED_FRAMES` | `2` | Minimum temporally aligned frames required |
| `FINGERPRINT_TIMEOUT_SECONDS` | `600` | Max seconds to wait for background fingerprinting |
| `PRELOAD_DINOV2` | `false` | Warm-load DINOv2 on startup when using `dinov2` |
| `TORCH_NUM_THREADS` | `2` | CPU threads used by PyTorch when using `dinov2` |

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

For DINOv2 matching locally:

```bash
pip install -r requirements-dinov2.txt
export FINGERPRINT_METHOD=dinov2
export PRELOAD_DINOV2=true
uvicorn app.main:app --reload
```

## Deploy to Render

1. Push this repo to GitHub.
2. Create a **Web Service** on [render.com](https://render.com) connected to the repo.
3. Use the included `render.yaml` Blueprint, or set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Python version:** `3.12.8` via `PYTHON_VERSION` env var or `.python-version`
   - **Fingerprint method:** `FINGERPRINT_METHOD=vpdq` (set in `render.yaml`)

No other environment variables are required for the default vPDQ deployment.

## Notes

- Only `.mp4` files are accepted.
- `video_id` is an 8-digit ID derived from the file content (CRC32).
- Videos, metadata, and frame fingerprints are kept in memory only and are lost on redeploy or restart.
- Default fingerprinting uses **vPDQ/PDQ** via `threatengine` (no PyTorch on Render).
- Set `FINGERPRINT_METHOD=dinov2` for neural embeddings when running locally with PyTorch installed.

## Architecture

```text
upload → store video + metadata → return response
       → background task → sample frames → PDQ/vPDQ fingerprints
GET /match → if any video still fingerprinting: HTTP 202
            → if ready: cross-bucket candidates → alignment → ranked confidence scores
```

DINOv2 remains available via `FINGERPRINT_METHOD=dinov2` for higher-accuracy offline use.
