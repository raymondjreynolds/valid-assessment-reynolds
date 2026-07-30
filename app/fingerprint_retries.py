from app.config import (
    FINGERPRINT_MAX_RETRIES,
    FINGERPRINT_RETRY_COOLDOWN_SECONDS,
    monotonic_now,
)
from app.fingerprint_jobs import schedule_fingerprint_job
from app.fingerprint_status import FingerprintStatus
from app.storage import StoredVideo, VideoStore
from app.video import is_matchable_ratio_bucket


def can_retry_fingerprint(video: StoredVideo) -> bool:
    if video.fingerprint_attempt >= FINGERPRINT_MAX_RETRIES:
        return False
    if video.fingerprint_last_attempt_at is None:
        return True
    elapsed = monotonic_now() - video.fingerprint_last_attempt_at
    return elapsed >= FINGERPRINT_RETRY_COOLDOWN_SECONDS


def schedule_fingerprint_retry(
    video_id: str,
    store: VideoStore,
    *,
    force: bool = False,
) -> bool:
    video = store.get(video_id)
    if video is None:
        return False
    if video.fingerprint_status not in {
        FingerprintStatus.FAILED,
        FingerprintStatus.TIMED_OUT,
    }:
        return False
    if not force and not can_retry_fingerprint(video):
        return False
    if video.fingerprint_attempt >= FINGERPRINT_MAX_RETRIES:
        return False
    if not store.prepare_fingerprint_retry(video_id):
        return False
    schedule_fingerprint_job(video_id, store)
    return True


def maybe_retry_failed_candidates(query: StoredVideo, store: VideoStore) -> None:
    """Best-effort background retries for failed cross-bucket candidates."""
    for video in store.list_all():
        if video.video_id == query.video_id:
            continue
        if video.ratio_bucket == query.ratio_bucket:
            continue
        if not is_matchable_ratio_bucket(video.ratio_bucket):
            continue
        if video.fingerprint_status not in {
            FingerprintStatus.FAILED,
            FingerprintStatus.TIMED_OUT,
        }:
            continue
        schedule_fingerprint_retry(video.video_id, store)
