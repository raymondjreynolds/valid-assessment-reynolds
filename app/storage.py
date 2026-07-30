import threading
from dataclasses import dataclass, field

from app.config import monotonic_now
from app.fingerprint_status import FingerprintStatus
from app.fingerprints.base import FingerprintSet


@dataclass
class StoredVideo:
    video_id: str
    filename: str
    width: int
    height: int
    aspect_ratio: str
    ratio_bucket: str
    content: bytes
    fingerprints: FingerprintSet = field(default_factory=FingerprintSet)
    fingerprint_method: str = "vpdq"
    fingerprint_status: FingerprintStatus = FingerprintStatus.PENDING
    fingerprint_started_at: float | None = None
    fingerprint_last_attempt_at: float | None = None
    fingerprint_attempt: int = 0
    duration_seconds: float | None = None
    fingerprint_error: str | None = None


class VideoStore:
    """In-memory store for uploaded video files and metadata."""

    def __init__(self) -> None:
        self._videos: dict[str, StoredVideo] = {}
        self._lock = threading.Lock()

    def store(self, video: StoredVideo) -> None:
        with self._lock:
            self._videos[video.video_id] = video

    def get(self, video_id: str) -> StoredVideo | None:
        with self._lock:
            return self._videos.get(video_id)

    def delete(self, video_id: str) -> bool:
        with self._lock:
            if video_id not in self._videos:
                return False
            del self._videos[video_id]
            return True

    def list_all(self) -> list[StoredVideo]:
        with self._lock:
            return list(self._videos.values())

    def set_fingerprint_status(
        self,
        video_id: str,
        status: FingerprintStatus,
        *,
        started_at: float | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            video = self._videos.get(video_id)
            if video is None:
                return
            video.fingerprint_status = status
            if started_at is not None:
                video.fingerprint_started_at = started_at
            if error is not None:
                video.fingerprint_error = error
            if status is FingerprintStatus.READY:
                video.fingerprint_error = None

    def update_fingerprints(
        self,
        video_id: str,
        fingerprints: FingerprintSet,
        *,
        status: FingerprintStatus = FingerprintStatus.READY,
        expected_attempt: int | None = None,
    ) -> bool:
        with self._lock:
            video = self._videos.get(video_id)
            if video is None:
                return False
            if video.fingerprint_status in {
                FingerprintStatus.TIMED_OUT,
                FingerprintStatus.FAILED,
            }:
                return False
            if (
                expected_attempt is not None
                and video.fingerprint_attempt != expected_attempt
            ):
                return False
            video.fingerprints = fingerprints
            video.fingerprint_method = fingerprints.method
            video.fingerprint_status = status
            video.fingerprint_error = None
            return True

    def prepare_fingerprint_retry(self, video_id: str) -> bool:
        with self._lock:
            video = self._videos.get(video_id)
            if video is None:
                return False
            now = monotonic_now()
            video.fingerprint_attempt += 1
            video.fingerprint_last_attempt_at = now
            video.fingerprint_started_at = now
            video.fingerprint_status = FingerprintStatus.PENDING
            video.fingerprint_error = None
            return True

    def mark_fingerprint_started(self, video_id: str) -> None:
        with self._lock:
            video = self._videos.get(video_id)
            if video is None:
                return
            now = monotonic_now()
            video.fingerprint_status = FingerprintStatus.PENDING
            video.fingerprint_attempt = 1
            video.fingerprint_last_attempt_at = now
            video.fingerprint_started_at = now
            video.fingerprint_error = None
