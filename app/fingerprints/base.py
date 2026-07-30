"""Shared fingerprint data structures."""

from dataclasses import dataclass, field
from typing import Protocol

from app.frames import SampledFrame


@dataclass
class FrameFingerprint:
    """Per-frame features used for temporal alignment and scoring."""

    timestamp: float
    dinov2: list[float] | None = None
    vpdq: str | None = None


class VideoFingerprinter(Protocol):
    """Compute per-frame fingerprints for sampled video frames."""

    def fingerprint(self, frames: list[SampledFrame]) -> list[FrameFingerprint]:
        ...


@dataclass
class FingerprintSet:
    """All frame fingerprints for one video."""

    method: str = "vpdq"
    frames: list[FrameFingerprint] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when no frame fingerprints were produced."""
        return not self.frames
