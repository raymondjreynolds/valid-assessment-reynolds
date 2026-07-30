import threading
from typing import Literal

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import FINGERPRINT_METHOD, PRELOAD_DINOV2, monotonic_now
from app.fingerprint_jobs import schedule_fingerprint_job, shutdown_fingerprint_executor
from app.fingerprint_readiness import FingerprintNotReadyError
from app.fingerprint_status import FingerprintStatus
from app.matching import MatchResult, VideoMatcher
from app.matching.matcher import default_matcher
from app.storage import StoredVideo, VideoStore
from app.video import (
    compute_aspect_ratio,
    compute_ratio_bucket,
    extract_video_metadata,
    generate_video_id,
    is_canonical_ratio_filter,
    is_valid_video_id,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if PRELOAD_DINOV2 and FINGERPRINT_METHOD == "dinov2":
        from app.fingerprints.dinov2 import preload_dinov2

        threading.Thread(target=preload_dinov2, daemon=True).start()
    yield
    shutdown_fingerprint_executor()


app = FastAPI(title="Valid Assessment Video API", version="1.0.0", lifespan=lifespan)
store = VideoStore()
matcher = default_matcher(store)


class UploadResponseItem(BaseModel):
    video_id: str
    width: int
    height: int
    aspect_ratio: str
    ratio_bucket: str
    filename: str


class DeleteResponse(BaseModel):
    deleted: str


class MatchResponseItem(BaseModel):
    video_id: str
    ratio_bucket: str
    confidence: float
    matched_frame_ratio: float
    alignment: str
    method: str


class MatchProcessingResponse(BaseModel):
    status: Literal["processing"]
    message: str


class MatchErrorResponse(BaseModel):
    status: Literal["failed", "timed_out"]
    message: str


def _to_response_item(video: StoredVideo) -> UploadResponseItem:
    return UploadResponseItem(
        video_id=video.video_id,
        width=video.width,
        height=video.height,
        aspect_ratio=video.aspect_ratio,
        ratio_bucket=video.ratio_bucket,
        filename=video.filename,
    )


def _to_match_response(match: MatchResult) -> MatchResponseItem:
    return MatchResponseItem(
        video_id=match.video_id,
        ratio_bucket=match.ratio_bucket,
        confidence=match.confidence,
        matched_frame_ratio=match.matched_frame_ratio,
        alignment=match.alignment,
        method=match.method,
    )


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
        ratio_bucket = compute_ratio_bucket(width, height)
        video_id = generate_video_id(content)

        video = StoredVideo(
            video_id=video_id,
            filename=upload.filename,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            ratio_bucket=ratio_bucket,
            content=content,
            fingerprint_status=FingerprintStatus.PENDING,
            fingerprint_started_at=monotonic_now(),
        )
        store.store(video)
        schedule_fingerprint_job(video_id, store)
        results.append(_to_response_item(video))

    return results


@app.get("/videos", response_model=list[UploadResponseItem])
def list_videos(
    ratio: str | None = Query(default=None, description="Filter by ratio bucket"),
) -> list[UploadResponseItem]:
    if ratio is not None and not is_canonical_ratio_filter(ratio):
        raise HTTPException(status_code=404, detail=f"Unknown ratio filter: {ratio}")

    videos = store.list_all()
    if ratio is not None:
        videos = [video for video in videos if video.ratio_bucket == ratio]

    return [_to_response_item(video) for video in videos]


@app.get(
    "/match",
    responses={
        200: {"model": list[MatchResponseItem]},
        202: {"model": MatchProcessingResponse},
        503: {"model": MatchErrorResponse},
    },
)
def match_videos(
    video_id: str = Query(..., description="Query video id"),
):
    if not is_valid_video_id(video_id):
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    try:
        matches = matcher.match(video_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FingerprintNotReadyError as exc:
        if exc.status.is_in_progress():
            payload = MatchProcessingResponse(
                status="processing",
                message=exc.message,
            )
            return JSONResponse(status_code=202, content=payload.model_dump())

        status = "timed_out" if exc.status is FingerprintStatus.TIMED_OUT else "failed"
        payload = MatchErrorResponse(
            status=status,
            message=exc.message,
        )
        return JSONResponse(status_code=503, content=payload.model_dump())

    return [_to_match_response(match) for match in matches]


@app.delete("/videos/{video_id}", response_model=DeleteResponse)
def delete_video(video_id: str) -> DeleteResponse:
    if not is_valid_video_id(video_id) or not store.delete(video_id):
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    return DeleteResponse(deleted=video_id)
