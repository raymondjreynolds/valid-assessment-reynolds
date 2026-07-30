from __future__ import annotations

from typing import TYPE_CHECKING

from app.fingerprints.base import FrameFingerprint, VideoFingerprinter
from app.frames import SampledFrame

if TYPE_CHECKING:
    from app.storage import StoredVideo


class VPDQFingerprinter:
    """Placeholder for future vPDQ frame hashing at upload time."""

    def fingerprint(self, frames: list[SampledFrame]) -> list[str | None]:
        return [None for _ in frames]


class VPDQPrefilter:
    """Placeholder for future vPDQ candidate pre-filtering before DINOv2 scoring."""

    def prefilter(
        self,
        query: StoredVideo,
        candidates: list[StoredVideo],
        *,
        top_k: int = 20,
    ) -> list[StoredVideo]:
        raise NotImplementedError("vPDQ prefilter is not implemented yet")


def attach_vpdq_hashes(
    frame_fingerprints: list[FrameFingerprint],
    vpdq_hashes: list[str | None],
) -> list[FrameFingerprint]:
    return [
        FrameFingerprint(
            timestamp=frame.timestamp,
            dinov2=frame.dinov2,
            vpdq=vpdq_hash,
        )
        for frame, vpdq_hash in zip(frame_fingerprints, vpdq_hashes, strict=True)
    ]


def get_vpdq_fingerprinter() -> VideoFingerprinter | None:
    return None
