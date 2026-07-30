from app.config import monotonic_now
from app.fingerprinting import build_fingerprints
from app.fingerprint_status import FingerprintStatus
from app.storage import VideoStore


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
        fingerprints = build_fingerprints(video.content)
    except Exception as exc:
        store.set_fingerprint_status(
            video_id,
            FingerprintStatus.FAILED,
            error=str(exc),
        )
        return

    store.update_fingerprints(video_id, fingerprints, status=FingerprintStatus.READY)


def schedule_fingerprint_job(video_id: str, store: VideoStore) -> None:
    run_fingerprint_job(video_id, store)
