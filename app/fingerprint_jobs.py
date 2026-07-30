"""Background fingerprint job scheduling and execution."""

from concurrent.futures import ThreadPoolExecutor

from app.config import monotonic_now
from app.fingerprinting import build_fingerprints
from app.fingerprint_status import FingerprintStatus
from app.storage import VideoStore

# Single worker avoids overlapping ffmpeg/torch work on constrained hosts.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fingerprint")


def run_fingerprint_job(video_id: str, store: VideoStore) -> None:
    """Extract frames and compute fingerprints for one stored video.

    Ignores stale jobs when the video was deleted, timed out, failed, or
    superseded by a newer retry attempt.
    """
    video = store.get(video_id)
    if video is None:
        return
    # Do not resurrect TIMED_OUT/FAILED entries or run superseded attempts.
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

    # Refuse to overwrite terminal states or a newer retry attempt.
    store.update_fingerprints(
        video_id,
        fingerprints,
        status=FingerprintStatus.READY,
        expected_attempt=attempt,
    )


def schedule_fingerprint_job(video_id: str, store: VideoStore) -> None:
    """Queue a fingerprint job on the background executor."""
    _executor.submit(run_fingerprint_job, video_id, store)


def shutdown_fingerprint_executor() -> None:
    """Stop accepting new jobs during application shutdown."""
    _executor.shutdown(wait=False, cancel_futures=True)
