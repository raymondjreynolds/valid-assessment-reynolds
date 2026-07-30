import struct


def build_minimal_mp4(
    width: int,
    height: int,
    duration_seconds: float = 10.0,
    timescale: int = 1000,
) -> bytes:
    def box(box_type: bytes, content: bytes) -> bytes:
        return struct.pack(">I", 8 + len(content)) + box_type + content

    mvhd_content = bytearray(100)
    duration_ticks = int(duration_seconds * timescale)
    struct.pack_into(">I", mvhd_content, 12, timescale)
    struct.pack_into(">I", mvhd_content, 16, duration_ticks)

    tkhd_content = bytearray(84)
    tkhd_content[0] = 0
    struct.pack_into(">I", tkhd_content, 76, width << 16)
    struct.pack_into(">I", tkhd_content, 80, height << 16)

    hdlr_content = bytearray(24)
    hdlr_content[8:12] = b"vide"

    mdia = box(b"mdia", box(b"hdlr", bytes(hdlr_content)))
    trak = box(b"trak", box(b"tkhd", bytes(tkhd_content)) + mdia)
    moov = box(b"moov", box(b"mvhd", bytes(mvhd_content)) + trak)
    ftyp = box(b"ftyp", b"isom" + b"\x00" * 4 + b"isom")
    return ftyp + moov
