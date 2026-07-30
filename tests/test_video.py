import struct

from app.video import (
    compute_aspect_ratio,
    compute_ratio_bucket,
    extract_video_metadata,
    generate_video_id,
)


def _build_minimal_mp4(width: int, height: int) -> bytes:
    def box(box_type: bytes, content: bytes) -> bytes:
        return struct.pack(">I", 8 + len(content)) + box_type + content

    tkhd_content = bytearray(84)
    tkhd_content[0] = 0
    struct.pack_into(">I", tkhd_content, 76, width << 16)
    struct.pack_into(">I", tkhd_content, 80, height << 16)

    hdlr_content = bytearray(24)
    hdlr_content[8:12] = b"vide"

    mdia = box(b"mdia", box(b"hdlr", bytes(hdlr_content)))
    trak = box(b"trak", box(b"tkhd", bytes(tkhd_content)) + mdia)
    moov = box(b"moov", trak)
    ftyp = box(b"ftyp", b"isom" + b"\x00" * 4 + b"isom")
    return ftyp + moov


def test_aspect_ratio_standard_buckets():
    assert compute_aspect_ratio(576, 1024) == "9:16"
    assert compute_aspect_ratio(576, 576) == "1:1"
    assert compute_aspect_ratio(1080, 1350) == "4:5"
    assert compute_aspect_ratio(1280, 720) == "16:9"
    assert compute_aspect_ratio(1470, 630) == "7:3"


def test_ratio_bucket():
    assert compute_ratio_bucket(576, 1024) == "9:16"
    assert compute_ratio_bucket(576, 576) == "1:1"
    assert compute_ratio_bucket(1080, 1350) == "4:5"
    assert compute_ratio_bucket(1280, 720) == "16:9"
    assert compute_ratio_bucket(1470, 630) == "Other"


def test_aspect_ratio_and_bucket_from_spec_examples():
    examples = [
        (576, 1024, "9:16", "9:16"),
        (576, 576, "1:1", "1:1"),
        (1080, 1350, "4:5", "4:5"),
        (1280, 720, "16:9", "16:9"),
        (1470, 630, "7:3", "Other"),
    ]
    for width, height, expected_ratio, expected_bucket in examples:
        assert compute_aspect_ratio(width, height) == expected_ratio
        assert compute_ratio_bucket(width, height) == expected_bucket


def test_ratio_bucket_within_one_percent_tolerance():
    # 1080x1910 ≈ 9:16 within 1%, but reduced ratio is not exactly 9:16
    assert compute_aspect_ratio(1080, 1910) != "9:16"
    assert compute_ratio_bucket(1080, 1910) == "9:16"

    # 1000x1005 ≈ 1:1 within 1%
    assert compute_ratio_bucket(1000, 1005) == "1:1"


def test_ratio_bucket_outside_one_percent_tolerance():
    # Just outside ±1% of 9:16
    assert compute_ratio_bucket(1080, 1900) == "Other"

    # 7:3 ultrawide remains Other
    assert compute_ratio_bucket(1470, 630) == "Other"


def test_video_id_is_eight_digits():
    video_id = generate_video_id(b"sample video content")
    assert len(video_id) == 8
    assert video_id.isdigit()


def test_extract_video_metadata_from_mp4():
    content = _build_minimal_mp4(1280, 720)
    assert extract_video_metadata(content) == (1280, 720)
