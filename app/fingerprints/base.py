from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from app.frames import SampledFrame


@dataclass
class FrameFingerprint:
    timestamp: float
    dinov2: list[float] | None = None
    embedding: bytes | None = None
    vpdq: str | None = None


def frame_embedding_vector(frame: FrameFingerprint) -> np.ndarray | None:
    if frame.embedding is not None:
        return np.frombuffer(frame.embedding, dtype=np.float32)
    if frame.dinov2 is not None:
        return np.asarray(frame.dinov2, dtype=np.float32)
    return None


def has_frame_embedding(frame: FrameFingerprint) -> bool:
    return frame.embedding is not None or frame.dinov2 is not None


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
