from dataclasses import dataclass, field
from typing import Protocol

from app.frames import SampledFrame


@dataclass
class FrameFingerprint:
    timestamp: float
    dinov2: list[float] | None = None
    vpdq: str | None = None


class VideoFingerprinter(Protocol):
    def fingerprint(self, frames: list[SampledFrame]) -> list[FrameFingerprint]:
        """Compute per-frame fingerprints for sampled video frames."""


@dataclass
class FingerprintSet:
    method: str = "onnx"
    frames: list[FrameFingerprint] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.frames
