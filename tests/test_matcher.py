import tempfile

import numpy as np
import threatengine
from PIL import Image

from app.fingerprint_status import FingerprintStatus
from app.fingerprints.base import FingerprintSet, FrameFingerprint
from app.matching.matcher import VideoMatcher
from app.matching.prefilter import NoOpPrefilter
from app.storage import StoredVideo, VideoStore


def _video(
    video_id: str,
    ratio_bucket: str,
    vector_index: int,
    timestamps: list[float],
) -> StoredVideo:
    frames = [
        FrameFingerprint(
            timestamp=timestamp,
            dinov2=np.eye(8, dtype=np.float32)[vector_index].tolist(),
        )
        for timestamp in timestamps
    ]
    return StoredVideo(
        video_id=video_id,
        filename=f"{video_id}.mp4",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        ratio_bucket=ratio_bucket,
        content=b"video",
        fingerprints=FingerprintSet(frames=frames, method="dinov2"),
        fingerprint_method="dinov2",
        fingerprint_status=FingerprintStatus.READY,
    )


def _hash_solid_color(red: int, green: int, blue: int) -> str:
    image = Image.new("RGB", (224, 224), color=(red, green, blue))
    with tempfile.NamedTemporaryFile(suffix=".jpg") as handle:
        image.save(handle.name, "JPEG")
        hash_hex, _quality = threatengine.pdq_hash_file(handle.name)
        return hash_hex


def _vpdq_video(
    video_id: str,
    ratio_bucket: str,
    hash_hex: str,
    timestamps: list[float],
) -> StoredVideo:
    return StoredVideo(
        video_id=video_id,
        filename=f"{video_id}.mp4",
        width=576,
        height=1024,
        aspect_ratio="9:16",
        ratio_bucket=ratio_bucket,
        content=b"video",
        fingerprints=FingerprintSet(
            method="vpdq",
            frames=[
                FrameFingerprint(timestamp=timestamp, vpdq=hash_hex)
                for timestamp in timestamps
            ],
        ),
        fingerprint_method="vpdq",
        fingerprint_status=FingerprintStatus.READY,
    )


def test_matcher_returns_cross_bucket_matches_only():
    store = VideoStore()
    query = _video("11111111", "9:16", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    same_bucket = _video("22222222", "9:16", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    cross_bucket = _video("33333333", "16:9", vector_index=0, timestamps=[0.5, 1.5, 2.5, 3.5])
    unrelated = _video("44444444", "1:1", vector_index=1, timestamps=[0.0, 1.0, 2.0, 3.0])

    store.store(query)
    store.store(same_bucket)
    store.store(cross_bucket)
    store.store(unrelated)

    matcher = VideoMatcher(store=store, prefilter=NoOpPrefilter())
    matches = matcher.match("11111111")

    assert len(matches) == 1
    assert matches[0].video_id == "33333333"
    assert matches[0].filename == "33333333.mp4"
    assert matches[0].confidence > 0


def test_matcher_returns_vpdq_cross_bucket_matches():
    shared_hash = _hash_solid_color(120, 80, 40)
    store = VideoStore()
    query = _vpdq_video("11111111", "9:16", shared_hash, [0.0, 1.0, 2.0, 3.0])
    cross_bucket = _vpdq_video("33333333", "16:9", shared_hash, [0.5, 1.5, 2.5, 3.5])
    store.store(query)
    store.store(cross_bucket)

    matcher = VideoMatcher(store=store, prefilter=NoOpPrefilter())
    matches = matcher.match("11111111")

    assert len(matches) == 1
    assert matches[0].video_id == "33333333"
    assert matches[0].confidence >= 0.5


def test_matcher_excludes_other_bucket_query():
    store = VideoStore()
    query = _video("11111111", "Other", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    candidate = _video("22222222", "16:9", vector_index=0, timestamps=[0.5, 1.5, 2.5, 3.5])
    store.store(query)
    store.store(candidate)

    matcher = VideoMatcher(store=store, prefilter=NoOpPrefilter())
    assert matcher.match("11111111") == []


def test_matcher_excludes_other_bucket_candidates():
    store = VideoStore()
    query = _video("11111111", "9:16", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    other_bucket = _video("22222222", "Other", vector_index=0, timestamps=[0.5, 1.5, 2.5, 3.5])
    canonical = _video("33333333", "16:9", vector_index=0, timestamps=[0.5, 1.5, 2.5, 3.5])
    store.store(query)
    store.store(other_bucket)
    store.store(canonical)

    matcher = VideoMatcher(store=store, prefilter=NoOpPrefilter())
    matches = matcher.match("11111111")

    assert len(matches) == 1
    assert matches[0].video_id == "33333333"


def test_matcher_filters_matches_below_confidence_threshold(monkeypatch):
    store = VideoStore()
    query = _video("11111111", "9:16", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    cross_bucket = _video("33333333", "16:9", vector_index=0, timestamps=[0.5, 1.5, 2.5, 3.5])
    store.store(query)
    store.store(cross_bucket)

    monkeypatch.setattr("app.matching.score.MATCH_CONFIDENCE_THRESHOLD", 1.01)
    matcher = VideoMatcher(store=store, prefilter=NoOpPrefilter())
    assert matcher.match("11111111") == []


def test_matcher_unknown_video_raises_key_error():
    matcher = VideoMatcher(store=VideoStore(), prefilter=NoOpPrefilter())
    try:
        matcher.match("12345678")
        assert False, "Expected KeyError"
    except KeyError:
        pass
