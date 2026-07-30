import os
import time

FRAME_SAMPLE_FPS = float(os.environ.get("FRAME_SAMPLE_FPS", "0.5"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "12"))
FRAME_SCALE_WIDTH = int(os.environ.get("FRAME_SCALE_WIDTH", "256"))
CENTER_CROP_FRACTION = float(os.environ.get("CENTER_CROP_FRACTION", "0.85"))
MATCH_CONFIDENCE_THRESHOLD = float(os.environ.get("MATCH_CONFIDENCE_THRESHOLD", "0.5"))
FRAME_SIMILARITY_THRESHOLD = float(os.environ.get("FRAME_SIMILARITY_THRESHOLD", "0.75"))
MIN_ALIGNED_FRAMES = int(os.environ.get("MIN_ALIGNED_FRAMES", "3"))
FINGERPRINT_TIMEOUT_SECONDS = int(os.environ.get("FINGERPRINT_TIMEOUT_SECONDS", "600"))
TORCH_NUM_THREADS = int(os.environ.get("TORCH_NUM_THREADS", "2"))
PRELOAD_DINOV2 = os.environ.get("PRELOAD_DINOV2", "true").lower() in {"1", "true", "yes"}


def monotonic_now() -> float:
    return time.monotonic()
