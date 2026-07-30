import io
import math
import zlib
from fractions import Fraction

import av

STANDARD_RATIO_BUCKETS = ("9:16", "1:1", "4:5", "16:9")


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def compute_aspect_ratio(width: int, height: int) -> str:
    divisor = _gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def compute_ratio_bucket(aspect_ratio: str) -> str:
    if aspect_ratio in STANDARD_RATIO_BUCKETS:
        return aspect_ratio
    return "Other"


def generate_video_id(content: bytes) -> str:
    return f"{zlib.crc32(content) % 100_000_000:08d}"


def extract_video_metadata(content: bytes) -> tuple[int, int]:
    with av.open(io.BytesIO(content)) as container:
        video_stream = next(
            (s for s in container.streams if s.type == "video"), None
        )
        if video_stream is None:
            raise ValueError("No video stream found in file")

        width = video_stream.width
        height = video_stream.height

        if width is None or height is None:
            raise ValueError("Could not determine video dimensions")

        # Some codecs store display aspect ratio separately from coded size.
        if video_stream.sample_aspect_ratio is not None:
            sar = float(Fraction(video_stream.sample_aspect_ratio))
            if not math.isclose(sar, 1.0):
                width = int(round(width * sar))

        return width, height
