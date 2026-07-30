import numpy as np

from app.fingerprints.base import FrameFingerprint
from app.matching.align import align_fingerprints


def _unit_vector(index: int, size: int = 16) -> list[float]:
    vector = np.zeros(size, dtype=np.float32)
    vector[index] = 1.0
    return vector.tolist()


def _frames(timestamps: list[float], vector_index: int) -> list[FrameFingerprint]:
    return [
        FrameFingerprint(timestamp=timestamp, dinov2=_unit_vector(vector_index))
        for timestamp in timestamps
    ]


def test_align_fingerprints_detects_linear_temporal_match():
    query = _frames([0.0, 1.0, 2.0, 3.0], vector_index=0)
    candidate = _frames([0.5, 1.5, 2.5, 3.5], vector_index=0)

    result = align_fingerprints(query, candidate, similarity_threshold=0.9)

    assert result is not None
    assert result.inlier_count >= 3
    assert result.confidence >= 0.5
    assert result.alignment in {"partial", "full"}


def test_align_fingerprints_detects_large_temporal_offset():
    query = _frames([0.0, 2.0, 4.0, 6.0], vector_index=0)
    candidate = _frames([10.5, 12.5, 14.5, 16.5], vector_index=0)

    result = align_fingerprints(query, candidate, similarity_threshold=0.9)

    assert result is not None
    assert result.inlier_count >= 3


def test_align_fingerprints_rejects_unrelated_videos():
    query = _frames([0.0, 1.0, 2.0], vector_index=0)
    candidate = _frames([0.0, 1.0, 2.0], vector_index=1)

    result = align_fingerprints(query, candidate, similarity_threshold=0.9)

    assert result is None
