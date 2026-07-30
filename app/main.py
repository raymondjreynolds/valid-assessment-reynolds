from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.storage import StoredVideo, VideoStore
from app.video import (
    compute_aspect_ratio,
    compute_ratio_bucket,
    extract_video_metadata,
    generate_video_id,
)

app = FastAPI(title="Valid Assessment Video API", version="1.0.0")
store = VideoStore()


class UploadResponseItem(BaseModel):
    video_id: str
    width: int
    height: int
    aspect_ratio: str
    ratio_bucket: str
    filename: str


class SignedUrlResponse(BaseModel):
    video_id: str
    url: str
    expires_in_seconds: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload", response_model=list[UploadResponseItem])
async def upload_videos(
    files: list[UploadFile] = File(...),
) -> list[UploadResponseItem]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results: list[UploadResponseItem] = []

    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".mp4"):
            raise HTTPException(
                status_code=400,
                detail=f"Only MP4 files are accepted: {upload.filename or 'unknown'}",
            )

        content = await upload.read()
        if not content:
            raise HTTPException(
                status_code=400,
                detail=f"Empty file: {upload.filename}",
            )

        try:
            width, height = extract_video_metadata(content)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video file {upload.filename}: {exc}",
            ) from exc

        aspect_ratio = compute_aspect_ratio(width, height)
        ratio_bucket = compute_ratio_bucket(aspect_ratio)
        video_id = generate_video_id(content)

        video = StoredVideo(
            video_id=video_id,
            gcs_blob_name=f"videos/{video_id}.mp4",
            filename=upload.filename,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            ratio_bucket=ratio_bucket,
        )

        try:
            store.upload(video, content)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        results.append(
            UploadResponseItem(
                video_id=video_id,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                ratio_bucket=ratio_bucket,
                filename=upload.filename,
            )
        )

    return results


@app.get("/videos/{video_id}/url", response_model=SignedUrlResponse)
def get_video_signed_url(video_id: str) -> SignedUrlResponse:
    from app.config import SIGNED_URL_EXPIRATION_SECONDS

    try:
        url = store.generate_signed_url(video_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SignedUrlResponse(
        video_id=video_id,
        url=url,
        expires_in_seconds=SIGNED_URL_EXPIRATION_SECONDS,
    )


@app.get("/videos/{video_id}")
def serve_video(video_id: str) -> RedirectResponse:
    """Redirect to a short-lived GCS V4 signed URL."""
    try:
        url = store.generate_signed_url(video_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RedirectResponse(url=url, status_code=302)
