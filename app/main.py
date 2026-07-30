from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
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

        store.store(
            StoredVideo(
                video_id=video_id,
                filename=upload.filename,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                ratio_bucket=ratio_bucket,
                content=content,
            )
        )

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


@app.get("/videos/{video_id}")
def serve_video(video_id: str) -> Response:
    video = store.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    return Response(
        content=video.content,
        media_type="video/mp4",
        headers={"Content-Disposition": f'inline; filename="{video.filename}"'},
    )
