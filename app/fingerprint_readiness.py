"""Fingerprint readiness checks for match requests."""

from app.config import FINGERPRINT_TIMEOUT_SECONDS, monotonic_now
from app.fingerprint_retries import schedule_fingerprint_retry
from app.fingerprint_status import FingerprintStatus
from app.storage import StoredVideo, VideoStore

PROCESSING_MESSAGE = "Fingerprints are still being computed"


class FingerprintNotReadyError(Exception):
    """Raised when a match request cannot proceed yet."""

    def __init__(self, video_id: str, status: FingerprintStatus, message: str) -> None:
        self.video_id = video_id
        self.status = status
        self.message = message
        super().__init__(message)


def _elapsed_seconds(video: StoredVideo) -> float:
    """Seconds since the current fingerprint attempt started."""
    if video.fingerprint_started_at is None:
        return 0.0
    return monotonic_now() - video.fingerprint_started_at


def _check_video_fingerprint_ready(video: StoredVideo, store: VideoStore) -> None:
    """Validate one video's fingerprint state, scheduling retries when allowed."""
    if video.fingerprint_status.is_ready():
        return

    if video.fingerprint_status in {
        FingerprintStatus.FAILED,
        FingerprintStatus.TIMED_OUT,
    }:
        if schedule_fingerprint_retry(video.video_id, store):
            raise FingerprintNotReadyError(
                video.video_id,
                FingerprintStatus.PENDING,
                PROCESSING_MESSAGE,
            )
        raise FingerprintNotReadyError(
            video.video_id,
            video.fingerprint_status,
            video.fingerprint_error
            or (
                "Fingerprinting failed"
                if video.fingerprint_status is FingerprintStatus.FAILED
                else f"Fingerprinting timed out after {FINGERPRINT_TIMEOUT_SECONDS} seconds"
            ),
        )

    if video.fingerprint_status.is_in_progress():
        elapsed = _elapsed_seconds(video)
        if elapsed > FINGERPRINT_TIMEOUT_SECONDS:
            store.set_fingerprint_status(
                video.video_id,
                FingerprintStatus.TIMED_OUT,
                error="Fingerprinting timed out",
            )
            if schedule_fingerprint_retry(video.video_id, store):
                raise FingerprintNotReadyError(
                    video.video_id,
                    FingerprintStatus.PENDING,
                    PROCESSING_MESSAGE,
                )
            raise FingerprintNotReadyError(
                video.video_id,
                FingerprintStatus.TIMED_OUT,
                f"Fingerprinting timed out after {FINGERPRINT_TIMEOUT_SECONDS} seconds",
            )

        raise FingerprintNotReadyError(
            video.video_id,
            video.fingerprint_status,
            PROCESSING_MESSAGE,
        )


def ensure_query_fingerprint_ready(query: StoredVideo, store: VideoStore) -> None:
    """Ensure the query video is ready before scoring cross-bucket matches.

    Only the query video is gated. Unrelated pending or failed uploads do not
    block matching.
    """
    _check_video_fingerprint_ready(query, store)
