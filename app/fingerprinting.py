from app.fingerprints.base import FingerprintSet
from app.fingerprints.dinov2 import DINOv2Fingerprinter
from app.frames import sample_frames
from app.storage import StoredVideo


def build_fingerprints(content: bytes, fingerprinter: DINOv2Fingerprinter | None = None) -> FingerprintSet:
    fingerprinter = fingerprinter or DINOv2Fingerprinter()
    frames = sample_frames(content)
    return FingerprintSet(frames=fingerprinter.fingerprint(frames))


def fingerprint_video(video: StoredVideo, fingerprinter: DINOv2Fingerprinter | None = None) -> StoredVideo:
    fingerprints = build_fingerprints(video.content, fingerprinter=fingerprinter)
    return StoredVideo(
        video_id=video.video_id,
        filename=video.filename,
        width=video.width,
        height=video.height,
        aspect_ratio=video.aspect_ratio,
        ratio_bucket=video.ratio_bucket,
        content=video.content,
        fingerprints=fingerprints,
    )
