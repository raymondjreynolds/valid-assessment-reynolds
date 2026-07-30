import struct
import zlib

RATIO_BUCKET_TARGETS = {
    "9:16": 9 / 16,
    "1:1": 1.0,
    "4:5": 4 / 5,
    "16:9": 16 / 9,
}
CANONICAL_RATIO_BUCKETS = frozenset(RATIO_BUCKET_TARGETS)
RATIO_BUCKET_TOLERANCE = 0.01  # ±1%

_CONTAINER_BOXES = frozenset(
    {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf"}
)


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def compute_aspect_ratio(width: int, height: int) -> str:
    divisor = _gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def compute_ratio_bucket(width: int, height: int) -> str:
    ratio = width / height
    for bucket, target in RATIO_BUCKET_TARGETS.items():
        if abs(ratio - target) / target <= RATIO_BUCKET_TOLERANCE:
            return bucket
    return "Other"


def is_canonical_ratio_filter(ratio: str) -> bool:
    return ratio in CANONICAL_RATIO_BUCKETS


def is_matchable_ratio_bucket(ratio_bucket: str) -> bool:
    return ratio_bucket in CANONICAL_RATIO_BUCKETS


def generate_video_id(content: bytes) -> str:
    return f"{zlib.crc32(content) % 100_000_000:08d}"


def is_valid_video_id(video_id: str) -> bool:
    return len(video_id) == 8 and video_id.isdigit()


def _read_box_header(data: bytes, offset: int, end: int) -> tuple[int, bytes, int] | None:
    if offset + 8 > end:
        return None

    size = struct.unpack_from(">I", data, offset)[0]
    box_type = data[offset + 4 : offset + 8]
    header_size = 8

    if size == 1:
        if offset + 16 > end:
            return None
        size = struct.unpack_from(">Q", data, offset + 8)[0]
        header_size = 16
    elif size == 0:
        size = end - offset

    if size < header_size or offset + size > end:
        return None

    return size, box_type, header_size


def _parse_tkhd(data: bytes, content_start: int) -> tuple[int, int]:
    version = data[content_start]
    if version == 0:
        width_offset = content_start + 76
        height_offset = content_start + 80
    elif version == 1:
        width_offset = content_start + 88
        height_offset = content_start + 92
    else:
        raise ValueError(f"Unsupported tkhd version: {version}")

    width = struct.unpack_from(">I", data, width_offset)[0] >> 16
    height = struct.unpack_from(">I", data, height_offset)[0] >> 16

    if width <= 0 or height <= 0:
        raise ValueError("Invalid video dimensions in tkhd box")

    return width, height


def _find_box(
    data: bytes, start: int, end: int, target: bytes
) -> tuple[int, int] | None:
    offset = start
    while offset < end:
        header = _read_box_header(data, offset, end)
        if header is None:
            break

        size, box_type, header_size = header
        content_start = offset + header_size
        box_end = offset + size

        if box_type == target:
            return content_start, box_end

        if box_type in _CONTAINER_BOXES:
            found = _find_box(data, content_start, box_end, target)
            if found is not None:
                return found

        offset = box_end

    return None


def _trak_is_video(data: bytes, trak_start: int, trak_end: int) -> bool:
    hdlr = _find_box(data, trak_start, trak_end, b"hdlr")
    if hdlr is None:
        return False

    content_start, _ = hdlr
    if content_start + 12 > len(data):
        return False

    handler_type = data[content_start + 8 : content_start + 12]
    return handler_type == b"vide"


def _find_video_dimensions(data: bytes) -> tuple[int, int]:
    offset = 0
    end = len(data)

    while offset < end:
        header = _read_box_header(data, offset, end)
        if header is None:
            break

        size, box_type, header_size = header
        content_start = offset + header_size
        box_end = offset + size

        if box_type == b"moov":
            trak_offset = content_start
            while trak_offset < box_end:
                trak_header = _read_box_header(data, trak_offset, box_end)
                if trak_header is None:
                    break

                trak_size, trak_type, trak_header_size = trak_header
                trak_content = trak_offset + trak_header_size
                trak_end = trak_offset + trak_size

                if trak_type == b"trak" and _trak_is_video(data, trak_content, trak_end):
                    tkhd = _find_box(data, trak_content, trak_end, b"tkhd")
                    if tkhd is None:
                        raise ValueError("Video track is missing tkhd box")

                    tkhd_start, _ = tkhd
                    return _parse_tkhd(data, tkhd_start)

                trak_offset = trak_end

        offset = box_end

    raise ValueError("No video stream found in file")


def _parse_mvhd(data: bytes, content_start: int) -> float:
    version = data[content_start]
    if version == 0:
        timescale = struct.unpack_from(">I", data, content_start + 12)[0]
        duration = struct.unpack_from(">I", data, content_start + 16)[0]
    elif version == 1:
        timescale = struct.unpack_from(">I", data, content_start + 20)[0]
        duration = struct.unpack_from(">Q", data, content_start + 24)[0]
    else:
        raise ValueError(f"Unsupported mvhd version: {version}")

    if timescale == 0:
        raise ValueError("Invalid mvhd timescale")

    return duration / timescale


def _find_movie_duration(data: bytes) -> float:
    offset = 0
    end = len(data)

    while offset < end:
        header = _read_box_header(data, offset, end)
        if header is None:
            break

        size, box_type, header_size = header
        content_start = offset + header_size
        box_end = offset + size

        if box_type == b"moov":
            mvhd = _find_box(data, content_start, box_end, b"mvhd")
            if mvhd is None:
                raise ValueError("moov is missing mvhd box")
            mvhd_start, _ = mvhd
            return _parse_mvhd(data, mvhd_start)

        offset = box_end

    raise ValueError("No moov box found in file")


def extract_video_duration(content: bytes) -> float:
    if len(content) < 8 or content[4:8] != b"ftyp":
        raise ValueError("File is not a valid MP4")

    return _find_movie_duration(content)


def extract_video_metadata(content: bytes) -> tuple[int, int, float]:
    if len(content) < 8 or content[4:8] != b"ftyp":
        raise ValueError("File is not a valid MP4")

    width, height = _find_video_dimensions(content)
    duration = _find_movie_duration(content)
    return width, height, duration
