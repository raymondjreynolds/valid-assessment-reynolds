"""Meta PDQ (vPDQ-style) frame fingerprinting."""

import tempfile
from pathlib import Path

import threatengine

from app.config import MIN_PDQ_QUALITY
from app.fingerprints.base import FrameFingerprint
from app.frames import MIN_SAMPLE_FRAMES, SampledFrame


class VPDQFingerprinter:
    """Hash sampled frames with Meta PDQ for fast vPDQ-style matching."""

    def fingerprint(self, frames: list[SampledFrame]) -> list[FrameFingerprint]:
        """Hash each sampled frame and skip low-quality PDQ outputs when possible."""
        if not frames:
            return []

        results: list[FrameFingerprint] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, frame in enumerate(frames):
                frame_path = Path(temp_dir) / f"frame_{index:04d}.jpg"
                frame.image.save(frame_path, "JPEG", quality=90)
                hash_hex, quality = threatengine.pdq_hash_file(str(frame_path))
                if quality < MIN_PDQ_QUALITY and len(results) >= MIN_SAMPLE_FRAMES:
                    continue
                results.append(
                    FrameFingerprint(
                        timestamp=frame.timestamp,
                        vpdq=hash_hex,
                    )
                )

        return results
