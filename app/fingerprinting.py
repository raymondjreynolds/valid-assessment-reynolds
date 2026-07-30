from app.config import FINGERPRINT_METHOD
from app.fingerprints.base import FingerprintSet, VideoFingerprinter
from app.fingerprints.vpdq import VPDQFingerprinter
from app.frames import sample_frames
from app.storage import StoredVideo


def get_fingerprinter(method: str | None = None) -> VideoFingerprinter:
    selected = (method or FINGERPRINT_METHOD).lower()
    if selected == "vpdq":
        return VPDQFingerprinter()
    if selected == "dinov2":
        from app.fingerprints.dinov2 import DINOv2Fingerprinter

        return DINOv2Fingerprinter()
    raise ValueError(f"Unsupported fingerprint method: {selected}")


def build_fingerprints(
    content: bytes,
    method: str | None = None,
    fingerprinter: VideoFingerprinter | None = None,
) -> FingerprintSet:
    selected = (method or FINGERPRINT_METHOD).lower()
    fingerprinter = fingerprinter or get_fingerprinter(selected)
    frames = sample_frames(content)
    return FingerprintSet(
        method=selected,
        frames=fingerprinter.fingerprint(frames),
    )


def fingerprint_video(
    video: StoredVideo,
    method: str | None = None,
    fingerprinter: VideoFingerprinter | None = None,
) -> StoredVideo:
    fingerprints = build_fingerprints(
        video.content,
        method=method,
        fingerprinter=fingerprinter,
    )
    return StoredVideo(
        video_id=video.video_id,
        filename=video.filename,
        width=video.width,
        height=video.height,
        aspect_ratio=video.aspect_ratio,
        ratio_bucket=video.ratio_bucket,
        content=video.content,
        fingerprints=fingerprints,
        fingerprint_method=fingerprints.method,
        fingerprint_status=video.fingerprint_status,
        fingerprint_started_at=video.fingerprint_started_at,
        fingerprint_error=video.fingerprint_error,
    )
