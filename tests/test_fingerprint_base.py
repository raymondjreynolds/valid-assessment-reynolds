import numpy as np

from app.fingerprints.base import FrameFingerprint, frame_embedding_vector, has_frame_embedding


def test_frame_embedding_vector_reads_packed_bytes():
    vector = np.asarray([0.6, 0.8, 0.0], dtype=np.float32)
    frame = FrameFingerprint(timestamp=0.0, embedding=vector.tobytes())

    assert np.allclose(frame_embedding_vector(frame), vector)


def test_has_frame_embedding_supports_list_and_bytes():
    assert has_frame_embedding(FrameFingerprint(timestamp=0.0, dinov2=[1.0, 0.0]))
    assert has_frame_embedding(
        FrameFingerprint(timestamp=0.0, embedding=np.asarray([1.0], dtype=np.float32).tobytes())
    )
    assert not has_frame_embedding(FrameFingerprint(timestamp=0.0, vpdq="abc"))
