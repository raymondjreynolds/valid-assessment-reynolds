"""Application configuration loaded from environment variables."""

import os
import time

# Fingerprinting
FINGERPRINT_METHOD = os.environ.get("FINGERPRINT_METHOD", "vpdq").lower()
FRAME_SAMPLE_FPS = float(os.environ.get("FRAME_SAMPLE_FPS", "1"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "24"))
FRAME_SCALE_WIDTH = int(os.environ.get("FRAME_SCALE_WIDTH", "384"))
LETTERBOX_SIZE = int(os.environ.get("LETTERBOX_SIZE", "384"))
CONTENT_CROP_THRESHOLD = int(os.environ.get("CONTENT_CROP_THRESHOLD", "8"))
DARK_FRAME_THRESHOLD = float(os.environ.get("DARK_FRAME_THRESHOLD", "12"))
FFMPEG_FRAME_QUALITY = int(os.environ.get("FFMPEG_FRAME_QUALITY", "2"))
MIN_PDQ_QUALITY = int(os.environ.get("MIN_PDQ_QUALITY", "50"))

# Matching
FRAME_SIMILARITY_THRESHOLD = float(os.environ.get("FRAME_SIMILARITY_THRESHOLD", "0.75"))
MATCH_CONFIDENCE_THRESHOLD = float(os.environ.get("MATCH_CONFIDENCE_THRESHOLD", "0.5"))
MIN_ALIGNED_FRAMES = int(os.environ.get("MIN_ALIGNED_FRAMES", "2"))
VPDQ_HAMMING_THRESHOLD = int(os.environ.get("VPDQ_HAMMING_THRESHOLD", "50"))

# Fingerprint job lifecycle
FINGERPRINT_TIMEOUT_SECONDS = int(os.environ.get("FINGERPRINT_TIMEOUT_SECONDS", "600"))
FFMPEG_TIMEOUT_SECONDS = int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "120"))
FINGERPRINT_RETRY_COOLDOWN_SECONDS = int(
    os.environ.get("FINGERPRINT_RETRY_COOLDOWN_SECONDS", "60")
)
FINGERPRINT_MAX_RETRIES = int(os.environ.get("FINGERPRINT_MAX_RETRIES", "3"))

# Optional DINOv2 (local / PyTorch)
TORCH_NUM_THREADS = int(os.environ.get("TORCH_NUM_THREADS", "2"))
PRELOAD_DINOV2 = os.environ.get("PRELOAD_DINOV2", "false").lower() in {"1", "true", "yes"}


def monotonic_now() -> float:
    """Return a monotonic timestamp for timeouts and retry cooldowns."""
    return time.monotonic()
