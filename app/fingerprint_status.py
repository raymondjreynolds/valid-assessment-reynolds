from enum import Enum


class FingerprintStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    TIMED_OUT = "timed_out"

    def is_ready(self) -> bool:
        return self is FingerprintStatus.READY

    def is_in_progress(self) -> bool:
        return self in {FingerprintStatus.PENDING, FingerprintStatus.PROCESSING}
