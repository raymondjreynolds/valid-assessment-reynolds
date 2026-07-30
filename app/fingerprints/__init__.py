from app.fingerprints.base import FrameFingerprint, VideoFingerprinter

__all__ = ["DINOv2Fingerprinter", "FrameFingerprint", "VideoFingerprinter"]


def __getattr__(name: str):
    if name == "DINOv2Fingerprinter":
        from app.fingerprints.dinov2 import DINOv2Fingerprinter

        return DINOv2Fingerprinter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
