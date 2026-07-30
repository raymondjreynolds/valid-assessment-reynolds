from app.fingerprints.base import FrameFingerprint, VideoFingerprinter

__all__ = ["DINOv2Fingerprinter", "FrameFingerprint", "VPDQFingerprinter", "VideoFingerprinter"]


def __getattr__(name: str):
    if name == "DINOv2Fingerprinter":
        from app.fingerprints.dinov2 import DINOv2Fingerprinter

        return DINOv2Fingerprinter
    if name == "VPDQFingerprinter":
        from app.fingerprints.vpdq import VPDQFingerprinter

        return VPDQFingerprinter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
