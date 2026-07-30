# Valid Assessment Video API

Python API for receiving MP4 uploads, storing them in a private Google Cloud Storage bucket, and serving them via short-lived V4 signed URLs.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload one or more MP4 files (multipart `files` field) |
| `GET` | `/videos/{video_id}` | Redirect to a short-lived GCS signed URL |
| `GET` | `/videos/{video_id}/url` | Return signed URL as JSON |
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

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GCS_BUCKET_NAME=your-bucket
export GCS_CREDENTIALS_JSON='{"type":"service_account",...}'

uvicorn app.main:app --reload
```

## Deploy to Render

1. Push this repo to GitHub.
2. Create a **Web Service** on [render.com](https://render.com) connected to the repo.
3. Use the included `render.yaml` Blueprint, or set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `GCS_BUCKET_NAME` — your private GCS bucket name
   - `GCS_CREDENTIALS_JSON` — full service account JSON (single line). The service account needs **Storage Object Admin** on the bucket and must include a `private_key` for V4 signed URLs.

## GCS setup

1. Create a private GCS bucket.
2. Create a service account with **Storage Object Admin** on that bucket.
3. Download the JSON key and set it as `GCS_CREDENTIALS_JSON` on Render.

Videos are stored at `videos/{video_id}.mp4` in the bucket. Video metadata is kept in memory (no database).

## Notes

- Only `.mp4` files are accepted.
- `video_id` is an 8-digit ID derived from the file content (CRC32).
- Signed URLs expire after 15 minutes by default (`SIGNED_URL_EXPIRATION_SECONDS`).
