"""Fingerprint lifecycle states for background processing."""

from enum import Enum


class FingerprintStatus(str, Enum):
    """Status of background fingerprint computation for one video."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    TIMED_OUT = "timed_out"

    def is_ready(self) -> bool:
        """True when fingerprints are available for matching."""
        return self is FingerprintStatus.READY

    def is_in_progress(self) -> bool:
        """True while a job is queued or actively running."""
        return self in {FingerprintStatus.PENDING, FingerprintStatus.PROCESSING}
