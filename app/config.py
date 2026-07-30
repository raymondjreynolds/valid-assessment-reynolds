import os
import time

FRAME_SAMPLE_FPS = float(os.environ.get("FRAME_SAMPLE_FPS", "1.0"))
CENTER_CROP_FRACTION = float(os.environ.get("CENTER_CROP_FRACTION", "0.85"))
MATCH_CONFIDENCE_THRESHOLD = float(os.environ.get("MATCH_CONFIDENCE_THRESHOLD", "0.5"))
FRAME_SIMILARITY_THRESHOLD = float(os.environ.get("FRAME_SIMILARITY_THRESHOLD", "0.75"))
MIN_ALIGNED_FRAMES = int(os.environ.get("MIN_ALIGNED_FRAMES", "3"))
FINGERPRINT_TIMEOUT_SECONDS = int(os.environ.get("FINGERPRINT_TIMEOUT_SECONDS", "300"))


def monotonic_now() -> float:
    return time.monotonic()
