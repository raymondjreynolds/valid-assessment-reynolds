from concurrent.futures import ThreadPoolExecutor

from app.config import monotonic_now
from app.fingerprinting import build_fingerprints
from app.fingerprint_status import FingerprintStatus
from app.storage import VideoStore

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fingerprint")


def run_fingerprint_job(video_id: str, store: VideoStore) -> None:
    video = store.get(video_id)
    if video is None:
        return
    if video.fingerprint_status not in {
        FingerprintStatus.PENDING,
        FingerprintStatus.PROCESSING,
    }:
        return

    attempt = video.fingerprint_attempt

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
    except Exception as exc:
        store.set_fingerprint_status(
            video_id,
            FingerprintStatus.FAILED,
            error=str(exc),
        )
        return

    store.update_fingerprints(
        video_id,
        fingerprints,
        status=FingerprintStatus.READY,
        expected_attempt=attempt,
    )


def schedule_fingerprint_job(video_id: str, store: VideoStore) -> None:
    _executor.submit(run_fingerprint_job, video_id, store)


def shutdown_fingerprint_executor() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
