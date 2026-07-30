import tempfile

import threatengine
from PIL import Image

from app.fingerprints.base import FrameFingerprint
from app.matching.align_vpdq import align_vpdq_fingerprints


def _hash_solid_color(red: int, green: int, blue: int) -> str:
    image = Image.new("RGB", (224, 224), color=(red, green, blue))
    with tempfile.NamedTemporaryFile(suffix=".jpg") as handle:
        image.save(handle.name, "JPEG")
        hash_hex, _quality = threatengine.pdq_hash_file(handle.name)
        return hash_hex


def test_align_vpdq_detects_matching_hashes():
    shared_hash = _hash_solid_color(120, 80, 40)
    query = [
        FrameFingerprint(timestamp=0.0, vpdq=shared_hash),
        FrameFingerprint(timestamp=1.0, vpdq=shared_hash),
        FrameFingerprint(timestamp=2.0, vpdq=shared_hash),
        FrameFingerprint(timestamp=3.0, vpdq=shared_hash),
    ]
    candidate = [
        FrameFingerprint(timestamp=0.5, vpdq=shared_hash),
        FrameFingerprint(timestamp=1.5, vpdq=shared_hash),
        FrameFingerprint(timestamp=2.5, vpdq=shared_hash),
        FrameFingerprint(timestamp=3.5, vpdq=shared_hash),
    ]

    result = align_vpdq_fingerprints(query, candidate)

    assert result is not None
    assert result.confidence >= 0.5
    assert result.inlier_count >= 3


def test_align_vpdq_detects_offset_temporal_match():
    shared_hash = _hash_solid_color(120, 80, 40)
    query = [
        FrameFingerprint(timestamp=0.0, vpdq=shared_hash),
        FrameFingerprint(timestamp=2.0, vpdq=shared_hash),
        FrameFingerprint(timestamp=4.0, vpdq=shared_hash),
        FrameFingerprint(timestamp=6.0, vpdq=shared_hash),
    ]
    candidate = [
        FrameFingerprint(timestamp=10.5, vpdq=shared_hash),
        FrameFingerprint(timestamp=12.5, vpdq=shared_hash),
        FrameFingerprint(timestamp=14.5, vpdq=shared_hash),
        FrameFingerprint(timestamp=16.5, vpdq=shared_hash),
    ]

    result = align_vpdq_fingerprints(query, candidate)

    assert result is not None
    assert result.inlier_count >= 3


def test_align_vpdq_rejects_unrelated_hashes():
    query = [
        FrameFingerprint(timestamp=0.0, vpdq=_hash_solid_color(10, 10, 10)),
        FrameFingerprint(timestamp=1.0, vpdq=_hash_solid_color(10, 10, 10)),
        FrameFingerprint(timestamp=2.0, vpdq=_hash_solid_color(10, 10, 10)),
    ]
    candidate = [
        FrameFingerprint(timestamp=0.0, vpdq=_hash_solid_color(200, 100, 50)),
        FrameFingerprint(timestamp=1.0, vpdq=_hash_solid_color(200, 100, 50)),
        FrameFingerprint(timestamp=2.0, vpdq=_hash_solid_color(200, 100, 50)),
    ]

    assert align_vpdq_fingerprints(query, candidate) is None
