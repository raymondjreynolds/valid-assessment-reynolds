import tempfile
from pathlib import Path

import threatengine

from app.fingerprints.base import FrameFingerprint
from app.frames import SampledFrame


class VPDQFingerprinter:
    """Hash sampled frames with Meta PDQ for fast vPDQ-style matching."""

    def fingerprint(self, frames: list[SampledFrame]) -> list[FrameFingerprint]:
        if not frames:
            return []

        results: list[FrameFingerprint] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, frame in enumerate(frames):
                frame_path = Path(temp_dir) / f"frame_{index:04d}.jpg"
                frame.image.save(frame_path, "JPEG", quality=85)
                hash_hex, _quality = threatengine.pdq_hash_file(str(frame_path))
                results.append(
                    FrameFingerprint(
                        timestamp=frame.timestamp,
                        vpdq=hash_hex,
                    )
                )

        return results
