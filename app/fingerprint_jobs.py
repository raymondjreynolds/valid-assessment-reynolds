from concurrent.futures import ThreadPoolExecutor

from app.config import RELEASE_VIDEO_CONTENT_AFTER_FINGERPRINT, monotonic_now
from app.fingerprinting import build_fingerprints
from app.fingerprint_status import FingerprintStatus
from app.inference_runtime import release_inference_resources
from app.storage import VideoStore

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fingerprint")


def run_fingerprint_job(video_id: str, store: VideoStore) -> None:
    video = store.get(video_id)
    if video is None:
        return

    store.set_fingerprint_status(
        video_id,
        FingerprintStatus.PROCESSING,
        started_at=monotonic_now(),
    )

    try:
        fingerprints = build_fingerprints(
            video.content,
            duration_seconds=video.duration_seconds,
        )
        store.update_fingerprints(video_id, fingerprints, status=FingerprintStatus.READY)
    except Exception as exc:
        store.set_fingerprint_status(
            video_id,
            FingerprintStatus.FAILED,
            error=str(exc),
        )
    finally:
        if RELEASE_VIDEO_CONTENT_AFTER_FINGERPRINT:
            store.release_video_content(video_id)
        release_inference_resources()


def schedule_fingerprint_job(video_id: str, store: VideoStore) -> None:
    _executor.submit(run_fingerprint_job, video_id, store)


def shutdown_fingerprint_executor() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
