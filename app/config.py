import os
import time

FINGERPRINT_METHOD = os.environ.get("FINGERPRINT_METHOD", "vpdq").lower()
FRAME_SAMPLE_FPS = float(os.environ.get("FRAME_SAMPLE_FPS", "0.5"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "12"))
FRAME_SCALE_WIDTH = int(os.environ.get("FRAME_SCALE_WIDTH", "256"))
LETTERBOX_SIZE = int(os.environ.get("LETTERBOX_SIZE", "256"))
FRAME_SIMILARITY_THRESHOLD = float(os.environ.get("FRAME_SIMILARITY_THRESHOLD", "0.75"))
MIN_ALIGNED_FRAMES = int(os.environ.get("MIN_ALIGNED_FRAMES", "2"))
VPDQ_HAMMING_THRESHOLD = int(os.environ.get("VPDQ_HAMMING_THRESHOLD", "45"))
FINGERPRINT_TIMEOUT_SECONDS = int(os.environ.get("FINGERPRINT_TIMEOUT_SECONDS", "600"))
TORCH_NUM_THREADS = int(os.environ.get("TORCH_NUM_THREADS", "2"))
PRELOAD_DINOV2 = os.environ.get("PRELOAD_DINOV2", "false").lower() in {"1", "true", "yes"}


def monotonic_now() -> float:
    return time.monotonic()
