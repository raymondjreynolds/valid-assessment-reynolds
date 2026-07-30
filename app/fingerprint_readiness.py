from app.config import FINGERPRINT_TIMEOUT_SECONDS, monotonic_now
from app.fingerprint_status import FingerprintStatus
from app.storage import StoredVideo, VideoStore


class FingerprintNotReadyError(Exception):
    def __init__(self, video_id: str, status: FingerprintStatus, message: str) -> None:
        self.video_id = video_id
        self.status = status
        self.message = message
        super().__init__(message)


def _elapsed_seconds(video: StoredVideo) -> float:
    if video.fingerprint_started_at is None:
        return 0.0
    return monotonic_now() - video.fingerprint_started_at


def ensure_fingerprint_ready(video: StoredVideo, store: VideoStore) -> None:
    if video.fingerprint_status.is_ready():
        return

    if video.fingerprint_status is FingerprintStatus.FAILED:
        raise FingerprintNotReadyError(
            video.video_id,
            video.fingerprint_status,
            video.fingerprint_error or "Fingerprinting failed",
        )

    if video.fingerprint_status.is_in_progress():
        elapsed = _elapsed_seconds(video)
        if elapsed > FINGERPRINT_TIMEOUT_SECONDS:
            store.set_fingerprint_status(
                video.video_id,
                FingerprintStatus.TIMED_OUT,
                error="Fingerprinting timed out",
            )
            raise FingerprintNotReadyError(
                video.video_id,
                FingerprintStatus.TIMED_OUT,
                f"Fingerprinting timed out after {FINGERPRINT_TIMEOUT_SECONDS} seconds",
            )

        raise FingerprintNotReadyError(
            video.video_id,
            video.fingerprint_status,
            f"Fingerprints are still being computed for video {video.video_id}",
        )

    if video.fingerprint_status is FingerprintStatus.TIMED_OUT:
        raise FingerprintNotReadyError(
            video.video_id,
            video.fingerprint_status,
            video.fingerprint_error or "Fingerprinting timed out",
        )
