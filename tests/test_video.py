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
    assert compute_ratio_bucket("9:16") == "9:16"
    assert compute_ratio_bucket("1:1") == "1:1"
    assert compute_ratio_bucket("4:5") == "4:5"
    assert compute_ratio_bucket("16:9") == "16:9"
    assert compute_ratio_bucket("7:3") == "Other"


def test_video_id_is_eight_digits():
    video_id = generate_video_id(b"sample video content")
    assert len(video_id) == 8
    assert video_id.isdigit()


def test_extract_video_metadata_from_mp4():
    content = _build_minimal_mp4(1280, 720)
    assert extract_video_metadata(content) == (1280, 720)
