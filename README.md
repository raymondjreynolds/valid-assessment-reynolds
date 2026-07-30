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

Matching is **cross-bucket only**: a query never matches videos in its own `ratio_bucket`. Videos in the **`Other`** bucket are excluded from matching entirely (as query or candidate). Uploads return immediately; fingerprinting runs in a background task. Default method is **ONNX CLIP**; set `FINGERPRINT_METHOD=vpdq` or `FINGERPRINT_METHOD=dinov2` for alternatives.

`/match` returns **HTTP 202** until **all** uploaded videos have finished fingerprinting:

```json
{
  "status": "processing",
  "message": "Fingerprints are still being computed"
}
```

If fingerprinting fails or exceeds the timeout, the API returns **HTTP 503** with `status` of `failed` or `timed_out`.

#### Expected confidence scores

Confidence is computed as `matched_frame_ratio × mean_frame_similarity` (0–1). For **cross-bucket reframed UGC** with vPDQ, **0.5–0.7 is normal** for true matches; identical pixel-level clips would score near 1.0 but are excluded by the cross-bucket rule. Rank order matters more than the absolute value—unrelated videos should score lower than reframed versions of the same creative.

Sampling is **length-aware**: frame rate and cap adjust to each video's duration (see table below). More frames improves temporal coverage but does **not** guarantee higher scores. For higher legitimate scores on reframed content, use **`FINGERPRINT_METHOD=onnx`** (Render-friendly) or **`FINGERPRINT_METHOD=dinov2`** locally.

| Duration | Sample rate | Max frames |
|----------|-------------|------------|
| ≤15s | 1 fps | 12 |
| ≤30s | 1 fps | 16 |
| ≤60s | 0.5 fps | 20 |
| >60s | 0.5 fps | 24 |

Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FINGERPRINT_METHOD` | `onnx` | `onnx` (default CLIP), `vpdq`, or `dinov2` (PyTorch, local) |
| `ONNX_MODEL` | `clip` | `clip` (default) or `mobilenet` when using `onnx` |
| `ONNX_MODEL_CACHE` | `.cache/onnx` | Directory for downloaded ONNX model files |
| `ONNX_BATCH_SIZE` | `4` | Frames per ONNX inference batch |
| `PRELOAD_ONNX` | `false` | Warm-load ONNX model on startup (disable on Render free tier) |
| `RELEASE_VIDEO_CONTENT_AFTER_FINGERPRINT` | `true` | Drop MP4 bytes from memory after fingerprinting completes |
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

For ONNX embeddings (default, included in `requirements.txt`):

```bash
uvicorn app.main:app --reload
```

Optional overrides:

```bash
export FINGERPRINT_METHOD=onnx
export ONNX_MODEL=clip
export PRELOAD_ONNX=true
uvicorn app.main:app --reload
```

The CLIP ONNX model is downloaded on first use into `ONNX_MODEL_CACHE` (~300 MB on disk, ~350+ MB RAM when loaded). **CLIP does not fit Render's free tier (512 MB)** alongside Python and uploaded videos. On Render, use `ONNX_MODEL=mobilenet` (configured in `render.yaml`) or upgrade the instance memory. Use `ONNX_MODEL=clip` locally or on larger instances.

#### Memory on Render free tier

| Component | Approx. RAM |
|-----------|-------------|
| Python + FastAPI + onnxruntime | ~120 MB |
| ONNX CLIP loaded | ~350+ MB |
| ONNX MobileNet loaded | ~50–80 MB |
| Each uploaded MP4 (until fingerprinted) | file size |

Mitigations enabled for Render: `ONNX_MODEL=mobilenet`, `PRELOAD_ONNX=false`, `ONNX_BATCH_SIZE=1`, `RELEASE_VIDEO_CONTENT_AFTER_FINGERPRINT=true`, and 256px frame processing. Set `FINGERPRINT_METHOD=vpdq` for the lowest memory footprint.

## Deploy to Render

1. Push this repo to GitHub.
2. Create a **Web Service** on [render.com](https://render.com) connected to the repo.
3. Use the included `render.yaml` Blueprint, or set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Python version:** `3.12.8` via `PYTHON_VERSION` env var or `.python-version`
   - **Fingerprint method:** `FINGERPRINT_METHOD=onnx` with `ONNX_MODEL=mobilenet` on free tier (see `render.yaml`)

No other environment variables are required for the default Render deployment.

## Notes

- Only `.mp4` files are accepted.
- `video_id` is an 8-digit ID derived from the file content (CRC32).
- Videos, metadata, and frame fingerprints are kept in memory only and are lost on redeploy or restart.
- Default fingerprinting uses **ONNX CLIP** via `onnxruntime` (model cached after first download).
- Set `FINGERPRINT_METHOD=vpdq` for PDQ hashing or `FINGERPRINT_METHOD=dinov2` for PyTorch locally.

## Architecture

```text
upload → store video + metadata → return response
       → background task → sample frames → ONNX CLIP / vPDQ fingerprints
GET /match → if any video still fingerprinting: HTTP 202
            → if ready: cross-bucket candidates → alignment → ranked confidence scores
```

DINOv2 remains available via `FINGERPRINT_METHOD=dinov2` for higher-accuracy offline use.
